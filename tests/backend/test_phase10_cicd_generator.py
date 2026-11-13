"""
DevPilot AI - Phase 10 CI/CD & DevOps Engine Tests
Tests framework detection, workflow synthesis, YAML validation, linter engine,
git commits, and REST endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, SessionLocal
from devops.cicd.framework_detector import framework_detector, FrameworkDetectionReport
from devops.cicd.pipeline_generator import pipeline_generator
from devops.cicd.yaml_validator import yaml_validator
from app.services.cicd_service import cicd_service
from app.models.cicd import WorkflowRun
from app.schemas.cicd import WorkflowGenerateRequest, WorkflowCommitRequest, WorkflowDispatchTriggerRequest


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


def test_framework_detection_python():
    files = ["backend/requirements.txt", "backend/app/main.py", "tests/test_api.py", "Dockerfile"]
    report = framework_detector.detect_from_file_list("/mock", files)
    assert report.primary_language == "Python"
    assert report.build_tool == "pip"
    assert report.test_runner == "pytest"
    assert report.linter == "ruff"
    assert report.has_docker is True
    assert report.has_tests is True
    assert "python-version" in report.recommended_matrix


def test_framework_detection_node_typescript():
    files = ["package.json", "src/App.tsx", "pnpm-lock.yaml", "vitest.config.ts"]
    report = framework_detector.detect_from_file_list("/mock", files)
    assert report.primary_language == "TypeScript"
    assert report.build_tool == "pnpm"
    assert report.linter == "eslint"
    assert "node-version" in report.recommended_matrix


def test_framework_detection_go_rust_java():
    # Go
    go_report = framework_detector.detect_from_file_list("/mock", ["go.mod", "main.go"])
    assert go_report.primary_language == "Go"
    assert go_report.test_runner == "go test ./..."

    # Rust
    rust_report = framework_detector.detect_from_file_list("/mock", ["Cargo.toml", "src/main.rs"])
    assert rust_report.primary_language == "Rust"
    assert rust_report.test_runner == "cargo test"

    # Java
    java_report = framework_detector.detect_from_file_list("/mock", ["pom.xml", "src/Main.java"])
    assert java_report.primary_language == "Java"
    assert java_report.build_tool == "maven"


def test_pipeline_generator_multi_job_matrix_services():
    report = FrameworkDetectionReport(
        primary_language="Python",
        detected_frameworks=["FastAPI"],
        build_tool="pip",
        test_runner="pytest",
        linter="ruff",
        has_docker=True,
        has_tests=True,
        has_linting=True,
        recommended_matrix={"python-version": ["3.11", "3.12"]},
        manifest_paths=["requirements.txt"]
    )

    result = pipeline_generator.generate(
        report=report,
        workflow_name="Custom CI Test",
        branches=["main", "staging"],
        include_linting=True,
        include_tests=True,
        include_matrix=True,
        include_docker=True,
        include_services=["postgres", "redis"]
    )

    assert result.workflow_name == "Custom CI Test"
    assert "lint" in result.jobs
    assert "test" in result.jobs
    assert "docker-build" in result.jobs
    assert result.matrix_enabled is True
    assert result.has_docker_job is True
    assert result.has_services is True

    yaml_text = result.yaml_content
    assert 'name: "Custom CI Test"' in yaml_text
    assert "actions/checkout@v4" in yaml_text
    assert "actions/setup-python@v5" in yaml_text
    assert "postgres:15-alpine" in yaml_text
    assert "redis:7-alpine" in yaml_text
    assert "matrix:" in yaml_text
    assert "python-version:" in yaml_text


def test_yaml_validator_valid_and_schema():
    valid_wf = """name: "DevPilot CI"
on:
  push:
    branches: ["main"]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: echo "hello world"
"""
    val = yaml_validator.validate(valid_wf)
    assert val.is_valid is True
    assert val.syntax_valid is True
    assert val.schema_valid is True
    assert len(val.errors) == 0
    assert "test" in val.jobs_detected


def test_yaml_validator_deprecated_action_and_linting():
    bad_wf = """name: "Deprecated CI"
on:
  push:
    branches: ["main"]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: curl -sSf https://example.com/install.sh | bash
"""
    val = yaml_validator.validate(bad_wf)
    assert any("deprecated" in w.lower() for w in val.warnings)
    assert any("actions/checkout@v4" in w for w in val.warnings)
    assert any("curl" in str(issue).lower() for issue in val.lint_issues)


def test_cicd_endpoints(client, db):
    # 1. Detect framework API
    det_res = client.post("/api/cicd/detect-framework/default-repo")
    assert det_res.status_code == 200
    data = det_res.json()
    assert "primary_language" in data
    assert "build_tool" in data

    # 2. Generate workflow API
    gen_res = client.post("/api/cicd/generate", json={
        "repository_id": "default-repo",
        "workflow_name": "API Generated CI",
        "include_linting": True,
        "include_tests": True,
        "include_docker": False
    })
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert gen_data["validation_status"] == "VALID"
    assert "actions/checkout@v4" in gen_data["workflow_yaml"]

    # 3. Validate workflow API
    val_res = client.post("/api/cicd/validate-workflow", json={
        "workflow_yaml": gen_data["workflow_yaml"]
    })
    assert val_res.status_code == 200
    assert val_res.json()["is_valid"] is True

    # 4. Commit workflow API
    commit_res = client.post("/api/cicd/commit-workflow", json={
        "repository_id": "default-repo",
        "workflow_yaml": gen_data["workflow_yaml"],
        "file_path": ".github/workflows/ci.yml",
        "branch_name": "devpilot/setup-cicd",
        "commit_message": "ci: add automated workflow"
    })
    assert commit_res.status_code == 200
    cdata = commit_res.json()
    assert cdata["success"] is True
    assert cdata["branch_name"] == "devpilot/setup-cicd"

    # 5. Trigger run API
    trigger_res = client.post("/api/cicd/trigger-run/default-repo", json={
        "repository_id": "default-repo",
        "workflow_name": "API Generated CI",
        "branch_name": "devpilot/setup-cicd"
    })
    assert trigger_res.status_code == 200
    trig_data = trigger_res.json()
    assert trig_data["status"] == "completed"
    assert trig_data["conclusion"] == "success"
    assert trig_data["branch_name"] == "devpilot/setup-cicd"

    # 6. List runs API
    runs_res = client.get("/api/cicd/runs")
    assert runs_res.status_code == 200
    assert len(runs_res.json()) >= 1

    # 7. Analyze run API
    run_id = trig_data["id"]
    analyze_res = client.post(f"/api/cicd/runs/{run_id}/analyse")
    assert analyze_res.status_code == 200
    assert "failure_category" in analyze_res.json()
