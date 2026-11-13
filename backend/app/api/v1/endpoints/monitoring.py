"""
DevPilot AI - Health Check, Prometheus Monitoring, Tracing & Audit Endpoints.
"""
from typing import Dict, Any, List, Optional
import os
import json
from fastapi import APIRouter, Depends, Query, Response, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.monitoring import (
    HealthResponse,
    AuditLogResponse,
    AuditLogCreate,
    TraceSpanResponse,
    DashboardListResponse,
    DashboardInfo
)
from app.services.health_service import health_service
from app.services.audit_service import audit_service
from app.core.tracer import global_tracer
from devops.monitoring.metrics_collector import metrics_collector

router = APIRouter(prefix="/monitoring", tags=["Monitoring, Observability & Auditing"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """System health check endpoint verifying database connectivity, subsystem statuses, and hardware utilization."""
    return health_service.get_system_health(db=db)


@router.get("/metrics")
def get_prometheus_metrics():
    """Exposes Prometheus scrape endpoint conforming to Prometheus Exposition Text Format 0.0.4."""
    exposition = metrics_collector.generate_exposition()
    return Response(content=exposition, media_type="text/plain; version=0.0.4; charset=utf-8")


@router.get("/traces", response_model=List[TraceSpanResponse])
def get_recent_execution_traces(
    limit: int = Query(50, ge=1, le=200),
    trace_id: Optional[str] = Query(None)
):
    """Retrieves recent OpenTelemetry-compatible execution spans and multi-agent pipeline traces."""
    return global_tracer.get_recent_spans(limit=limit, trace_id=trace_id)


@router.get("/traces/export")
def export_opentelemetry_traces(limit: int = Query(50, ge=1, le=200)):
    """Exports execution traces conforming to OpenTelemetry Collector JSON Schema."""
    return global_tracer.export_opentelemetry(limit=limit)


@router.get("/audit-logs", response_model=List[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Retrieves immutable security and compliance audit logs."""
    return audit_service.list_logs(db=db, limit=limit, offset=offset, action=action, resource_type=resource_type)


@router.post("/audit-logs", response_model=AuditLogResponse, status_code=status.HTTP_201_CREATED)
def create_audit_log_entry(
    payload: AuditLogCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Records a new compliance audit log event."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    return audit_service.record_event(
        db=db,
        action=payload.action,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        details=payload.details,
        ip_address=client_ip
    )


@router.get("/dashboards", response_model=DashboardListResponse)
def get_grafana_dashboards():
    """Lists provisioned Grafana dashboard definitions and panel metrics."""
    dashboards = [
        DashboardInfo(
            id="devpilot-platform-overview",
            title="DevPilot AI - Platform Overview & Health",
            description="Core system telemetry: HTTP request rate, P50/P99 latency, active agent tasks, failure rate, and host resource utilization.",
            tags=["devpilot", "overview", "prometheus", "system"],
            panel_count=8,
            path="devops/monitoring/grafana/dashboards/devpilot_overview_dashboard.json"
        ),
        DashboardInfo(
            id="devpilot-agent-analytics",
            title="DevPilot AI - Multi-Agent & LLM Analytics",
            description="Autonomous multi-agent execution durations, self-healing test repair iterations, CodeBERT defect throughput, and CI/CD pipeline outcomes.",
            tags=["devpilot", "agents", "langgraph", "ml"],
            panel_count=6,
            path="devops/monitoring/grafana/dashboards/devpilot_agent_analytics_dashboard.json"
        )
    ]
    return DashboardListResponse(total_dashboards=len(dashboards), dashboards=dashboards)
