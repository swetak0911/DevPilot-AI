"""
DevPilot AI - Phase 10 Verification Suite
Tests AI CI/CD Pipeline Generator: Multi-Language Framework Detection,
Multi-Job GitHub Actions Synthesis, Strict YAML Schema Validation,
Action Deprecation & Security Linter, Git Branch Commits, and CI/CD REST APIs.
Run directly using: python verify_phase10.py
"""
import sys
import os
import tempfile
import uuid

# Add root directory and backend directory to sys.path
root_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(root_path, "backend")
if root_path not in sys.path:
    sys.path.insert(0, root_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


def run_phase10_verification():
    print("=" * 72)
    print(" DevPilot AI - Phase 10 AI CI/CD Pipeline Generator Suite")
    print("=" * 72)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import init_db, SessionLocal
    from devops.cicd.framework_detector import framework_detector, FrameworkDetectionReport
    from devops.cicd.pipeline_generator import pipeline_generator, PipelineGenerationResult
    from devops.cicd.yaml_validator import yaml_validator, WorkflowValidationResult
    from app.services.git_service import git_service
    from app.services.cicd_service import cicd_service
    from app.models.repository import Repository
    from app.models.cicd import WorkflowRun
    from app.schemas.cicd import WorkflowGenerateRequest, WorkflowCommitRequest, WorkflowDispatchTriggerRequest

    init_db()
    client = TestClient(app)
    db = SessionLocal()
    passed_count = 0
    total_checks = 7

    try:
        # Check 1: Multi-Language Framework & Toolchain Detection Engine
        try:
            # 1. Python Detection
            py_report = framework_detector.detect_from_file_list(
                root_path,
                ["backend/requirements.txt", "backend/app/main.py", "tests/test_api.py", "Dockerfile"]
            )
            assert py_report.primary_language == "Python"
            assert py_report.build_tool == "pip"
            assert py_report.test_runner == "pytest"
            assert py_report.linter in ["ruff", "flake8"]
            assert py_report.has_docker is True
            assert py_report.has_tests is True
            assert "python-version" in py_report.recommended_matrix

            # 2. Node.js / TypeScript Detection
            ts_report = framework_detector.detect_from_file_list(
                "/tmp/mock_node",
                ["package.json", "src/index.tsx", "pnpm-lock.yaml", "vitest.config.ts"]
            )
            assert ts_report.primary_language == "TypeScript"
            assert ts_report.build_tool == "pnpm"
            assert ts_report.linter == "eslint"
            assert "node-version" in ts_report.recommended_matrix

            # 3. Go, Rust & Java Detections
            go_report = framework_detector.detect_from_file_list("/tmp/mock_go", ["go.mod", "main.go"])
            assert go_report.primary_language == "Go"
            assert go_report.test_runner == "go test ./..."

            rust_report = framework_detector.detect_from_file_list("/tmp/mock_rust", ["Cargo.toml", "src/main.rs"])
            assert rust_report.primary_language == "Rust"
            assert rust_report.test_runner == "cargo test"

            java_report = framework_detector.detect_from_file_list("/tmp/mock_java", ["pom.xml", "src/Main.java"])
            assert java_report.primary_language == "Java"
            assert java_report.build_tool == "maven"

            print(f" [PASS] 1. Multi-Language Framework & Toolchain Detection: OK (Python, TS, Go, Rust, Java verified)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 1. Framework Detection: {e}")

        # Check 2: Multi-Job GitHub Actions Workflow Generation
        try:
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
                manifest_paths=["backend/requirements.txt"]
            )

            gen_result = pipeline_generator.generate(
                report=report,
                workflow_name="DevPilot CI Full Pipeline",
                branches=["main", "release/*"],
                include_linting=True,
                include_tests=True,
                include_matrix=True,
                include_docker=True,
                include_services=["postgres", "redis"],
                environment_vars={"DEV_ENV": "testing"}
            )

            assert gen_result.workflow_name == "DevPilot CI Full Pipeline"
            assert set(gen_result.jobs) == {"lint", "test", "docker-build"}
            assert gen_result.matrix_enabled is True
            assert gen_result.has_docker_job is True
            assert gen_result.has_services is True

            yaml_text = gen_result.yaml_content
            assert 'name: "DevPilot CI Full Pipeline"' in yaml_text
            assert "actions/checkout@v4" in yaml_text
            assert "actions/setup-python@v5" in yaml_text
            assert "postgres:15-alpine" in yaml_text
            assert "redis:7-alpine" in yaml_text
            assert "strategy:" in yaml_text
            assert "matrix:" in yaml_text
            assert "actions/upload-artifact@v4" in yaml_text
            assert "docker/build-push-action@v5" in yaml_text
            print(f" [PASS] 2. Multi-Job GitHub Actions Synthesis: OK ({len(gen_result.jobs)} jobs, Matrix + Postgres/Redis + Docker)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 2. Workflow Generation: {e}")

        # Check 3: Strict YAML Syntax & GitHub Actions Schema Validation
        try:
            # Valid workflow test
            val_ok = yaml_validator.validate(gen_result.yaml_content)
            assert val_ok.is_valid is True
            assert val_ok.syntax_valid is True
            assert val_ok.schema_valid is True
            assert len(val_ok.errors) == 0
            assert set(val_ok.jobs_detected) == {"lint", "test", "docker-build"}

            # Invalid syntax test
            broken_yaml = "name: Broken CI\njobs: test: [invalid yaml"
            val_broken = yaml_validator.validate(broken_yaml)
            assert val_broken.is_valid is False
            assert val_broken.syntax_valid is False
            assert len(val_broken.errors) >= 1

            # Missing schema test (no jobs)
            missing_jobs = "name: No Jobs CI\non:\n  push:\n    branches: ['main']"
            val_missing = yaml_validator.validate(missing_jobs)
            assert val_missing.is_valid is False
            assert val_missing.schema_valid is False
            assert any("jobs" in err.lower() for err in val_missing.errors)
            print(f" [PASS] 3. Strict YAML Syntax & Schema Validation: OK (Syntax, Structure, Jobs hierarchy verified)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 3. YAML Validation: {e}")

        # Check 4: GitHub Actions Security & Deprecation Linter Engine
        try:
            risky_workflow = """name: "Insecure Workflow"
on:
  push:
    branches: ["main"]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repo
        uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v3
        with:
          python-version: "3.10"
      - name: Run Script
        run: curl -sSf https://install.example.com | bash
"""
            lint_res = yaml_validator.validate(risky_workflow)
            # Deprecated actions flagged in warnings
            has_dep_checkout = any("actions/checkout@v2" in w and "actions/checkout@v4" in w for w in lint_res.warnings)
            has_dep_python = any("actions/setup-python@v3" in w and "actions/setup-python@v5" in w for w in lint_res.warnings)
            assert has_dep_checkout, "Failed to flag deprecated actions/checkout@v2"
            assert has_dep_python, "Failed to flag deprecated actions/setup-python@v3"

            # Security check for curl | bash
            has_curl_pipe = any("curl-pipe" in issue.get("rule", "") for issue in lint_res.lint_issues)
            assert has_curl_pipe, "Failed to detect dangerous curl | bash pattern"
            print(f" [PASS] 4. Security & Deprecation Linter: OK (Flagged checkout@v2, python@v3, and curl|bash pipeline)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 4. Security & Deprecation Linter: {e}")

        # Check 5: Git Branching & Atomic Workflow Commit to Repository
        try:
            workflow_content = gen_result.yaml_content
            commit_result = git_service.apply_patch_and_commit(
                repo_path=root_path,
                file_path=".github/workflows/devpilot-test-ci.yml",
                modified_content=workflow_content,
                commit_message="ci: automated test workflow deployment",
                branch_name="devpilot/verify-cicd"
            )
            assert commit_result["success"] is True
            assert "commit_hash" in commit_result
            assert len(commit_result["commit_hash"]) >= 6

            # Verify file exists on disk
            target_file = os.path.join(root_path, ".github/workflows/devpilot-test-ci.yml")
            assert os.path.exists(target_file)
            with open(target_file, "r", encoding="utf-8") as f:
                saved_text = f.read()
            assert "actions/checkout@v4" in saved_text
            print(f" [PASS] 5. Git Branching & Atomic Workflow Commit: OK (Commit: {commit_result['commit_hash']}, File: .github/workflows/devpilot-test-ci.yml)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 5. Git Branching & Commit: {e}")

        # Check 6: Workflow Run Execution & Job Steps Tracking
        try:
            trigger_req = WorkflowDispatchTriggerRequest(
                repository_id="default-repo",
                workflow_name="DevPilot CI Full Pipeline",
                branch_name="devpilot/verify-cicd"
            )
            run_instance = cicd_service.trigger_workflow_run(db, trigger_req, explicit_path=root_path)

            assert run_instance.id is not None
            assert run_instance.status == "completed"
            assert run_instance.conclusion == "success"
            assert run_instance.branch_name == "devpilot/verify-cicd"
            assert run_instance.duration_seconds > 0
            assert isinstance(run_instance.jobs_data, list)
            assert len(run_instance.jobs_data) >= 2
            job_ids = [j["job_id"] for j in run_instance.jobs_data]
            assert "lint" in job_ids
            assert "test" in job_ids

            # Query from DB to confirm persistence
            retrieved = db.query(WorkflowRun).filter(WorkflowRun.id == run_instance.id).first()
            assert retrieved is not None
            assert retrieved.branch_name == "devpilot/verify-cicd"
            print(f" [PASS] 6. Workflow Run Execution & Job Steps Tracking: OK (Run ID: {retrieved.id[:8]}, Branch: {retrieved.branch_name}, 2 Jobs Tracked)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 6. Workflow Run Tracking: {e}")

        # Check 7: End-to-End REST APIs Verification
        try:
            # 1. POST /api/cicd/detect-framework/{repo_id}
            r_detect = client.post("/api/cicd/detect-framework/default-repo")
            assert r_detect.status_code == 200, f"detect failed: {r_detect.text}"
            det_data = r_detect.json()
            assert det_data["primary_language"] == "Python"
            assert det_data["build_tool"] == "pip"

            # 2. POST /api/cicd/generate
            r_gen = client.post("/api/cicd/generate", json={
                "repository_id": "default-repo",
                "workflow_name": "API CI Workflow",
                "include_linting": True,
                "include_tests": True,
                "include_docker": False
            })
            assert r_gen.status_code == 200, f"generate failed: {r_gen.text}"
            gen_data = r_gen.json()
            assert gen_data["validation_status"] == "VALID"
            assert "workflow_yaml" in gen_data

            # 3. POST /api/cicd/validate-workflow
            r_val = client.post("/api/cicd/validate-workflow", json={
                "workflow_yaml": gen_data["workflow_yaml"]
            })
            assert r_val.status_code == 200, f"validate failed: {r_val.text}"
            assert r_val.json()["is_valid"] is True

            # 4. POST /api/cicd/commit-workflow
            r_com = client.post("/api/cicd/commit-workflow", json={
                "repository_id": "default-repo",
                "workflow_yaml": gen_data["workflow_yaml"],
                "file_path": ".github/workflows/ci.yml",
                "branch_name": "devpilot/api-cicd",
                "commit_message": "ci: commit via API"
            })
            assert r_com.status_code == 200, f"commit failed: {r_com.text}"
            assert r_com.json()["success"] is True

            # 5. POST /api/cicd/trigger-run/{repo_id}
            r_trig = client.post("/api/cicd/trigger-run/default-repo", json={
                "repository_id": "default-repo",
                "workflow_name": "API CI Workflow",
                "branch_name": "devpilot/api-cicd"
            })
            assert r_trig.status_code == 200, f"trigger failed: {r_trig.text}"
            trig_data = r_trig.json()
            assert trig_data["status"] == "completed"
            assert trig_data["conclusion"] == "success"

            # 6. GET /api/cicd/runs and GET /api/cicd/runs/{run_id}
            r_runs = client.get("/api/cicd/runs")
            assert r_runs.status_code == 200, f"runs failed: {r_runs.text}"
            runs_list = r_runs.json()
            assert len(runs_list) >= 1

            r_single = client.get(f"/api/cicd/runs/{trig_data['id']}")
            assert r_single.status_code == 200, f"get single run failed: {r_single.text}"
            assert r_single.json()["id"] == trig_data["id"]

            # 7. POST /api/cicd/runs/{run_id}/analyse
            r_ana = client.post(f"/api/cicd/runs/{trig_data['id']}/analyse")
            assert r_ana.status_code == 200, f"analyse failed: {r_ana.text}"
            assert "root_cause_hypothesis" in r_ana.json()

            print(f" [PASS] 7. End-to-End REST APIs: OK (/detect-framework, /generate, /validate, /commit, /trigger-run, /runs, /analyse)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 7. REST APIs: {e}")

    finally:
        db.close()

    print("=" * 72)
    print(f" Phase 10 Verification Score: {passed_count}/{total_checks} ({(passed_count/total_checks)*100:.1f}%)")
    print("=" * 72)

    return passed_count == total_checks


if __name__ == "__main__":
    success = run_phase10_verification()
    sys.exit(0 if success else 1)
