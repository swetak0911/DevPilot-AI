"""
DevPilot AI - Phase 7 Verification Suite
Tests Testing and Repair Engine: Workspace Isolation, Sandbox Worker,
Error Trace Analyzer, Bounded Repair Loop (max 3 attempts), and REST APIs.
Run directly using: python verify_phase7.py
"""
import sys
import os
import tempfile
import shutil

# Add root directory and backend directory to sys.path
root_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(root_path, "backend")
if root_path not in sys.path:
    sys.path.insert(0, root_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def run_phase7_verification():
    print("=" * 72)
    print(" DevPilot AI - Phase 7 Testing & Repair Engine Suite")
    print("=" * 72)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import init_db, SessionLocal
    from execution.sandbox.workspace_manager import workspace_manager
    from execution.sandbox.docker_sandbox import sandbox_worker
    from execution.runners.error_analyzer import error_analyzer
    from execution.runners.test_runner import test_runner
    from execution.repair.repair_loop import repair_loop
    from app.models.repository import Repository
    from app.models.task import Task, CodePatch, TestResult, TaskType, TaskStatus

    init_db()
    client = TestClient(app)
    db = SessionLocal()
    passed_count = 0
    total_checks = 7

    try:
        # Check 1: Workspace Manager Scratch Isolation & Security Guards
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                # Create mock repo with sensitive .env
                with open(os.path.join(tmp_dir, "service.py"), "w", encoding="utf-8") as f:
                    f.write("def calculate(): return 42\n")
                with open(os.path.join(tmp_dir, ".env"), "w", encoding="utf-8") as f:
                    f.write("DATABASE_URL=secret\n")

                ws = workspace_manager.create_isolated_workspace("verify_task_ws", tmp_dir)
                assert os.path.exists(ws), "Workspace directory not created"
                assert os.path.exists(os.path.join(ws, "service.py")), "service.py not copied"
                assert not os.path.exists(os.path.join(ws, ".env")), ".env must be safely excluded"

                # Apply patch inside workspace
                workspace_manager.apply_patch_to_workspace(ws, "service.py", "def calculate(): return 100\n")
                with open(os.path.join(ws, "service.py"), "r", encoding="utf-8") as f:
                    assert f.read() == "def calculate(): return 100\n"

                # Path traversal guard check
                traversal_caught = False
                try:
                    workspace_manager.apply_patch_to_workspace(ws, "../../escaped.py", "malicious")
                except ValueError:
                    traversal_caught = True
                assert traversal_caught, "Path traversal guard failed to raise ValueError"

                # Cleanup
                assert workspace_manager.cleanup_workspace(ws) is True
                assert not os.path.exists(ws), "Workspace was not cleaned up"
            print(f" [PASS] 1. Scratch Workspace Isolation (.env filtered, Traversal guarded, Cleaned): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 1. Workspace Manager: {e}")

        # Check 2: Sandbox Worker Process & Timeout Limits
        try:
            python_bin = sys.executable or "python"
            exec_res = sandbox_worker.run_command(
                command=[python_bin, "-c", "print('sandbox_live_check_ok')"],
                working_dir=".",
                timeout=5
            )
            assert exec_res.exit_code == 0, f"Expected exit_code 0, got {exec_res.exit_code}"
            assert "sandbox_live_check_ok" in exec_res.stdout
            assert exec_res.timed_out is False
            assert exec_res.duration_seconds >= 0.0

            # Test timeout enforcement
            timeout_res = sandbox_worker.run_command(
                command=[python_bin, "-c", "import time; time.sleep(3)"],
                working_dir=".",
                timeout=1
            )
            assert timeout_res.timed_out is True, "Process failed to time out"
            assert timeout_res.exit_code == -1
            print(f" [PASS] 2. Sandbox Worker ({exec_res.runner_type.upper()} Runner, Timeout Guard Enforced): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 2. Sandbox Worker: {e}")

        # Check 3: Error Trace Analyzer & Failure Categorization
        try:
            # 1. Successful report
            pass_text = "=================== 15 passed in 0.95s ==================="
            pass_rep = error_analyzer.parse_test_output(pass_text, "", exit_code=0)
            assert pass_rep.all_passed is True
            assert pass_rep.passed == 15
            assert pass_rep.failed == 0

            # 2. Failing report with assertion error
            fail_text = (
                "FAILED tests/test_auth.py::test_jwt_login - AssertionError: assert False == True\n"
                "=================== 1 failed, 14 passed in 1.45s ==================="
            )
            fail_rep = error_analyzer.parse_test_output(fail_text, "", exit_code=1)
            assert fail_rep.all_passed is False
            assert fail_rep.failed == 1
            assert fail_rep.passed == 14
            assert len(fail_rep.failure_details) >= 1
            assert fail_rep.failure_details[0].failure_type == "ASSERTION_ERROR"
            assert "test_jwt_login" in fail_rep.failure_details[0].test_name

            # 3. Syntax error classification
            syn_text = "SyntaxError: invalid syntax"
            syn_rep = error_analyzer.parse_test_output("", syn_text, exit_code=1)
            assert syn_rep.failure_details[0].failure_type == "SYNTAX_ERROR"
            print(f" [PASS] 3. Error Trace Analyzer (Pass/Fail Counts, Traceback & Type Categorization): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 3. Error Trace Analyzer: {e}")

        # Check 4: Test Runner Automated Execution in Ephemeral Workspace
        try:
            with tempfile.TemporaryDirectory() as test_ws:
                test_file_path = os.path.join(test_ws, "test_verification.py")
                with open(test_file_path, "w", encoding="utf-8") as f:
                    f.write("def test_auto_check():\n    assert 1 + 1 == 2\n")

                report = test_runner.run_tests(workspace_path=test_ws, test_file="test_verification.py", attempt_number=1)
                assert report.attempt_number == 1
                assert report.all_passed is True
                assert report.passed >= 1
            print(f" [PASS] 4. Test Runner Sandbox Execution ({report.passed} passed in {report.duration_seconds}s): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 4. Test Runner: {e}")

        # Check 5: Bounded Self-Healing Repair Loop (Max 3 Attempts)
        try:
            with tempfile.TemporaryDirectory() as repair_dir:
                # Create buggy module and unit test
                with open(os.path.join(repair_dir, "calculator.py"), "w", encoding="utf-8") as f:
                    f.write("def calculate_sum(a, b):\n    return a - b  # Buggy subtraction\n")
                with open(os.path.join(repair_dir, "test_calculator.py"), "w", encoding="utf-8") as f:
                    f.write("from calculator import calculate_sum\ndef test_sum():\n    assert calculate_sum(3, 4) == 7\n")

                initial_patch = (
                    "--- a/calculator.py\n"
                    "+++ b/calculator.py\n"
                    "@@ -1,2 +1,2 @@\n"
                    " def calculate_sum(a, b):\n"
                    "-    return a - b  # Buggy subtraction\n"
                    "+    return a + b\n"
                )

                repair_res = repair_loop.execute_repair_loop(
                    task_id="phase7_verify_repair",
                    repo_path=repair_dir,
                    instruction="Fix calculate_sum so that 3 + 4 equals 7",
                    file_path="calculator.py",
                    original_content="def calculate_sum(a, b):\n    return a - b  # Buggy subtraction\n",
                    initial_diff=initial_patch,
                    test_file="test_calculator.py"
                )

                assert repair_res.resolved is True
                assert repair_res.attempts_used <= 3, f"Exceeded max 3 attempts: {repair_res.attempts_used}"
                assert len(repair_res.attempt_reports) >= 1
                assert repair_res.attempt_reports[-1].all_passed is True
            print(f" [PASS] 5. Bounded Self-Healing Repair Loop (Resolved on attempt {repair_res.attempts_used}/3): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 5. Bounded Repair Loop: {e}")

        # Setup Seed Task for Database & REST API Checks
        test_repo = db.query(Repository).filter(Repository.name == "testing-repair-repo").first()
        if not test_repo:
            test_repo = Repository(
                name="testing-repair-repo",
                full_name="devpilot/testing-repair-repo",
                html_url="https://github.com/devpilot/testing-repair-repo",
                clone_url="https://github.com/devpilot/testing-repair-repo.git",
                default_branch="main"
            )
            db.add(test_repo)
            db.commit()
            db.refresh(test_repo)

        repo_ws = os.path.join(".", "execution", "workspaces", "testing-repair-repo")
        os.makedirs(repo_ws, exist_ok=True)
        with open(os.path.join(repo_ws, "test_health.py"), "w", encoding="utf-8") as f:
            f.write("def test_health_check(): assert True\n")

        test_task = Task(
            user_id="phase7_developer",
            repository_id=test_repo.id,
            title="Verify sandbox unit tests on patched security module",
            instruction="Ensure hash verification handles empty string safely and passes pytest suite",
            task_type=TaskType.BUG_FIX,
            status=TaskStatus.RUNNING,
            execution_plan=[]
        )
        db.add(test_task)
        db.commit()
        db.refresh(test_task)

        test_patch = CodePatch(
            task_id=test_task.id,
            file_path="test_health.py",
            original_content="def test_health_check(): assert True\n",
            modified_content="def test_health_check(): assert True\n",
            unified_diff="--- a/test_health.py\n+++ b/test_health.py\n@@ -1,1 +1,1 @@\n def test_health_check(): assert True\n",
            is_approved="PENDING"
        )
        db.add(test_patch)
        db.commit()

        # Check 6: Database TestResult Record Persistence
        try:
            sample_tr = TestResult(
                task_id=test_task.id,
                attempt_number=1,
                passed=8,
                failed=0,
                errors=0,
                exit_code=0,
                stdout="=================== 8 passed in 0.92s ===================",
                stderr="",
                failure_details=[]
            )
            db.add(sample_tr)
            db.commit()
            db.refresh(sample_tr)

            saved_tr = db.query(TestResult).filter(TestResult.task_id == test_task.id).first()
            assert saved_tr is not None
            assert saved_tr.attempt_number == 1
            assert saved_tr.passed == 8
            print(f" [PASS] 6. Database TestResult Persistence (Task: {test_task.id[:8]}, Attempt: #{saved_tr.attempt_number}): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 6. Database TestResult Persistence: {e}")

        # Check 7: Testing & Repair REST APIs (/api/tasks/:id/run-tests & /tests)
        try:
            # 1. Run tests API
            run_res = client.post(f"/api/tasks/{test_task.id}/run-tests")
            assert run_res.status_code == 200, f"Run tests API failed: {run_res.text}"
            run_data = run_res.json()
            assert "attempt_number" in run_data
            assert "all_passed" in run_data

            # 2. Get tests API
            get_res = client.get(f"/api/tasks/{test_task.id}/tests")
            assert get_res.status_code == 200, f"Get tests API failed: {get_res.text}"
            test_records = get_res.json()["test_results"]
            assert len(test_records) >= 1
            assert test_records[0]["passed"] >= 0
            print(f" [PASS] 7. Testing & Repair REST APIs (/api/tasks/:id/run-tests, /tests): OK ({len(test_records)} attempts logged)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 7. Testing & Repair REST APIs: {e}")

    finally:
        db.close()

    print("=" * 72)
    print(f" Phase 7 Verification Score: {passed_count}/{total_checks} ({(passed_count/total_checks)*100:.1f}%)")
    print("=" * 72)

    return passed_count == total_checks

if __name__ == "__main__":
    success = run_phase7_verification()
    sys.exit(0 if success else 1)
