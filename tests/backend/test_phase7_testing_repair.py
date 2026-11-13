"""
Phase 7 Testing and Repair Engine Test Suite
Tests Workspace Manager isolation, Sandbox Worker execution, Error Trace Analyzer,
Test Runner, Bounded Repair Loop (max 3 attempts), and Test Results REST APIs.
"""
import sys
import os
import pytest
from execution.sandbox.workspace_manager import workspace_manager
from execution.sandbox.docker_sandbox import sandbox_worker, ExecutionResult
from execution.runners.error_analyzer import error_analyzer, StructuredTestReport
from execution.runners.test_runner import test_runner
from execution.repair.repair_loop import repair_loop, RepairResult
from app.services.test_service import test_service
from app.models.task import Task, TaskStatus, TaskType, CodePatch, TestResult
from app.models.repository import Repository


def test_workspace_manager_isolation_and_patching(tmp_path):
    """Verifies scratch directory provisioning, file copying, patch application, and path traversal guard."""
    # 1. Setup mock source repository
    src_dir = tmp_path / "mock_repo"
    src_dir.mkdir()
    (src_dir / "app.py").write_text("def hello(): return 'world'\n", encoding="utf-8")
    (src_dir / ".env").write_text("SECRET=12345\n", encoding="utf-8")

    ws = workspace_manager.create_isolated_workspace(task_id="test_ws_1", source_repo_path=str(src_dir))
    assert os.path.exists(ws)
    assert os.path.exists(os.path.join(ws, "app.py"))
    assert not os.path.exists(os.path.join(ws, ".env")), ".env must not be copied to workspace"

    # 2. Apply patch
    workspace_manager.apply_patch_to_workspace(ws, "app.py", "def hello(): return 'patched'\n")
    with open(os.path.join(ws, "app.py"), "r", encoding="utf-8") as f:
        assert f.read() == "def hello(): return 'patched'\n"

    # 3. Path traversal rejection
    with pytest.raises(ValueError):
        workspace_manager.apply_patch_to_workspace(ws, "../../escaped.py", "malicious")

    # 4. Cleanup
    assert workspace_manager.cleanup_workspace(ws) is True
    assert not os.path.exists(ws)


def test_sandbox_worker_execution():
    """Verifies command execution in sandbox, capturing stdout, exit_code, and timeout."""
    python_bin = sys.executable or "python"
    res: ExecutionResult = sandbox_worker.run_command(
        command=[python_bin, "-c", "print('sandbox_test_success')"],
        working_dir=".",
        timeout=5
    )
    assert res.exit_code == 0
    assert "sandbox_test_success" in res.stdout
    assert res.timed_out is False
    assert res.duration_seconds >= 0.0

    # Test timeout guard
    timeout_res = sandbox_worker.run_command(
        command=[python_bin, "-c", "import time; time.sleep(3)"],
        working_dir=".",
        timeout=1
    )
    assert timeout_res.timed_out is True
    assert timeout_res.exit_code == -1


def test_error_analyzer_parsing():
    """Verifies pytest output parsing, failure classification, and traceback extraction."""
    # 1. Passing Pytest Output
    passed_output = "=================== 5 passed in 0.85s ==================="
    rep_pass = error_analyzer.parse_test_output(passed_output, "", exit_code=0)
    assert rep_pass.all_passed is True
    assert rep_pass.passed == 5
    assert rep_pass.failed == 0

    # 2. Failing Pytest Output with AssertionError
    failed_output = (
        "FAILED tests/test_security.py::test_auth - AssertionError: assert False\n"
        "=================== 1 failed, 4 passed in 1.12s ==================="
    )
    rep_fail = error_analyzer.parse_test_output(failed_output, "", exit_code=1)
    assert rep_fail.all_passed is False
    assert rep_fail.failed == 1
    assert rep_fail.passed == 4
    assert len(rep_fail.failure_details) >= 1
    f_detail = rep_fail.failure_details[0]
    assert f_detail.failure_type == "ASSERTION_ERROR"
    assert "test_security.py" in f_detail.test_name

    # 3. Syntax Error Output
    syntax_output = "SyntaxError: invalid syntax (runner.py, line 5)"
    rep_syn = error_analyzer.parse_test_output("", syntax_output, exit_code=1)
    assert rep_syn.all_passed is False
    assert rep_syn.failure_details[0].failure_type == "SYNTAX_ERROR"


def test_test_runner_execution(tmp_path):
    """Verifies that TestRunner invokes sandbox and generates structured report."""
    test_dir = tmp_path / "sandbox_test_dir"
    test_dir.mkdir()
    (test_dir / "test_sample.py").write_text("def test_ok(): assert True\n", encoding="utf-8")

    report: StructuredTestReport = test_runner.run_tests(
        workspace_path=str(test_dir),
        test_file="test_sample.py",
        attempt_number=1
    )
    assert report.attempt_number == 1
    assert report.all_passed is True
    assert report.passed >= 1


def test_bounded_repair_loop(tmp_path):
    """Verifies that RepairLoop respects upper bound (max 3 attempts) and records history."""
    repo_dir = tmp_path / "repair_repo"
    repo_dir.mkdir()
    (repo_dir / "mod.py").write_text("def add(a, b): return a - b\n", encoding="utf-8")
    (repo_dir / "test_mod.py").write_text("from mod import add\ndef test_add(): assert add(1, 2) == 3\n", encoding="utf-8")

    diff = (
        "--- a/mod.py\n"
        "+++ b/mod.py\n"
        "@@ -1,1 +1,1 @@\n"
        "-def add(a, b): return a - b\n"
        "+def add(a, b): return a + b\n"
    )

    res: RepairResult = repair_loop.execute_repair_loop(
        task_id="repair_test_task",
        repo_path=str(repo_dir),
        instruction="Fix add function so that 1 + 2 equals 3",
        file_path="mod.py",
        original_content="def add(a, b): return a - b\n",
        initial_diff=diff,
        test_file="test_mod.py"
    )

    assert res.resolved is True
    assert res.attempts_used >= 1
    assert res.attempts_used <= 3
    assert len(res.attempt_reports) >= 1
    assert res.attempt_reports[-1].all_passed is True


def test_test_service_and_db_persistence(db_session):
    """Verifies that TestService coordinates test execution and persists TestResult records."""
    repo = Repository(
        name="test-service-repo",
        full_name="devpilot/test-service-repo",
        html_url="https://github.com/devpilot/test-service-repo",
        clone_url="https://github.com/devpilot/test-service-repo.git",
        default_branch="main"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    task = Task(
        user_id="test_user",
        repository_id=repo.id,
        title="Verify patch execution in sandbox",
        instruction="Run pytest and assert all tests pass",
        task_type=TaskType.BUG_FIX,
        status=TaskStatus.RUNNING,
        execution_plan=[]
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    patch = CodePatch(
        task_id=task.id,
        file_path="app/math_ops.py",
        original_content="def multiply(x, y): return x + y\n",
        modified_content="def multiply(x, y): return x * y\n",
        unified_diff="--- a/app/math_ops.py\n+++ b/app/math_ops.py\n@@ -1,1 +1,1 @@\n-def multiply(x, y): return x + y\n+def multiply(x, y): return x * y\n",
        is_approved="PENDING"
    )
    db_session.add(patch)
    db_session.commit()

    run_res = test_service.run_sandbox_tests(db_session, task.id)
    assert "attempt_number" in run_res
    assert "all_passed" in run_res

    # Check database persistence
    saved_results = db_session.query(TestResult).filter(TestResult.task_id == task.id).all()
    assert len(saved_results) >= 1
    assert saved_results[0].attempt_number == 1
