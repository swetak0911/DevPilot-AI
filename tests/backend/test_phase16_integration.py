"""
DevPilot AI - Phase 16 Final Integration & Deployment Verification Tests
Validates end-to-end Workflow A (Software Engineering Loop), Workflow B (DevOps Delivery Loop),
SWE-bench Lite benchmark evaluation harness, static secret scanner & path traversal guard,
and production Docker Compose & Nginx deployment assets.
"""
import os
import json
import pytest

from app.core.database import init_db
from app.services.workflow_integration_service import workflow_integration_service, WorkflowExecutionReport
from ai_engine.evaluation.swe_bench_evaluator import swe_bench_evaluator, SWEBenchSuiteReport
from devops.security.secret_scanner import secret_scanner, SecurityAuditReport


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


def test_workflow_a_software_engineering_loop():
    """Verifies end-to-end Workflow A from CodeBERT defect detection to git commit."""
    report: WorkflowExecutionReport = workflow_integration_service.execute_workflow_a("test-repo-wf-a")
    assert report.overall_status == "SUCCESS", f"Workflow A failed: {report.steps}"
    assert report.total_steps == 7
    assert report.passed_steps == 7
    for step in report.steps:
        assert step.status == "PASS", f"Step '{step.step_name}' failed with details: {step.details}"


def test_workflow_b_devops_delivery_loop():
    """Verifies end-to-end Workflow B from CI/CD pipeline to ML deployment risk and Prometheus."""
    report: WorkflowExecutionReport = workflow_integration_service.execute_workflow_b("test-repo-wf-b")
    assert report.overall_status == "SUCCESS", f"Workflow B failed: {report.steps}"
    assert report.total_steps == 8
    assert report.passed_steps == 8
    for step in report.steps:
        assert step.status == "PASS", f"Step '{step.step_name}' failed with details: {step.details}"


def test_swe_bench_lite_benchmark():
    """Verifies SWE-bench Lite synthetic benchmark execution, Pass@1, AST validity, and persistence."""
    report: SWEBenchSuiteReport = swe_bench_evaluator.run_benchmark_suite()
    assert report.total_instances == 4
    assert report.resolution_rate >= 0.75, f"Resolution rate {report.resolution_rate} below 75%"
    assert report.ast_validity_rate >= 0.75, f"AST validity rate {report.ast_validity_rate} below 75%"
    assert report.avg_latency_seconds > 0.0
    assert os.path.exists(swe_bench_evaluator.BENCHMARK_RESULTS_PATH)

    with open(swe_bench_evaluator.BENCHMARK_RESULTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["total_instances"] == 4
    assert len(data["instances"]) == 4


def test_security_audit_secret_scanner():
    """Verifies static secret scanning, credential pattern matching, and path traversal guards."""
    vulnerable_snippet = (
        '# Leaked credential sample\n'
        'AWS_KEY = "AKIA1234567890ABCDEF"\n'
        'SECRET_KEY = "devpilot_secret_key_abcdef1234567890"\n'
    )
    findings = secret_scanner.scan_content(vulnerable_snippet, "config/secrets.py")
    assert len(findings) >= 2
    rule_ids = [f.rule_id for f in findings]
    assert "SEC_AWS_KEY" in rule_ids
    assert "SEC_GENERIC_KEY" in rule_ids

    # Path traversal validation
    base_dir = os.path.abspath(os.path.dirname(__file__))
    assert secret_scanner.check_path_traversal("safe_file.py", base_dir) is True
    assert secret_scanner.check_path_traversal("../../etc/passwd", base_dir) is False
    assert secret_scanner.check_path_traversal("subdir/../../outside.py", base_dir) is False


def test_production_deployment_assets():
    """Verifies production Docker Compose, Nginx reverse proxy, and multi-stage Dockerfiles."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # 1. docker-compose.prod.yml
    prod_compose_path = os.path.join(root_dir, "docker-compose.prod.yml")
    assert os.path.exists(prod_compose_path)
    with open(prod_compose_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "devpilot-prod-backend" in content
    assert "devpilot-prod-frontend" in content
    assert "devpilot-prod-postgres" in content
    assert "devpilot-prod-redis" in content
    assert "devpilot-prod-prometheus" in content
    assert "devpilot-prod-grafana" in content

    # 2. frontend/nginx.conf
    nginx_path = os.path.join(root_dir, "frontend", "nginx.conf")
    assert os.path.exists(nginx_path)
    with open(nginx_path, "r", encoding="utf-8") as f:
        nginx_content = f.read()
    assert "proxy_pass http://backend:8000/api/;" in nginx_content
    assert "X-Frame-Options" in nginx_content
    assert "try_files $uri $uri/ /index.html;" in nginx_content

    # 3. frontend/Dockerfile.prod
    dockerfile_prod_path = os.path.join(root_dir, "frontend", "Dockerfile.prod")
    assert os.path.exists(dockerfile_prod_path)
    with open(dockerfile_prod_path, "r", encoding="utf-8") as f:
        df_content = f.read()
    assert "FROM node:20-alpine AS builder" in df_content
    assert "FROM nginx:1.25-alpine AS runner" in df_content
    assert "COPY --from=builder /app/dist /usr/share/nginx/html" in df_content
