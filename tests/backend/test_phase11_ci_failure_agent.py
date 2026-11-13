"""
DevPilot AI - Phase 11 CI/CD Failure Intelligence Tests
Tests log parser, multi-category classification, RAG code lookup,
root-cause hypothesis generation, patch synthesis, and REST APIs.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, SessionLocal
from devops.cicd.log_parser import ci_log_parser, ParsedCIError
from ai_engine.agents.ci_failure_agent import ci_failure_agent, CIFailureDiagnosis
from app.services.ci_intelligence_service import ci_intelligence_service
from app.models.cicd import WorkflowRun
from app.schemas.cicd import CIRemediateRequest, CILogParseRequest


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def db():
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_log_parser_ansi_and_boundaries():
    ansi_log = "\x1b[31m##[error]backend/app/core/security.py:45:1: F401 'jwt' imported but unused\x1b[0m"
    clean = ci_log_parser.strip_ansi(ansi_log)
    assert "\x1b" not in clean
    assert "F401 'jwt' imported but unused" in clean

    raw_log = """
##[group]Run Run Code Linter
backend/app/core/security.py:45:1: F401 'jwt' imported but unused
backend/app/api/v1/endpoints/auth.py:28:9: E501 line too long
##[error]Process completed with exit code 1.
"""
    parsed = ci_log_parser.parse(raw_log, default_job="lint", default_step="Run Code Linter")
    assert parsed.failing_job == "lint"
    assert parsed.failing_step == "Run Code Linter"
    assert parsed.failing_file == "backend/app/core/security.py"
    assert parsed.failing_line == 45
    assert "F401" in parsed.error_message


def test_multi_category_failure_classification():
    # 1. Dependency
    dep_log = "ModuleNotFoundError: No module named 'jwt2'\n##[error]Process completed with exit code 1."
    p1 = ci_log_parser.parse(dep_log)
    c1, conf1 = ci_failure_agent.classify_failure(p1, dep_log)
    assert c1 == "DEPENDENCY"
    assert conf1 >= 0.90

    # 2. CI Config
    cfg_log = "yaml.scanner.ScannerError: mapping values are not allowed here in .github/workflows/ci.yml:14"
    p2 = ci_log_parser.parse(cfg_log)
    c2, conf2 = ci_failure_agent.classify_failure(p2, cfg_log)
    assert c2 == "CI_CONFIG"
    assert conf2 >= 0.90

    # 3. Environment
    env_log = "Fatal: No space left on device\nCommand timed out after 300 seconds"
    p3 = ci_log_parser.parse(env_log)
    c3, conf3 = ci_failure_agent.classify_failure(p3, env_log)
    assert c3 == "ENVIRONMENT"
    assert conf3 >= 0.90

    # 4. Application Code
    app_log = "FAILED tests/test_security.py::test_jwt - AssertionError: assert 401 == 200"
    p4 = ci_log_parser.parse(app_log)
    c4, conf4 = ci_failure_agent.classify_failure(p4, app_log)
    assert c4 == "APPLICATION_CODE"
    assert conf4 >= 0.90


def test_root_cause_hypothesis_generation():
    parsed = ParsedCIError(
        failing_job="test",
        failing_step="Execute Automated Tests",
        error_message="ModuleNotFoundError: No module named 'pydantic_settings'",
        error_trace="Traceback (most recent call last):\n  File 'main.py', line 5\n    import pydantic_settings",
        failing_file="main.py",
        failing_line=5
    )
    hypothesis, fix = ci_failure_agent.generate_root_cause_hypothesis(parsed, "DEPENDENCY")
    assert "missing" in hypothesis.lower()
    assert "requirements.txt" in fix.lower()


def test_remediation_patch_synthesis():
    parsed = ParsedCIError(
        failing_job="lint",
        failing_step="Run Code Linter",
        error_message="backend/app/core/security.py:45:1: F401 'jwt' imported but unused",
        error_trace="F401 'jwt' imported but unused",
        failing_file="backend/app/core/security.py",
        failing_line=45
    )
    file_content = "import os\nimport jwt\nimport sys\n\ndef decode():\n    pass\n"
    patch = ci_failure_agent.generate_remediation_patch(parsed, "APPLICATION_CODE", file_content=file_content)
    assert patch is not None
    assert "--- a/backend/app/core/security.py" in patch
    assert "-import jwt" in patch


def test_ci_failure_rest_apis(client, db):
    # Ensure representative failed run exists
    failed_run = db.query(WorkflowRun).filter(WorkflowRun.conclusion == "failure").first()
    if not failed_run:
        failed_run = WorkflowRun(
            repository_id="default-repo",
            github_run_id="999901",
            workflow_name="Docker Container Build",
            event="push",
            status="completed",
            conclusion="failure",
            duration_seconds=35,
            commit_sha="a7b8c9d",
            branch_name="feature/docker-fix",
            logs_summary="Step 'Run Linting Checks' failed with 2 errors in security.py."
        )
        db.add(failed_run)
        db.commit()
        db.refresh(failed_run)

    # 1. POST /api/cicd/runs/{run_id}/analyse
    res_analyse = client.post(f"/api/cicd/runs/{failed_run.id}/analyse")
    assert res_analyse.status_code == 200
    data = res_analyse.json()
    assert data["run_id"] == failed_run.id
    assert data["failure_category"] in ["APPLICATION_CODE", "DEPENDENCY", "CI_CONFIG", "ENVIRONMENT"]
    assert "root_cause_hypothesis" in data
    assert "suggested_fix" in data

    # 2. POST /api/cicd/runs/{run_id}/remediate
    res_remediate = client.post(f"/api/cicd/runs/{failed_run.id}/remediate", json={
        "run_id": failed_run.id,
        "branch_name": f"devpilot/ci-fix-test-{failed_run.id[:6]}"
    })
    assert res_remediate.status_code == 200
    rem_data = res_remediate.json()
    assert rem_data["success"] is True
    assert "commit_hash" in rem_data
    assert "branch_name" in rem_data

    # 3. POST /api/cicd/logs/parse
    raw_log = "##[group]Run Tests\nModuleNotFoundError: No module named 'cryptography'\n##[error]exit 1"
    res_parse = client.post("/api/cicd/logs/parse", json={"logs": raw_log})
    assert res_parse.status_code == 200
    parse_data = res_parse.json()
    assert parse_data["failure_category"] == "DEPENDENCY"
    assert "cryptography" in parse_data["error_message"]
