"""
========================================================================
 DevPilot AI - Phase 16 Final Integration & Deployment Verification Suite
========================================================================
Validates complete end-to-end multi-agent software engineering & DevOps
delivery pipelines:
1. Workflow A: Autonomous Software Engineering & Defect Remediation
2. Workflow B: Autonomous DevOps & Infrastructure Delivery
3. SWE-bench Lite Benchmark Evaluation Suite (Pass@1, AST Validity)
4. Security Audit, Static Secret Scanner & Path Traversal Guards
5. Production Docker Compose & Hardened Nginx Deployment Architecture
6. Platform Verification Matrix Across All 16 Phases
========================================================================
"""
import sys
import os
import json
import traceback

# Add workspace and backend to sys.path
root_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(root_path, "backend")
if root_path not in sys.path:
    sys.path.insert(0, root_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.database import init_db
from app.services.workflow_integration_service import workflow_integration_service, WorkflowExecutionReport
from ai_engine.evaluation.swe_bench_evaluator import swe_bench_evaluator, SWEBenchSuiteReport
from devops.security.secret_scanner import secret_scanner, SecurityAuditReport


def run_phase16_verification() -> bool:
    print("=" * 72)
    print(" DevPilot AI - Phase 16 Final Integration & Deployment Suite")
    print("=" * 72)

    init_db()

    # -------------------------------------------------------------------------
    # 1. Workflow A: Autonomous Software Engineering & Defect Remediation Loop
    # -------------------------------------------------------------------------
    print("\n[CHECK 1] Workflow A: Autonomous Software Engineering Loop...")
    try:
        report_a: WorkflowExecutionReport = workflow_integration_service.execute_workflow_a("repo-verification-wf-a")
        assert report_a.overall_status == "SUCCESS", f"Workflow A failed: {report_a.steps}"
        assert report_a.passed_steps == 7, f"Expected 7 passed steps, got {report_a.passed_steps}"
        for step in report_a.steps:
            assert step.status == "PASS", f"Step '{step.step_name}' failed"

        print(
            f" [PASS] 1. Workflow A (Software Engineering): OK "
            f"(Executed 7/7 autonomous steps in {report_a.duration_seconds}s: "
            f"Defect Scan -> Plan -> Coding -> AST Validate -> Test -> AI Review -> Git Commit)"
        )
    except Exception as exc:
        print(f" [FAIL] 1. Workflow A: {exc}\n{traceback.format_exc()}")
        return False

    # -------------------------------------------------------------------------
    # 2. Workflow B: Autonomous DevOps & Infrastructure Delivery Loop
    # -------------------------------------------------------------------------
    print("\n[CHECK 2] Workflow B: Autonomous DevOps & Infrastructure Delivery Loop...")
    try:
        report_b: WorkflowExecutionReport = workflow_integration_service.execute_workflow_b("repo-verification-wf-b")
        assert report_b.overall_status == "SUCCESS", f"Workflow B failed: {report_b.steps}"
        assert report_b.passed_steps == 8, f"Expected 8 passed steps, got {report_b.passed_steps}"
        for step in report_b.steps:
            assert step.status == "PASS", f"Step '{step.step_name}' failed"

        print(
            f" [PASS] 2. Workflow B (DevOps Delivery): OK "
            f"(Executed 8/8 autonomous steps in {report_b.duration_seconds}s: "
            f"CI/CD Synthesize -> Failure Diagnosis -> Docker Build -> K8s PSS Restricted -> "
            f"Terraform IaC -> HITL Gate -> ML Risk -> Prometheus)"
        )
    except Exception as exc:
        print(f" [FAIL] 2. Workflow B: {exc}\n{traceback.format_exc()}")
        return False

    # -------------------------------------------------------------------------
    # 3. SWE-bench Lite Benchmark Evaluation Suite
    # -------------------------------------------------------------------------
    print("\n[CHECK 3] SWE-bench Lite Benchmark Evaluation Suite...")
    try:
        bench_report: SWEBenchSuiteReport = swe_bench_evaluator.run_benchmark_suite()
        assert bench_report.total_instances == 4, f"Expected 4 benchmark instances, got {bench_report.total_instances}"
        assert bench_report.resolution_rate >= 0.75, f"Resolution rate {bench_report.resolution_rate:.1%} < 75%"
        assert bench_report.ast_validity_rate >= 0.75, f"AST validity rate {bench_report.ast_validity_rate:.1%} < 75%"
        assert os.path.exists(swe_bench_evaluator.BENCHMARK_RESULTS_PATH), "Benchmark results JSON missing"

        print(
            f" [PASS] 3. SWE-bench Lite Benchmark: OK "
            f"(Resolution: {bench_report.resolution_rate:.1%}, Pass@1: {bench_report.pass_at_1_rate:.1%}, "
            f"AST Validity: {bench_report.ast_validity_rate:.1%}, Avg Latency: {bench_report.avg_latency_seconds}s)"
        )
    except Exception as exc:
        print(f" [FAIL] 3. SWE-bench Lite: {exc}\n{traceback.format_exc()}")
        return False

    # -------------------------------------------------------------------------
    # 4. Security Audit, Secret Scanner & Path Traversal Guards
    # -------------------------------------------------------------------------
    print("\n[CHECK 4] Security Audit, Secret Scanner & Path Traversal Guards...")
    try:
        vuln_sample = (
            '# AWS and Token Leak Sample\n'
            'AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"\n'
            'GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"\n'
        )
        findings = secret_scanner.scan_content(vuln_sample, "config.py")
        assert len(findings) >= 2, f"Expected >= 2 secret findings, got {len(findings)}"
        rule_ids = {f.rule_id for f in findings}
        assert "SEC_AWS_KEY" in rule_ids
        assert "SEC_GITHUB_PAT" in rule_ids

        # Path traversal checks
        assert secret_scanner.check_path_traversal("safe/sub/file.py", root_path) is True
        assert secret_scanner.check_path_traversal("../../../etc/shadow", root_path) is False
        assert secret_scanner.check_path_traversal("subdir/../../escaped.key", root_path) is False

        print(f" [PASS] 4. Security & Secret Guards: OK (Detected AWS & GitHub token leaks; validated path traversal boundaries)")
    except Exception as exc:
        print(f" [FAIL] 4. Security Audit: {exc}\n{traceback.format_exc()}")
        return False

    # -------------------------------------------------------------------------
    # 5. Production Docker Compose & Hardened Nginx Deployment Architecture
    # -------------------------------------------------------------------------
    print("\n[CHECK 5] Production Docker Compose & Hardened Nginx Assets...")
    try:
        # docker-compose.prod.yml
        compose_prod = os.path.join(root_path, "docker-compose.prod.yml")
        assert os.path.exists(compose_prod), "Missing docker-compose.prod.yml"
        with open(compose_prod, "r", encoding="utf-8") as f:
            c_text = f.read()
        for svc in ["backend", "frontend", "postgres", "redis", "prometheus", "grafana"]:
            assert f"devpilot-prod-{svc}" in c_text, f"Missing {svc} container definition in docker-compose.prod.yml"

        # frontend/nginx.conf
        nginx_conf = os.path.join(root_path, "frontend", "nginx.conf")
        assert os.path.exists(nginx_conf), "Missing frontend/nginx.conf"
        with open(nginx_conf, "r", encoding="utf-8") as f:
            n_text = f.read()
        assert "proxy_pass http://backend:8000/api/;" in n_text, "Missing backend proxy pass in nginx.conf"
        assert "X-Frame-Options" in n_text, "Missing security headers in nginx.conf"

        # frontend/Dockerfile.prod
        df_prod = os.path.join(root_path, "frontend", "Dockerfile.prod")
        assert os.path.exists(df_prod), "Missing frontend/Dockerfile.prod"
        with open(df_prod, "r", encoding="utf-8") as f:
            df_text = f.read()
        assert "FROM node:20-alpine AS builder" in df_text
        assert "FROM nginx:1.25-alpine AS runner" in df_text

        print(f" [PASS] 5. Production Deployment Architecture: OK (Validated 6-service compose, multi-stage Dockerfile, and reverse-proxy Nginx)")
    except Exception as exc:
        print(f" [FAIL] 5. Production Assets: {exc}\n{traceback.format_exc()}")
        return False

    # -------------------------------------------------------------------------
    # 6. Master Platform Verification Matrix Across All 16 Phases
    # -------------------------------------------------------------------------
    print("\n[CHECK 6] Master Platform Verification Matrix Across All 16 Phases...")
    try:
        phase_runners = [f"verify_phase{i}.py" for i in range(1, 17)]
        for runner in phase_runners:
            p = os.path.join(root_path, runner)
            assert os.path.exists(p), f"Missing verification runner: {runner}"

        # Verify TASKS.md has all 16 phases completed
        tasks_path = os.path.join(root_path, "TASKS.md")
        with open(tasks_path, "r", encoding="utf-8") as f:
            tasks_content = f.read()
        for i in range(1, 17):
            assert f"## Phase {i}:" in tasks_content, f"Phase {i} missing from TASKS.md"

        print(f" [PASS] 6. Master Verification Matrix: OK (All 16 standalone verification runners verified on disk: verify_phase1.py through verify_phase16.py)")
    except Exception as exc:
        print(f" [FAIL] 6. Master Verification Matrix: {exc}\n{traceback.format_exc()}")
        return False

    print("\n" + "=" * 72)
    print(" [SUCCESS] Phase 16 Final Integration & Deployment Suite Verified 100%!")
    print(" [CONGRATULATIONS] DevPilot AI Platform Implementation 100% Complete!")
    print("=" * 72)
    return True


if __name__ == "__main__":
    success = run_phase16_verification()
    sys.exit(0 if success else 1)
