"""
DevPilot AI - Phase 15 Monitoring & Observability Test Suite
Tests Prometheus metrics collection, text exposition format, OpenTelemetry distributed tracing,
structured JSON logging, system health probing, audit trail logging, and Grafana dashboard assets.
"""
import os
import json
import logging
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import init_db, SessionLocal
from app.core.tracer import global_tracer, Span
from app.core.logging import JSONFormatter, set_log_context, get_log_context
from devops.monitoring.metrics_collector import metrics_collector
from app.services.health_service import health_service
from app.services.audit_service import audit_service


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


def test_prometheus_metrics_collector():
    """Verifies counter, gauge, histogram observation, and standard Prometheus text exposition format."""
    metrics_collector.inc_counter("test_counter_total", 5.0, {"service": "test", "env": "ci"})
    metrics_collector.set_gauge("test_gauge_val", 42.5, {"cluster": "us-east"})
    metrics_collector.observe_histogram("test_latency_seconds", 0.045, {"endpoint": "/api/test"})

    # Test domain helpers
    metrics_collector.record_http_request("GET", "/api/test", 200, 0.025)
    metrics_collector.record_task_status("BUG_FIX", "COMPLETED")
    metrics_collector.record_agent_execution("CodingAgent", 1.85)
    metrics_collector.record_deployment_risk("repo-p15", 0.15)
    metrics_collector.record_codebert_inference("python", True)

    text_exposition = metrics_collector.generate_exposition()
    assert "# HELP devpilot_http_requests_total" in text_exposition
    assert "# TYPE devpilot_http_requests_total counter" in text_exposition
    assert "devpilot_http_requests_total" in text_exposition
    assert "devpilot_request_duration_seconds_bucket" in text_exposition
    assert "devpilot_deployment_risk_score" in text_exposition
    assert "test_counter_total" in text_exposition
    assert "test_gauge_val" in text_exposition
    assert text_exposition.endswith("\n")


def test_opentelemetry_tracer():
    """Verifies hierarchical span context propagation, timing, attributes, and OTLP export."""
    global_tracer.clear()

    with global_tracer.start_span("agent.pipeline", {"task_id": "task-15-test"}) as root_span:
        root_span.add_event("pipeline_started")
        time_sleep_sim = 0.005
        # Child span
        with global_tracer.start_span("agent.planning") as child_span:
            child_span.set_attribute("plan.steps", 3)
            assert child_span.parent_span_id == root_span.span_id
            assert child_span.trace_id == root_span.trace_id

    recent = global_tracer.get_recent_spans()
    assert len(recent) >= 2
    root_dict = next(s for s in recent if s["name"] == "agent.pipeline")
    child_dict = next(s for s in recent if s["name"] == "agent.planning")
    assert child_dict["parent_span_id"] == root_dict["span_id"]
    assert root_dict["duration_ms"] is not None
    assert root_dict["status"] == "OK"

    # Export OpenTelemetry schema
    otlp = global_tracer.export_opentelemetry()
    assert "resourceSpans" in otlp
    assert len(otlp["resourceSpans"]) > 0
    spans = otlp["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert any(s["name"] == "agent.pipeline" for s in spans)


def test_structured_json_logging():
    """Verifies structured JSON log formatting with correlation contextvars."""
    set_log_context(trace_id="tr-abc-123", span_id="sp-456", task_id="task-789")

    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test message with trace context",
        args=(),
        exc_info=None
    )

    formatted = formatter.format(record)
    log_json = json.loads(formatted)
    assert log_json["message"] == "Test message with trace context"
    assert log_json["level"] == "INFO"
    assert log_json["trace_id"] == "tr-abc-123"
    assert log_json["span_id"] == "sp-456"
    assert log_json["task_id"] == "task-789"
    assert "timestamp" in log_json


def test_system_health_service(db):
    """Verifies system health probes, uptime calculation, database ping latency, and subsystem statuses."""
    health = health_service.get_system_health(db=db)
    assert health["status"] in ("HEALTHY", "DEGRADED", "UNHEALTHY")
    assert health["database_latency_ms"] >= 0.0
    assert health["uptime_seconds"] >= 0.0
    assert "resource_usage" in health
    assert health["resource_usage"]["memory_mb"] > 0
    assert health["resource_usage"]["cpu_percent"] >= 0

    services = health["services"]
    assert services["api_server"] == "ONLINE"
    assert services["database"] == "CONNECTED"
    assert services["codebert_inference"] == "INITIALIZED"
    assert services["docker_sandbox"] == "CONFIGURED"
    assert services["k8s_terraform_engine"] == "READY"
    assert services["ml_deployment_risk"] == "TRAINED"


