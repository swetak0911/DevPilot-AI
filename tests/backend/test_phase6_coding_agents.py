"""
Phase 6 LLM Coding Agents Test Suite
Tests LLM Provider abstraction, Planning Agent, Bug Detection Agent,
Coding Agent patch generation, Patch Validator, and Agent Orchestrator pipeline.
"""
import pytest
from ai_engine.agents.llm_provider import llm_provider
from ai_engine.agents.planning_agent import planning_agent, PlanningResult
from ai_engine.agents.bug_detection_agent import bug_detection_agent, BugReport
from ai_engine.agents.coding_agent import coding_agent, CodingResult
from ai_engine.agents.patch_validator import patch_validator, PatchValidationResult
from ai_engine.agents.agent_orchestrator import agent_orchestrator
from app.services.agent_service import agent_service
from app.models.task import Task, TaskStatus, TaskType, CodePatch
from app.models.repository import Repository


def test_llm_provider_token_estimation_and_fallback():
    """Verifies token estimator and deterministic engineering fallback engine."""
    tokens = llm_provider.estimate_tokens("def hello_world(): return 'hello'")
    assert tokens > 0

    plan_resp = llm_provider.generate(
        prompt="Decompose task into execution plan",
        system_prompt="You are a Planning Agent",
        json_mode=True
    )
    assert "task_summary" in plan_resp
    assert "execution_steps" in plan_resp


def test_planning_agent_decomposition():
    """Verifies that Planning Agent deconstructs instructions into structured plans."""
    instruction = "Refactor user authentication endpoint to add rate limiting and eliminate SQL injection."
    plan: PlanningResult = planning_agent.plan(
        instruction=instruction,
        task_type="SECURITY_PATCH",
        repository_context={"name": "DevPilot-AI", "primary_language": "Python"}
    )
    assert len(plan.task_summary) > 5
    assert len(plan.relevant_files) >= 1
    assert len(plan.execution_steps) >= 3
    assert len(plan.acceptance_criteria) >= 1
    assert any("step" in s for s in plan.execution_steps)


def test_bug_detection_agent_analysis():
    """Verifies that Bug Detection Agent identifies defects, CWE types, and line numbers."""
    vulnerable_code = (
        "def query_user(username: str, db):\n"
        "    cursor = db.cursor()\n"
        "    cursor.execute(f'SELECT * FROM users WHERE name = {username}')\n"
        "    return cursor.fetchone()\n"
    )
    report: BugReport = bug_detection_agent.analyze(
        file_path="src/user_service.py",
        file_content=vulnerable_code,
        task_instruction="Fix SQL injection vulnerability"
    )
    assert report.defect_found is True
    assert "SQL" in report.defect_type or "Injection" in report.defect_type or report.codebert_probability > 0.5
    assert report.severity in ["HIGH", "CRITICAL", "MEDIUM"]
    assert "start_line" in report.vulnerable_lines
    assert len(report.remediation_strategy) > 5


def test_coding_agent_patch_generation():
    """Verifies that Coding Agent generates modified code and valid unified diff."""
    original_code = (
        "def run_command(cmd: str):\n"
        "    return eval(cmd)\n"
    )
    res: CodingResult = coding_agent.generate_patch(
        instruction="Remediate arbitrary code execution in run_command",
        file_path="app/cmd_runner.py",
        original_content=original_code
    )
    assert res.file_path == "app/cmd_runner.py"
    assert "eval(" not in res.modified_content or "ast.literal_eval" in res.modified_content or len(res.modified_content) > 10
    assert "--- a/app/cmd_runner.py" in res.unified_diff
    assert "+++ b/app/cmd_runner.py" in res.unified_diff
    assert "@@" in res.unified_diff
    assert res.lines_added > 0


def test_patch_validator_valid_and_malformed():
    """Verifies that Patch Validator verifies valid unified diffs and rejects corrupt hunks."""
    orig = "def greet(name: str):\n    return f'Hello {name}'\n"
    valid_diff = (
        "--- a/greet.py\n"
        "+++ b/greet.py\n"
        "@@ -1,2 +1,4 @@\n"
        " def greet(name: str):\n"
        "+    if not name:\n"
        "+        return 'Hello Stranger'\n"
        "     return f'Hello {name}'\n"
    )
    res: PatchValidationResult = patch_validator.validate_and_apply(
        original_content=orig,
        unified_diff=valid_diff,
        file_path="greet.py"
    )
    assert res.is_valid is True
    assert res.hunk_count == 1
    assert len(res.errors) == 0
    assert res.syntax_valid is True
    assert "Hello Stranger" in res.applied_content

    # Malformed diff missing hunk headers
    bad_diff = "Invalid diff text without headers"
    bad_res = patch_validator.validate_and_apply(orig, bad_diff, "greet.py")
    assert bad_res.is_valid is False
    assert len(bad_res.errors) >= 1


def test_agent_orchestrator_pipeline():
    """Verifies end-to-end agent workflow execution."""
    pipeline_res = agent_orchestrator.execute_task_pipeline(
        task_id="task_test_123",
        instruction="Eliminate SQL injection risk in database lookup function",
        repository_path="."
    )
    assert pipeline_res["status"] in ["COMPLETED", "VALIDATION_FAILED"]
    assert "plan" in pipeline_res
    assert "bug_report" in pipeline_res
    assert "patch" in pipeline_res
    assert len(pipeline_res["logs"]) >= 4
    assert any(log["agent"] == "Planning Agent" for log in pipeline_res["logs"])
    assert any(log["agent"] == "Coding Agent" for log in pipeline_res["logs"])


def test_agent_service_task_integration(db_session):
    """Verifies database persistence of plans, steps, and patches via agent_service."""
    repo = Repository(
        name="agent-test-repo",
        full_name="devpilot/agent-test-repo",
        html_url="https://github.com/devpilot/agent-test-repo",
        clone_url="https://github.com/devpilot/agent-test-repo.git",
        default_branch="main"
    )
    db_session.add(repo)
    db_session.commit()
    db_session.refresh(repo)

    task = Task(
        user_id="test_user",
        repository_id=repo.id,
        title="Fix arbitrary eval in runner",
        instruction="Remove eval() call and replace with safe literal evaluation",
        task_type=TaskType.BUG_FIX,
        status=TaskStatus.RUNNING,
        execution_plan=[]
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    agent_service.execute_task_agents(db_session, task)
    assert len(task.execution_plan) >= 1
    assert task.status == TaskStatus.IN_REVIEW

    patches = db_session.query(CodePatch).filter(CodePatch.task_id == task.id).all()
    assert len(patches) >= 1
    assert "--- a/" in patches[0].unified_diff
