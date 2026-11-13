"""
DevPilot AI - Distributed Execution Tracer (OpenTelemetry Compatible)
Provides hierarchical span context propagation, latency measurement,
metadata attribute recording, and OpenTelemetry JSON serialization
for multi-agent pipelines and HTTP request execution.
"""
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import time
import uuid
import logging

logger = logging.getLogger(__name__)

# ContextVars for active span propagation across async tasks
_current_trace_id: ContextVar[Optional[str]] = ContextVar("current_trace_id", default=None)
_current_span_id: ContextVar[Optional[str]] = ContextVar("current_span_id", default=None)


@dataclass
class SpanEvent:
    name: str
    timestamp: float
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "UNSET"  # "OK", "ERROR", "UNSET"
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    error_message: Optional[str] = None

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.events.append(SpanEvent(
            name=name,
            timestamp=time.time(),
            attributes=attributes or {}
        ))

    def set_status(self, status: str, description: Optional[str] = None) -> None:
        self.status = status
        if description:
            self.error_message = description

    def finish(self) -> None:
        if self.end_time is None:
            self.end_time = time.time()
            self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
            if self.status == "UNSET":
                self.status = "OK"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "attributes": self.attributes,
            "events": [asdict(e) for e in self.events],
            "error_message": self.error_message
        }

    def to_opentelemetry_format(self) -> Dict[str, Any]:
        """Formats span according to standard OpenTelemetry Collector JSON Schema."""
        return {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "parentSpanId": self.parent_span_id or "",
            "name": self.name,
            "kind": "SPAN_KIND_INTERNAL",
            "startTimeUnixNano": int(self.start_time * 1e9),
            "endTimeUnixNano": int((self.end_time or time.time()) * 1e9),
            "attributes": [
                {"key": k, "value": {"stringValue": str(v)}}
                for k, v in self.attributes.items()
            ],
            "status": {
                "code": 1 if self.status == "OK" else (2 if self.status == "ERROR" else 0),
                "message": self.error_message or ""
            }
        }


class SpanContextManager:
    """Context manager for tracing code blocks and multi-agent execution steps."""

    def __init__(self, tracer: 'Tracer', span: Span):
        self.tracer = tracer
        self.span = span
        self._prev_trace_token = None
        self._prev_span_token = None

    def __enter__(self) -> Span:
        self._prev_trace_token = _current_trace_id.set(self.span.trace_id)
        self._prev_span_token = _current_span_id.set(self.span.span_id)
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.span.set_status("ERROR", str(exc_val))
        self.span.finish()
        self.tracer.record_span(self.span)

        if self._prev_trace_token:
            _current_trace_id.reset(self._prev_trace_token)
        if self._prev_span_token:
            _current_span_id.reset(self._prev_span_token)


class Tracer:
    """Central OpenTelemetry-compatible tracing engine with in-memory buffer."""

    def __init__(self, service_name: str = "devpilot-backend", buffer_size: int = 1000):
        self.service_name = service_name
        self.buffer_size = buffer_size
        self._spans: List[Span] = []

    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        parent_span_id: Optional[str] = None
    ) -> SpanContextManager:
        """Starts a new span inheriting active trace context or generating a new trace."""
        trace_id = _current_trace_id.get() or uuid.uuid4().hex
        parent_id = parent_span_id or _current_span_id.get()
        span_id = uuid.uuid4().hex[:16]

        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_id,
            attributes=attributes or {}
        )
        span.set_attribute("service.name", self.service_name)
        return SpanContextManager(self, span)

    def record_span(self, span: Span) -> None:
        self._spans.append(span)
        if len(self._spans) > self.buffer_size:
            self._spans.pop(0)

    def get_recent_spans(self, limit: int = 50, trace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns recent spans filtered optionally by trace_id."""
        spans = self._spans
        if trace_id:
            spans = [s for s in spans if s.trace_id == trace_id]
        return [s.to_dict() for s in reversed(spans[-limit:])]

    def export_opentelemetry(self, limit: int = 50) -> Dict[str, Any]:
        """Exports spans in OpenTelemetry OTLP/JSON resource structure."""
        return {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": self.service_name}},
                            {"key": "telemetry.sdk.language", "value": {"stringValue": "python"}}
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "devpilot.tracer", "version": "1.0.0"},
                            "spans": [s.to_opentelemetry_format() for s in self._spans[-limit:]]
                        }
                    ]
                }
            ]
        }

    def clear(self) -> None:
        self._spans.clear()


# Global Singleton Tracer
global_tracer = Tracer()
