"""
DevPilot AI - Phase 6 Verification Suite
Tests LLM Coding Agents: Provider Abstraction, Planning Agent,
Bug Detection Agent, Coding Agent, Patch Validator, and Autonomous Task Lifecycle.
Run directly using: python verify_phase6.py
"""
import sys
import os

# Add root directory and backend directory to sys.path
root_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(root_path, "backend")
if root_path not in sys.path:
    sys.path.insert(0, root_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

def run_phase6_verification():
    print("=" * 72)
    print(" DevPilot AI - Phase 6 LLM Coding Agents Suite")
    print("=" * 72)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import init_db, SessionLocal
    from ai_engine.agents.llm_provider import llm_provider
    from ai_engine.agents.planning_agent import planning_agent
    from ai_engine.agents.bug_detection_agent import bug_detection_agent
    from ai_engine.agents.coding_agent import coding_agent
    from ai_engine.agents.patch_validator import patch_validator
    from ai_engine.agents.agent_orchestrator import agent_orchestrator
    from app.models.repository import Repository
    from app.models.task import Task, CodePatch

    init_db()
    client = TestClient(app)
    db = SessionLocal()
    passed_count = 0
    total_checks = 7

    try:
        # Check 1: Multi-Provider LLM Abstraction & Token Estimator
        try:
            tokens = llm_provider.estimate_tokens("def test_function(a: int) -> int: return a * 2")
            assert tokens > 0, "Token count must be positive"
            gen_resp = llm_provider.generate(
                prompt="Deconstruct this feature request into a plan",
                system_prompt="You are a planning agent",
                json_mode=True
            )
            assert len(gen_resp) > 10, "LLM provider generated empty response"
            print(f" [PASS] 1. LLM Provider Abstraction & Engineering Intelligence Engine: OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 1. LLM Provider Abstraction: {e}")

        # Check 2: Planning Agent Architectural Task Decomposition
        try:
            task_instr = "Refactor authentication service to introduce password length verification and rate limits."
            plan = planning_agent.plan(
                instruction=task_instr,
                task_type="SECURITY_PATCH",
                repository_context={"name": "DevPilot-AI", "primary_language": "Python"}
            )
            assert len(plan.task_summary) > 5, "Missing task summary"
            assert len(plan.relevant_files) >= 1, "Missing relevant files"
            assert len(plan.execution_steps) >= 3, f"Expected >= 3 steps, got {len(plan.execution_steps)}"
            assert len(plan.acceptance_criteria) >= 1, "Missing acceptance criteria"
            print(f" [PASS] 2. Planning Agent Task Decomposition ({len(plan.execution_steps)} execution steps, target: {plan.relevant_files[0]}): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 2. Planning Agent: {e}")

        # Check 3: Bug Detection Agent & CodeBERT Signal Synthesis
        try:
            vulnerable_snippet = (
                "def execute_user_query(user_query: str, db):\n"
                "    cursor = db.cursor()\n"
                "    cursor.execute(f'SELECT * FROM users WHERE name = {user_query}')\n"
                "    return cursor.fetchall()\n"
            )
            bug_report = bug_detection_agent.analyze(
                file_path="backend/services/user_db.py",
                file_content=vulnerable_snippet,
                task_instruction="Remediate SQL injection vulnerability"
            )
            assert bug_report.defect_found is True, "Vulnerability not detected"
            assert bug_report.codebert_probability >= 0.60, f"Expected high CodeBERT score, got {bug_report.codebert_probability}"
            assert bug_report.severity in ["HIGH", "CRITICAL"], f"Expected HIGH/CRITICAL severity, got {bug_report.severity}"
            assert len(bug_report.remediation_strategy) > 5, "Missing remediation strategy"
            print(f" [PASS] 3. Bug Detection Agent (Isolated {bug_report.defect_type}, Severity: {bug_report.severity}): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 3. Bug Detection Agent: {e}")

        # Check 4: Coding Agent Patch Generation & Unified Diff
        try:
            orig_script = (
                "def run_script(cmd: str):\n"
                "    return eval(cmd)\n"
            )
            coding_res = coding_agent.generate_patch(
                instruction="Eliminate eval() vulnerability in run_script",
                file_path="execution/runner.py",
                original_content=orig_script,
                bug_report=bug_report
            )
            assert coding_res.file_path == "execution/runner.py"
            assert "--- a/execution/runner.py" in coding_res.unified_diff
            assert "+++ b/execution/runner.py" in coding_res.unified_diff
            assert "@@" in coding_res.unified_diff
            assert coding_res.lines_added > 0
            print(f" [PASS] 4. Coding Agent Patch Generation (+{coding_res.lines_added} / -{coding_res.lines_removed} lines diff): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 4. Coding Agent: {e}")

        # Check 5: Patch Validator Hunk Parser, Line Boundaries & AST Validation
        try:
            valid_diff = (
                "--- a/execution/runner.py\n"
                "+++ b/execution/runner.py\n"
                "@@ -1,2 +1,4 @@\n"
                " def run_script(cmd: str):\n"
                "+    import ast\n"
                "+    return ast.literal_eval(cmd)\n"
                "     return eval(cmd)\n"
            )
            val_res = patch_validator.validate_and_apply(
                original_content=orig_script,
                unified_diff=valid_diff,
                file_path="execution/runner.py"
            )
            assert val_res.is_valid is True, f"Validation failed: {val_res.errors}"
            assert val_res.hunk_count == 1
            assert val_res.syntax_valid is True
            assert "ast.literal_eval" in val_res.applied_content

            # Test malformed patch rejection
            bad_diff = "MALFORMED DIFF WITHOUT HUNK HEADERS"
            bad_res = patch_validator.validate_and_apply(orig_script, bad_diff, "execution/runner.py")
            assert bad_res.is_valid is False, "Malformed patch was unexpectedly accepted"
            assert len(bad_res.errors) >= 1
            print(f" [PASS] 5. Patch Syntax & Line Boundary Validator (Valid Dry-Run + Corrupt Rejection): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 5. Patch Validator: {e}")

        # Check 6: Agent Orchestrator Multi-Stage Pipeline Execution
        try:
            pipeline_res = agent_orchestrator.execute_task_pipeline(
                task_id="phase6_verify_task",
                instruction="Fix SQL injection vulnerability in database lookup function",
                repository_path="."
            )
            assert pipeline_res["status"] in ["COMPLETED", "VALIDATION_FAILED"]
            assert "plan" in pipeline_res and "execution_steps" in pipeline_res["plan"]
            assert "bug_report" in pipeline_res and pipeline_res["bug_report"]["defect_found"] is True
            assert "patch" in pipeline_res and "unified_diff" in pipeline_res["patch"]
            assert len(pipeline_res["logs"]) >= 4, f"Expected >= 4 logs, got {len(pipeline_res['logs'])}"
            print(f" [PASS] 6. Agent Orchestrator Pipeline (Planning -> Defect Diagnosis -> Coding -> Validation): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 6. Agent Orchestrator: {e}")

        # Check 7: Autonomous Task REST API Lifecycle & Patch Validation Endpoint
        try:
            # Setup seed repository
            repo = db.query(Repository).first()
            if not repo:
                repo = Repository(
                    name="autonomous-repo",
                    full_name="devpilot/autonomous-repo",
                    html_url="https://github.com/devpilot/autonomous-repo",
                    clone_url="https://github.com/devpilot/autonomous-repo.git",
                    default_branch="main"
                )
                db.add(repo)
                db.commit()
                db.refresh(repo)

            # 1. Test /api/tasks/validate-patch standalone endpoint
            val_payload = {
                "file_path": "runner.py",
                "original_content": orig_script,
                "unified_diff": valid_diff
            }
            val_api_res = client.post("/api/tasks/validate-patch", json=val_payload)
            assert val_api_res.status_code == 200, f"Validate patch API failed: {val_api_res.text}"
            assert val_api_res.json()["is_valid"] is True

            # 2. Test Task Creation & Agent Execution via REST API
            task_payload = {
                "repository_id": repo.id,
                "title": "Remediate command injection vulnerability",
                "instruction": "Replace eval() and dynamic execution with safe ast literal evaluation",
                "task_type": "BUG_FIX"
            }
            create_res = client.post("/api/tasks", json=task_payload)
            assert create_res.status_code == 201, f"Task creation failed: {create_res.text}"
            task_data = create_res.json()
            assert task_data["id"] is not None
            assert len(task_data["execution_plan"]) >= 1

            # 3. Retrieve Diff endpoint
            diff_res = client.get(f"/api/tasks/{task_data['id']}/diff")
            assert diff_res.status_code == 200, f"Diff API failed: {diff_res.text}"
            diff_data = diff_res.json()
            assert diff_data["has_patches"] is True
            assert len(diff_data["patches"]) >= 1
            print(f" [PASS] 7. Autonomous Task Lifecycle & Patch Endpoints (/api/tasks/*): OK")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 7. Task Lifecycle & Patch APIs: {e}")

    finally:
        db.close()

    print("=" * 72)
    print(f" Phase 6 Verification Score: {passed_count}/{total_checks} ({(passed_count/total_checks)*100:.1f}%)")
    print("=" * 72)

    return passed_count == total_checks

if __name__ == "__main__":
    success = run_phase6_verification()
    sys.exit(0 if success else 1)
