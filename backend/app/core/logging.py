"""
Structured Logging Configuration for DevPilot AI
Provides JSON-structured log formatting, ContextVar-based trace/span correlation,
and task-scoped execution logging for observability.
"""
from contextvars import ContextVar
import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ContextVars for active request and task correlation
_log_trace_id: ContextVar[Optional[str]] = ContextVar("log_trace_id", default=None)
_log_span_id: ContextVar[Optional[str]] = ContextVar("log_span_id", default=None)
_log_task_id: ContextVar[Optional[str]] = ContextVar("log_task_id", default=None)
_log_request_id: ContextVar[Optional[str]] = ContextVar("log_request_id", default=None)


def set_log_context(
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    task_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> None:
    """Sets contextual identifiers for all log statements in the current async execution context."""
    if trace_id is not None:
        _log_trace_id.set(trace_id)
    if span_id is not None:
        _log_span_id.set(span_id)
    if task_id is not None:
        _log_task_id.set(task_id)
    if request_id is not None:
        _log_request_id.set(request_id)


def get_log_context() -> Dict[str, Optional[str]]:
    """Returns active correlation context."""
    return {
        "trace_id": _log_trace_id.get(),
        "span_id": _log_span_id.get(),
        "task_id": _log_task_id.get(),
        "request_id": _log_request_id.get()
    }


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON with correlation IDs and stack traces."""

    def format(self, record: logging.LogRecord) -> str:
        ctx = get_log_context()
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", ctx["trace_id"]),
            "span_id": getattr(record, "span_id", ctx["span_id"]),
            "task_id": getattr(record, "task_id", ctx["task_id"]),
            "request_id": getattr(record, "request_id", ctx["request_id"])
        }

        # Include other custom record attributes if explicitly passed
        for attr in ("execution_id", "agent_name", "user_id", "status_code", "duration_ms"):
            val = getattr(record, attr, None)
            if val is not None:
                log_obj[attr] = val

        # Clean null values
        log_obj = {k: v for k, v in log_obj.items() if v is not None}

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logging(log_level: str = "INFO", json_format: bool = False) -> None:
    """Configures application-wide logging with optional JSON formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)

    root_logger.addHandler(handler)
