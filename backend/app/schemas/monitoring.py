"""
Monitoring, Telemetry, and Audit Schemas for DevPilot AI.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ResourceUsage(BaseModel):
    memory_mb: float
    cpu_percent: float
    python_version: str


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: str
    uptime_seconds: float = 0.0
    database_latency_ms: float = 0.0
    resource_usage: ResourceUsage
    services: Dict[str, str]


class OverviewStatsResponse(BaseModel):
    connected_repositories: int
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    active_executions: int
    test_pass_rate: float
    ci_success_rate: float
    recent_activities: List[Dict[str, Any]]


class AuditLogCreate(BaseModel):
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class TraceSpanResponse(BaseModel):
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = None


class DashboardInfo(BaseModel):
    id: str
    title: str
    description: str
    tags: List[str]
    panel_count: int
    path: str


class DashboardListResponse(BaseModel):
    total_dashboards: int
    dashboards: List[DashboardInfo]
