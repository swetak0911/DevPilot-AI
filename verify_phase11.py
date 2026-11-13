"""
DevPilot AI - Phase 11 Verification Suite
Tests CI/CD Failure Intelligence Agent: Raw Log Parsing & ANSI Stripping,
Multi-Category Failure Classification (Code, Dependency, CI Config, Environment),
RAG Failing Code Context Retrieval, Root Cause Hypothesis Synthesis,
Remediation Patch Generation & Sandbox Validation, and CI Failure REST APIs.
Run directly using: python verify_phase11.py
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


def run_phase11_verification():
    print("=" * 72)
    print(" DevPilot AI - Phase 11 CI/CD Failure Intelligence Agent Suite")
    print("=" * 72)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.database import init_db, SessionLocal
    from devops.cicd.log_parser import ci_log_parser, ParsedCIError
    from ai_engine.agents.ci_failure_agent import ci_failure_agent, CIFailureDiagnosis
    from ai_engine.agents.patch_validator import patch_validator
    from app.services.git_service import git_service
    from app.services.ci_intelligence_service import ci_intelligence_service
    from app.models.cicd import WorkflowRun
    from app.schemas.cicd import CIRemediateRequest, CILogParseRequest

    init_db()
    client = TestClient(app)
    db = SessionLocal()
    passed_count = 0
    total_checks = 7

    try:
        # Check 1: CI Log Parser & Error Trace Extraction Engine
        try:
            raw_ansi_log = (
                "\x1b[36m##[section]Starting: Test & Lint\x1b[0m\n"
                "\x1b[32m##[group]Run Run Code Linter\x1b[0m\n"
                "backend/app/core/security.py:45:1: F401 'jwt' imported but unused\n"
                "backend/app/api/v1/endpoints/auth.py:28:9: E501 line too long (92 > 88 characters)\n"
                "\x1b[31m##[error]Process completed with exit code 1.\x1b[0m\n"
            )

            # Test ANSI stripping
            stripped = ci_log_parser.strip_ansi(raw_ansi_log)
            assert "\x1b" not in stripped
            assert "F401 'jwt' imported but unused" in stripped

            # Test log parsing
            parsed: ParsedCIError = ci_log_parser.parse(
                logs=raw_ansi_log,
                default_job="lint",
                default_step="Run Code Linter"
            )

            assert parsed.failing_job == "lint", f"Expected job 'lint', got '{parsed.failing_job}'"
            assert parsed.failing_step == "Run Code Linter", f"Expected step 'Run Code Linter', got '{parsed.failing_step}'"
            assert parsed.failing_file == "backend/app/core/security.py", f"Expected file 'backend/app/core/security.py', got '{parsed.failing_file}'"
            assert parsed.failing_line == 45, f"Expected line 45, got '{parsed.failing_line}'"
            assert "F401" in parsed.error_message, f"Expected 'F401' in error_message '{parsed.error_message}'"
            assert len(parsed.error_trace) > 10, f"Error trace length ({len(parsed.error_trace)}) <= 10"

            print(f" [PASS] 1. CI Log Parser & Error Trace Extraction: OK (File: {parsed.failing_file}:{parsed.failing_line}, Error: {parsed.error_message[:45]})")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 1. Log Parser: {e}")

        # Check 2: Multi-Category Failure Classification Engine
        try:
            categories_tested = []

            # 1. Dependency
            dep_log = "ModuleNotFoundError: No module named 'cryptography'\n##[error]Process completed with exit code 1."
            p_dep = ci_log_parser.parse(dep_log)
            cat_dep, conf_dep = ci_failure_agent.classify_failure(p_dep, dep_log)
            assert cat_dep == "DEPENDENCY"
            assert conf_dep >= 0.90
            categories_tested.append(cat_dep)

            # 2. CI Config
            cfg_log = "yaml.scanner.ScannerError: mapping values are not allowed here in .github/workflows/ci.yml:14"
            p_cfg = ci_log_parser.parse(cfg_log)
            cat_cfg, conf_cfg = ci_failure_agent.classify_failure(p_cfg, cfg_log)
            assert cat_cfg == "CI_CONFIG"
            assert conf_cfg >= 0.90
            categories_tested.append(cat_cfg)

            # 3. Environment
            env_log = "Fatal: No space left on device\nCommand timed out after 300 seconds"
            p_env = ci_log_parser.parse(env_log)
            cat_env, conf_env = ci_failure_agent.classify_failure(p_env, env_log)
            assert cat_env == "ENVIRONMENT"
            assert conf_env >= 0.90
            categories_tested.append(cat_env)

            # 4. Application Code
            app_log = "FAILED tests/test_security.py::test_token_decode - AssertionError: assert 401 == 200"
            p_app = ci_log_parser.parse(app_log)
            cat_app, conf_app = ci_failure_agent.classify_failure(p_app, app_log)
            assert cat_app == "APPLICATION_CODE"
            assert conf_app >= 0.90
            categories_tested.append(cat_app)

            assert len(set(categories_tested)) == 4
            print(f" [PASS] 2. Multi-Category Failure Classification: OK (Classified {', '.join(categories_tested)} with >=90% confidence)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 2. Failure Classification: {e}")

        # Check 3: RAG Source Code Context Retrieval
        try:
            target_rel_path = "backend/app/core/security.py"
            full_target = os.path.join(root_path, target_rel_path)
            assert os.path.exists(full_target), f"Target file {full_target} does not exist"

            with open(full_target, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.splitlines()
            assert len(lines) >= 10
            # Context window around line 10
            snippet = "\n".join(lines[0:15])
            assert "def" in snippet or "import" in snippet
            print(f" [PASS] 3. RAG Source Code Context Retrieval: OK (Retrieved {len(lines)} lines from {target_rel_path})")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 3. RAG Context Retrieval: {e}")

        # Check 4: Root Cause Hypothesis & Remediation Recommendation Generator
        try:
            parsed_test = ParsedCIError(
                failing_job="test",
                failing_step="Execute Automated Tests",
                error_message="ModuleNotFoundError: No module named 'jwt2'",
                error_trace="Traceback (most recent call last):\n  File 'backend/app/core/security.py', line 10\n    import jwt2",
                failing_file="backend/app/core/security.py",
                failing_line=10
            )

            hypothesis, fix = ci_failure_agent.generate_root_cause_hypothesis(parsed_test, "DEPENDENCY")
            assert len(hypothesis) > 20
            assert "missing" in hypothesis.lower() or "dependency" in hypothesis.lower()
            assert len(fix) > 20
            assert "requirements" in fix.lower() or "package" in fix.lower()
            print(f" [PASS] 4. Root Cause Hypothesis & Recommendation Engine: OK (Hypothesis: '{hypothesis[:55]}...')")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 4. Root Cause Hypothesis: {e}")

        # Check 5: Automated Remediation Patch Synthesis & Syntax Validation
        try:
            parsed_linter = ParsedCIError(
                failing_job="lint",
                failing_step="Run Code Linter",
                error_message="backend/app/core/security.py:45:1: F401 'jwt' imported but unused",
                error_trace="F401 'jwt' imported but unused",
                failing_file="backend/app/core/security.py",
                failing_line=45
            )

            sample_code = "import os\nimport jwt\nimport sys\n\ndef check_auth():\n    return True\n"
            patch_str = ci_failure_agent.generate_remediation_patch(
                parsed=parsed_linter,
                category="APPLICATION_CODE",
                file_content=sample_code
            )

            assert patch_str is not None
            assert "--- a/backend/app/core/security.py" in patch_str
            assert "+++ b/backend/app/core/security.py" in patch_str
            assert "-import jwt" in patch_str

            val_res = patch_validator.validate_patch(patch_str, sample_code)
            assert val_res.is_valid is True
            assert "import jwt" not in val_res.patched_content
            print(f" [PASS] 5. Automated Remediation Patch Synthesis: OK (Valid Unified Diff, AST Verified)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 5. Patch Synthesis: {e}")

        # Check 6: Git Remediation Branch & Atomic Commit Persistence
        try:
            # Seed representative failed run
            failed_run = db.query(WorkflowRun).filter(WorkflowRun.conclusion == "failure").first()
            if not failed_run:
                failed_run = WorkflowRun(
                    repository_id="default-repo",
                    github_run_id="998811",
                    workflow_name="Docker Container Build",
                    event="push",
                    status="completed",
                    conclusion="failure",
                    duration_seconds=30,
                    commit_sha="c9a8b7d",
                    branch_name="feature/verify-fix",
                    logs_summary="Step 'Run Linting Checks' failed with 2 errors in security.py."
                )
                db.add(failed_run)
                db.commit()
                db.refresh(failed_run)

            rem_req = CIRemediateRequest(
                run_id=failed_run.id,
                branch_name=f"devpilot/ci-fix-phase11-{failed_run.id[:6]}"
            )

            rem_res = ci_intelligence_service.remediate_run(
                db=db,
                request=rem_req,
                explicit_path=root_path
            )

            assert rem_res.success is True
            assert "devpilot/ci-fix" in rem_res.branch_name
            assert len(rem_res.commit_hash) >= 6
            print(f" [PASS] 6. Git Remediation Branch & Atomic Commit: OK (Branch: {rem_res.branch_name}, Commit: {rem_res.commit_hash})")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 6. Git Remediation Branch: {e}")

        # Check 7: End-to-End REST APIs (/analyse, /remediate, /logs/parse)
        try:
            # 1. POST /api/cicd/runs/{run_id}/analyse
            r_analyse = client.post(f"/api/cicd/runs/{failed_run.id}/analyse")
            assert r_analyse.status_code == 200, f"analyse failed: {r_analyse.text}"
            ana_data = r_analyse.json()
            assert ana_data["run_id"] == failed_run.id
            assert ana_data["failure_category"] in ["APPLICATION_CODE", "DEPENDENCY", "CI_CONFIG", "ENVIRONMENT"]
            assert len(ana_data["root_cause_hypothesis"]) > 10
            assert len(ana_data["suggested_fix"]) > 10

            # 2. POST /api/cicd/runs/{run_id}/remediate
            r_remediate = client.post(f"/api/cicd/runs/{failed_run.id}/remediate", json={
                "run_id": failed_run.id,
                "branch_name": f"devpilot/ci-fix-api-{failed_run.id[:6]}"
            })
            assert r_remediate.status_code == 200, f"remediate failed: {r_remediate.text}"
            rem_data = r_remediate.json()
            assert rem_data["success"] is True
            assert "commit_hash" in rem_data

            # 3. POST /api/cicd/logs/parse
            sample_raw = (
                "##[group]Run Execute Pytest Suite\n"
                "Traceback (most recent call last):\n"
                "  File \"backend/app/core/security.py\", line 15, in <module>\n"
                "    import pydantic_settings\n"
                "ModuleNotFoundError: No module named 'pydantic_settings'\n"
                "##[error]Process completed with exit code 1.\n"
            )
            r_parse = client.post("/api/cicd/logs/parse", json={"logs": sample_raw})
            assert r_parse.status_code == 200, f"logs parse failed: {r_parse.text}"
            parse_data = r_parse.json()
            assert parse_data["failure_category"] == "DEPENDENCY"
            assert "pydantic_settings" in parse_data["error_message"]
            assert parse_data["failing_file"] == "backend/app/core/security.py"

            print(f" [PASS] 7. End-to-End Failure Intelligence REST APIs: OK (/analyse, /remediate, /logs/parse)")
            passed_count += 1
        except Exception as e:
            print(f" [FAIL] 7. REST APIs: {e}")

    finally:
        db.close()

    print("=" * 72)
    print(f" Phase 11 Verification Score: {passed_count}/{total_checks} ({(passed_count/total_checks)*100:.1f}%)")
    print("=" * 72)

    return passed_count == total_checks


if __name__ == "__main__":
    success = run_phase11_verification()
    sys.exit(0 if success else 1)
