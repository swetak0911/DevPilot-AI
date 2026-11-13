"""
DevPilot AI - Autonomous Software Engineering & DevOps Intelligence Platform
FastAPI Application Entry Point
"""
import os
import sys

# Ensure backend root directory is on sys.path when launched from root
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging, set_log_context
from app.core.database import init_db
from app.api.v1.router import api_router
from devops.monitoring.metrics_collector import metrics_collector

# Setup application logging
setup_logging(log_level=settings.LOG_LEVEL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager for startup and shutdown routines."""
    # Startup routines
    init_db()
    yield
    # Shutdown routines


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Autonomous Software Engineering & DevOps Intelligence Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS if isinstance(settings.ALLOWED_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_timing_and_id_middleware(request: Request, call_next):
    """Attaches correlation ID, trace context, and measures request execution latency for Prometheus."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    trace_id = request.headers.get("X-Trace-ID") or uuid.uuid4().hex
    set_log_context(trace_id=trace_id, request_id=request_id)

    start_time = time.perf_counter()
    response = await call_next(request)
    duration_sec = time.perf_counter() - start_time
    duration_ms = duration_sec * 1000

    # Record Prometheus metrics
    endpoint_path = request.url.path
    metrics_collector.record_http_request(
        method=request.method,
        endpoint=endpoint_path,
        status_code=response.status_code,
        duration_sec=duration_sec
    )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Trace-ID"] = trace_id
    response.headers["X-Response-Time-MS"] = f"{duration_ms:.2f}"
    return response


# Mount consolidated v1 API router (supports both /api and /api/v1 prefixes)
app.include_router(api_router, prefix=settings.API_V1_STR)
if settings.API_V1_STR != "/api/v1":
    app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
def root_endpoint():
    """Root info endpoint providing basic platform metadata."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "OPERATIONAL",
        "documentation": "/docs",
        "api_v1": settings.API_V1_STR,
        "health": f"{settings.API_V1_STR}/monitoring/health"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Centralized fallback exception handler preventing secret leakage."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please consult system logs."},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