def test_audit_log_service(db):
    """Verifies security audit logging, filtering, and summary statistics."""
    entry = audit_service.record_event(
        db=db,
        action="TERRAFORM_APPLY_APPROVED",
        resource_type="terraform_plan",
        resource_id="plan-phase15-audit",
        details={"environment": "production", "approver": "lead_devops"},
        ip_address="192.168.1.100"
    )
    assert entry.id is not None
    assert entry.action == "TERRAFORM_APPLY_APPROVED"

    logs = audit_service.list_logs(db=db, action="TERRAFORM_APPLY_APPROVED")
    assert len(logs) >= 1
    matched = next(l for l in logs if l.resource_id == "plan-phase15-audit")
    assert matched.ip_address == "192.168.1.100"
    assert matched.details["approver"] == "lead_devops"

    summary = audit_service.get_audit_summary(db=db)
    assert summary["total_audit_events"] >= 1


def test_grafana_dashboard_definitions():
    """Verifies Grafana JSON schema validity, panel counts, and Prometheus queries."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # 1. Overview Dashboard
    overview_path = os.path.join(root_dir, "devops", "monitoring", "grafana", "dashboards", "devpilot_overview_dashboard.json")
    assert os.path.exists(overview_path)
    with open(overview_path, "r", encoding="utf-8") as f:
        overview_data = json.load(f)
    assert overview_data["uid"] == "devpilot-platform-overview"
    assert len(overview_data["panels"]) >= 8

    # 2. Agent Analytics Dashboard
    agent_path = os.path.join(root_dir, "devops", "monitoring", "grafana", "dashboards", "devpilot_agent_analytics_dashboard.json")
    assert os.path.exists(agent_path)
    with open(agent_path, "r", encoding="utf-8") as f:
        agent_data = json.load(f)
    assert agent_data["uid"] == "devpilot-agent-analytics"
    assert len(agent_data["panels"]) >= 5

    # 3. Provisioning configs
    ds_path = os.path.join(root_dir, "devops", "monitoring", "grafana", "datasources", "prometheus.yml")
    assert os.path.exists(ds_path)
    dash_prov_path = os.path.join(root_dir, "devops", "monitoring", "grafana", "dashboards", "dashboards.yml")
    assert os.path.exists(dash_prov_path)


def test_monitoring_rest_api_endpoints(client):
    """Verifies all REST API endpoints under /api/monitoring."""
    # 1. GET /api/monitoring/health
    r_health = client.get("/api/monitoring/health")
    assert r_health.status_code == 200
    h_data = r_health.json()
    assert h_data["status"] in ("HEALTHY", "DEGRADED", "UNHEALTHY")
    assert "resource_usage" in h_data

    # 2. GET /api/monitoring/metrics
    r_metrics = client.get("/api/monitoring/metrics")
    assert r_metrics.status_code == 200
    assert "text/plain" in r_metrics.headers["content-type"]
    assert "devpilot_http_requests_total" in r_metrics.text

    # 3. GET /api/monitoring/traces
    r_traces = client.get("/api/monitoring/traces")
    assert r_traces.status_code == 200
    assert isinstance(r_traces.json(), list)

    # 4. GET /api/monitoring/traces/export
    r_export = client.get("/api/monitoring/traces/export")
    assert r_export.status_code == 200
    assert "resourceSpans" in r_export.json()

    # 5. POST & GET /api/monitoring/audit-logs
    audit_payload = {
        "action": "CONFIG_MUTATION",
        "resource_type": "kubernetes_deployment",
        "resource_id": "dep-api-15",
        "details": {"replicas": 4}
    }
    r_post_audit = client.post("/api/monitoring/audit-logs", json=audit_payload)
    assert r_post_audit.status_code == 201
    audit_id = r_post_audit.json()["id"]

    r_get_audit = client.get("/api/monitoring/audit-logs?limit=10")
    assert r_get_audit.status_code == 200
    assert any(a["id"] == audit_id for a in r_get_audit.json())

    # 6. GET /api/monitoring/dashboards
    r_dash = client.get("/api/monitoring/dashboards")
    assert r_dash.status_code == 200
    d_data = r_dash.json()
    assert d_data["total_dashboards"] >= 2
