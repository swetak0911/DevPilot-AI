"""
========================================================================
 DevPilot AI - Phase 15 Monitoring & Observability Verification Suite
========================================================================
Statically and dynamically verifies Prometheus metrics collection,
text exposition formatting (v0.0.4), OpenTelemetry distributed tracing,
structured JSON logging with context correlation, system health & hardware
diagnostics, security audit logging, Grafana dashboards, and REST APIs.
========================================================================
"""
import sys
import os
import json
import logging
import traceback
from typing import Dict, Any, List

# Add workspace and backend to sys.path
root_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(root_path, "backend")
if root_path not in sys.path:
    sys.path.insert(0, root_path)
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from fastapi.testclient import TestClient
from app.main import app
from app.core.database import init_db, SessionLocal
from app.core.tracer import global_tracer, Span
from app.core.logging import JSONFormatter, set_log_context, get_log_context
from devops.monitoring.metrics_collector import metrics_collector
from app.services.health_service import health_service
from app.services.audit_service import audit_service


def run_phase15_verification() -> bool:
    print("=" * 72)
    print(" DevPilot AI - Phase 15 Monitoring & Observability Suite")
    print("=" * 72)

    init_db()
    db = SessionLocal()
    client = TestClient(app)

    # -------------------------------------------------------------------------
    # 1. Prometheus Metrics Collector & Exposition Engine
    # -------------------------------------------------------------------------
    print("\n[CHECK 1] Prometheus Metrics Collector & Exposition Engine...")
    try:
        metrics_collector.inc_counter("devpilot_test_requests_total", 3.0, {"method": "GET", "status": "200"})
        metrics_collector.set_gauge("devpilot_test_pool_size", 16.0, {"pool": "worker"})
        metrics_collector.observe_histogram("devpilot_test_execution_latency", 0.085, {"agent": "CodingAgent"})

        # Record domain telemetry
        metrics_collector.record_http_request("POST", "/api/tasks", 201, 0.042)
        metrics_collector.record_task_status("CODE_GENERATION", "SUCCESS")
        metrics_collector.record_agent_execution("PlanningAgent", 1.25)
        metrics_collector.record_deployment_risk("repo-verification-p15", 0.08)
        metrics_collector.record_codebert_inference("python", False)

        exposition = metrics_collector.generate_exposition()
        assert "# HELP devpilot_http_requests_total" in exposition, "Missing HTTP requests HELP"
        assert "# TYPE devpilot_http_requests_total counter" in exposition, "Missing HTTP requests TYPE"
        assert "devpilot_http_requests_total" in exposition, "Missing HTTP requests metric series"
        assert "devpilot_deployment_risk_score" in exposition, "Missing deployment risk gauge"
        assert "devpilot_request_duration_seconds_bucket" in exposition, "Missing request duration histogram"
        assert exposition.endswith("\n"), "Exposition must end with trailing newline"

        print(f" [PASS] 1. Prometheus Metrics Collector: OK (Generated standard v0.0.4 exposition with {len(exposition.splitlines())} metric lines)")
    except Exception as exc:
        print(f" [FAIL] 1. Metrics Collector: {exc}\n{traceback.format_exc()}")
        db.close()
        return False

    # -------------------------------------------------------------------------
    # 2. OpenTelemetry-Compatible Distributed Tracer
    # -------------------------------------------------------------------------
    print("\n[CHECK 2] OpenTelemetry-Compatible Distributed Tracer...")
    try:
        global_tracer.clear()

        # Multi-agent execution pipeline span hierarchy
        with global_tracer.start_span("orchestrator.pipeline", {"task.id": "task-phase15-trace"}) as root:
            root.add_event("pipeline_started", {"timestamp_epoch": 123456})

            with global_tracer.start_span("agent.planning", {"agent": "PlanningAgent"}) as planning_span:
                planning_span.set_attribute("plan.tasks_count", 4)
                assert planning_span.parent_span_id == root.span_id, "Child span must reference parent span ID"
                assert planning_span.trace_id == root.trace_id, "Child span must inherit root trace ID"

            with global_tracer.start_span("agent.coding", {"agent": "CodingAgent"}) as coding_span:
                coding_span.set_attribute("diff.files_count", 2)
                assert coding_span.parent_span_id == root.span_id

        recent_spans = global_tracer.get_recent_spans(limit=10)
        assert len(recent_spans) >= 3, f"Expected at least 3 spans, got {len(recent_spans)}"

        root_dict = next(s for s in recent_spans if s["name"] == "orchestrator.pipeline")
        child_dict = next(s for s in recent_spans if s["name"] == "agent.planning")
        assert root_dict["status"] == "OK"
        assert root_dict["duration_ms"] is not None and root_dict["duration_ms"] >= 0.0
        assert child_dict["parent_span_id"] == root_dict["span_id"]

        # OTLP Export
        otlp_export = global_tracer.export_opentelemetry(limit=5)
        assert "resourceSpans" in otlp_export
        spans_list = otlp_export["resourceSpans"][0]["scopeSpans"][0]["spans"]
        assert len(spans_list) >= 3

        print(f" [PASS] 2. OpenTelemetry Distributed Tracer: OK (Hierarchical trace {root.trace_id[:8]}... with {len(recent_spans)} validated spans)")
    except Exception as exc:
        print(f" [FAIL] 2. Distributed Tracer: {exc}\n{traceback.format_exc()}")
        db.close()
        return False

    # -------------------------------------------------------------------------
    # 3. Structured JSON Logging with Context Correlation
    # -------------------------------------------------------------------------
    print("\n[CHECK 3] Structured JSON Logging with Correlation Context...")
    try:
        set_log_context(trace_id="tr-verify-p15", span_id="sp-root-001", task_id="task-p15-verify")
        active_ctx = get_log_context()
        assert active_ctx["trace_id"] == "tr-verify-p15"
        assert active_ctx["span_id"] == "sp-root-001"
        assert active_ctx["task_id"] == "task-p15-verify"

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="app.services.observability",
            level=logging.INFO,
            pathname="verify_phase15.py",
            lineno=105,
            msg="Agent execution step completed successfully",
            args=(),
            exc_info=None
        )

        formatted_json_str = formatter.format(record)
        parsed = json.loads(formatted_json_str)
        assert parsed["message"] == "Agent execution step completed successfully"
        assert parsed["level"] == "INFO"
        assert parsed["trace_id"] == "tr-verify-p15"
        assert parsed["span_id"] == "sp-root-001"
        assert parsed["task_id"] == "task-p15-verify"
        assert "timestamp" in parsed

        print(f" [PASS] 3. Structured JSON Logging: OK (Correlated trace_id={parsed['trace_id']}, span_id={parsed['span_id']}, task_id={parsed['task_id']})")
    except Exception as exc:
        print(f" [FAIL] 3. Structured Logging: {exc}\n{traceback.format_exc()}")
        db.close()
        return False

    # -------------------------------------------------------------------------
    # 4. System Health & Hardware Diagnostics
    # -------------------------------------------------------------------------
    print("\n[CHECK 4] System Health & Hardware Diagnostics Probes...")
    try:
        health = health_service.get_system_health(db=db)
        assert health["status"] in ("HEALTHY", "DEGRADED", "UNHEALTHY"), f"Unexpected health status {health['status']}"
        assert health["database_latency_ms"] >= 0.0, "Database ping latency must be non-negative"
        assert health["uptime_seconds"] >= 0.0, "Uptime must be non-negative"
        assert "services" in health and len(health["services"]) >= 6, "Missing subsystem statuses"
        assert health["services"]["database"] == "CONNECTED"
        assert health["services"]["api_server"] == "ONLINE"
        assert health["services"]["codebert_inference"] == "INITIALIZED"
        assert "resource_usage" in health
        assert health["resource_usage"]["memory_mb"] > 0.0

        print(
            f" [PASS] 4. System Health Diagnostics: OK "
            f"(Status: {health['status']}, DB Latency: {health['database_latency_ms']}ms, "
            f"RAM: {health['resource_usage']['memory_mb']}MB, Subsystems: {len(health['services'])} online)"
        )
    except Exception as exc:
        print(f" [FAIL] 4. Health Diagnostics: {exc}\n{traceback.format_exc()}")
        db.close()
        return False

    # -------------------------------------------------------------------------
    # 5. Security & Compliance Audit Log Engine
    # -------------------------------------------------------------------------
    print("\n[CHECK 5] Security & Compliance Audit Log Engine...")
    try:
        entry = audit_service.record_event(
            db=db,
            action="TERRAFORM_PLAN_APPROVED",
            resource_type="infrastructure_iac",
            resource_id="plan-p15-test",
            details={"approved_by": "secops_admin", "risk": "MEDIUM"},
            ip_address="10.0.0.42"
        )
        assert entry.id is not None
        assert entry.action == "TERRAFORM_PLAN_APPROVED"

        queried = audit_service.list_logs(db=db, action="TERRAFORM_PLAN_APPROVED")
        assert len(queried) >= 1
        record = next(q for q in queried if q.resource_id == "plan-p15-test")
        assert record.ip_address == "10.0.0.42"
        assert record.details["approved_by"] == "secops_admin"

        summary = audit_service.get_audit_summary(db=db)
        assert summary["total_audit_events"] >= 1

        print(f" [PASS] 5. Compliance Audit Log Engine: OK (Persisted & retrieved event '{entry.action}' on '{entry.resource_type}')")
    except Exception as exc:
        print(f" [FAIL] 5. Audit Logging: {exc}\n{traceback.format_exc()}")
        db.close()
        return False

    # -------------------------------------------------------------------------
    # 6. Grafana Dashboard Definitions & Provisioning Assets
    # -------------------------------------------------------------------------
    print("\n[CHECK 6] Grafana Dashboard Definitions & Provisioning Assets...")
    try:
        # Overview Dashboard
        overview_path = os.path.join(root_path, "devops", "monitoring", "grafana", "dashboards", "devpilot_overview_dashboard.json")
        assert os.path.exists(overview_path), "Missing devpilot_overview_dashboard.json"
        with open(overview_path, "r", encoding="utf-8") as f:
            overview_dash = json.load(f)
        assert overview_dash["uid"] == "devpilot-platform-overview"
        assert len(overview_dash["panels"]) >= 8

        # Agent Analytics Dashboard
        agent_path = os.path.join(root_path, "devops", "monitoring", "grafana", "dashboards", "devpilot_agent_analytics_dashboard.json")
        assert os.path.exists(agent_path), "Missing devpilot_agent_analytics_dashboard.json"
        with open(agent_path, "r", encoding="utf-8") as f:
            agent_dash = json.load(f)
        assert agent_dash["uid"] == "devpilot-agent-analytics"
        assert len(agent_dash["panels"]) >= 5

        # Provisioning YAMLs
        ds_yaml = os.path.join(root_path, "devops", "monitoring", "grafana", "datasources", "prometheus.yml")
        assert os.path.exists(ds_yaml), "Missing prometheus.yml datasource config"
        dash_yaml = os.path.join(root_path, "devops", "monitoring", "grafana", "dashboards", "dashboards.yml")
        assert os.path.exists(dash_yaml), "Missing dashboards.yml provider config"

        print(
            f" [PASS] 6. Grafana Dashboard Assets: OK "
            f"(Validated 'devpilot-platform-overview' [{len(overview_dash['panels'])} panels], "
            f"'devpilot-agent-analytics' [{len(agent_dash['panels'])} panels], and auto-provisioning configs)"
        )
    except Exception as exc:
        print(f" [FAIL] 6. Grafana Dashboards: {exc}\n{traceback.format_exc()}")
        db.close()
        return False

    # -------------------------------------------------------------------------
    # 7. End-to-End REST APIs
    # -------------------------------------------------------------------------
    print("\n[CHECK 7] End-to-End Monitoring & Observability REST APIs...")
    try:
        def fetch_api(path: str, method: str = "GET", json_body: Any = None):
            # Try /api first then /api/v1
            r = client.request(method, f"/api{path}", json=json_body)
            if r.status_code == 404:
                r = client.request(method, f"/api/v1{path}", json=json_body)
            return r

        # 1. GET /monitoring/health
        r_health = fetch_api("/monitoring/health")
        assert r_health.status_code == 200, f"Health returned {r_health.status_code}"
        assert r_health.json()["status"] in ("HEALTHY", "DEGRADED", "UNHEALTHY")

        # 2. GET /monitoring/metrics
        r_met = fetch_api("/monitoring/metrics")
        assert r_met.status_code == 200, f"Metrics returned {r_met.status_code}"
        assert "text/plain" in r_met.headers["content-type"]
        assert "devpilot_http_requests_total" in r_met.text

        # 3. GET /monitoring/traces
        r_trc = fetch_api("/monitoring/traces")
        assert r_trc.status_code == 200, f"Traces returned {r_trc.status_code}"
        assert isinstance(r_trc.json(), list)

        # 4. GET /monitoring/traces/export
        r_exp = fetch_api("/monitoring/traces/export")
        assert r_exp.status_code == 200, f"Traces export returned {r_exp.status_code}"
        assert "resourceSpans" in r_exp.json()

        # 5. POST /monitoring/audit-logs
        audit_payload = {
            "action": "DOCKERFILE_HARDENING",
            "resource_type": "container_manifest",
            "resource_id": "Dockerfile-p15",
            "details": {"linter_score": 100}
        }
        r_post_audit = fetch_api("/monitoring/audit-logs", method="POST", json_body=audit_payload)
        assert r_post_audit.status_code == 201, f"POST audit-logs returned {r_post_audit.status_code}"
        audit_entry_id = r_post_audit.json()["id"]

        # 6. GET /monitoring/audit-logs
        r_get_audit = fetch_api("/monitoring/audit-logs?limit=10")
        assert r_get_audit.status_code == 200, f"GET audit-logs returned {r_get_audit.status_code}"
        assert any(a["id"] == audit_entry_id for a in r_get_audit.json())

        # 7. GET /monitoring/dashboards
        r_dash = fetch_api("/monitoring/dashboards")
        assert r_dash.status_code == 200, f"Dashboards returned {r_dash.status_code}"
        assert r_dash.json()["total_dashboards"] >= 2

        print(f" [PASS] 7. End-to-End REST APIs: OK (/health, /metrics, /traces, /traces/export, /audit-logs [POST/GET], /dashboards all verified)")
    except Exception as exc:
        print(f" [FAIL] 7. REST APIs: {exc}\n{traceback.format_exc()}")
        db.close()
        return False

    db.close()
    print("\n" + "=" * 72)
    print(" [SUCCESS] Phase 15 Monitoring & Observability Suite Verified 100%!")
    print("=" * 72)
    return True


if __name__ == "__main__":
    success = run_phase15_verification()
    sys.exit(0 if success else 1)
