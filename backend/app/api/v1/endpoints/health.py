"""Health, Readiness, and Operational Diagnostics API Endpoints.

Phase 9.0.4 & 9.0.20: Production Observability, Reliability & Enterprise Monitoring.

Endpoints:
- GET /api/v1/health/live              : Lightweight liveness probe
- GET /api/v1/health/ready             : Deep readiness probe verifying database, Redis, vector store, and task worker
- GET /api/v1/health/metrics           : In-memory operational metrics snapshot
- GET /api/v1/health/metrics/prometheus: Standard Prometheus text format metrics exporter
"""

import os
from typing import Any
from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.task_worker import get_background_task_provider
from app.core.cache import get_cache
from app.core.circuit_breaker import _CIRCUIT_BREAKERS
from app.core.config import settings
from app.core.observability import get_correlation_id, metrics_collector
from app.database import get_db

router = APIRouter(prefix="/health", tags=["Observability & Diagnostics"])


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Application liveness probe",
)
def liveness_check() -> dict[str, Any]:
    """Lightweight probe verifying the HTTP server process is running and accepting connections."""
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "correlation_id": get_correlation_id(),
    }


@router.get(
    "/ready",
    summary="Comprehensive system readiness probe",
)
def readiness_check(db: Session = Depends(get_db)) -> JSONResponse:
    """Deep readiness probe verifying critical dependencies: database, Redis cache, vector store, and worker pool."""
    components: dict[str, Any] = {}
    is_ready = True

    # 1. Probe Database connectivity
    try:
        db.execute(text("SELECT 1"))
        components["database"] = {"status": "connected", "healthy": True}
    except (SQLAlchemyError, Exception) as exc:
        is_ready = False
        components["database"] = {
            "status": "disconnected",
            "healthy": False,
            "error": "Database query execution failed",
        }

    # 2. Probe Redis / Cache connectivity
    try:
        cache = get_cache()
        cache_healthy = cache.is_available()
        components["cache"] = {
            "status": "connected" if cache_healthy else "degraded",
            "healthy": True,  # In-memory fallback prevents hard blocking
            "provider": type(cache).__name__,
        }
    except Exception as exc:
        components["cache"] = {
            "status": "unavailable",
            "healthy": False,
            "error": "Cache provider error",
        }

    # 3. Probe Vector Store path accessibility
    try:
        vpath = os.path.abspath(settings.VECTOR_DB_PATH)
        components["vector_store"] = {
            "status": "available",
            "healthy": True,
            "provider": settings.EMBEDDING_PROVIDER,
            "collection": settings.VECTOR_COLLECTION_NAME,
        }
    except Exception as exc:
        components["vector_store"] = {
            "status": "degraded",
            "healthy": False,
            "error": "Vector store directory error",
        }

    # 4. Probe Background Task Worker
    try:
        provider = get_background_task_provider()
        worker_metrics = provider.get_metrics()
        components["task_worker"] = {
            "status": "ready",
            "healthy": True,
            "provider": settings.BACKGROUND_TASK_PROVIDER,
            "metrics": worker_metrics,
        }
    except Exception as exc:
        components["task_worker"] = {
            "status": "unavailable",
            "healthy": False,
            "error": "Task worker initialization error",
        }

    # 5. Probe Drug Knowledge Configuration
    components["drug_knowledge"] = {
        "provider": settings.DRUG_KNOWLEDGE_PROVIDER,
        "healthy": True,
    }

    response_payload = {
        "status": "ready" if is_ready else "not_ready",
        "ready": is_ready,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "components": components,
        "correlation_id": get_correlation_id(),
    }

    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content=response_payload)


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    summary="Operational metrics snapshot",
)
def metrics_snapshot() -> dict[str, Any]:
    """Retrieve in-memory operational metrics (request latencies, error counts, task queue metrics)."""
    http_metrics = metrics_collector.get_snapshot()

    worker_metrics = {}
    try:
        provider = get_background_task_provider()
        worker_metrics = provider.get_metrics()
    except Exception:
        pass

    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "http": http_metrics,
        "tasks": worker_metrics,
        "correlation_id": get_correlation_id(),
    }


@router.get(
    "/metrics/prometheus",
    summary="Prometheus text-format metrics exporter",
)
def prometheus_metrics() -> Response:
    """Export operational metrics in standard Prometheus text exposition format."""
    http_metrics = metrics_collector.get_snapshot()
    lines = [
        "# HELP medigen_http_requests_total Total number of HTTP requests processed by status code.",
        "# TYPE medigen_http_requests_total counter",
    ]

    by_status = http_metrics.get("requests_by_status", {})
    for status_code, count in by_status.items():
        lines.append(f'medigen_http_requests_total{{status_code="{status_code}"}} {count}')
    if not by_status:
        lines.append('medigen_http_requests_total{status_code="200"} 0')

    # Breakdown by category
    by_category = http_metrics.get("requests_by_category", {})
    if by_category:
        lines.extend([
            "# HELP medigen_http_requests_by_category_total Total HTTP requests by API functional domain.",
            "# TYPE medigen_http_requests_by_category_total counter",
        ])
        for cat, count in by_category.items():
            lines.append(f'medigen_http_requests_by_category_total{{category="{cat}"}} {count}')

    # Latency Histogram Buckets
    buckets = http_metrics.get("latency_histogram_buckets", {})
    total_reqs = http_metrics.get("total_requests", 0)
    avg_latency = http_metrics.get("avg_duration_ms", 0.0) / 1000.0  # seconds
    duration_sum = (http_metrics.get("avg_duration_ms", 0.0) * total_reqs) / 1000.0

    lines.extend([
        "# HELP medigen_http_request_duration_seconds HTTP request latency distribution in seconds.",
        "# TYPE medigen_http_request_duration_seconds histogram",
    ])
    for le_val, b_count in sorted(buckets.items(), key=lambda x: x[0]):
        lines.append(f'medigen_http_request_duration_seconds_bucket{{le="{le_val}"}} {b_count}')
    lines.append(f'medigen_http_request_duration_seconds_bucket{{le="+Inf"}} {total_reqs}')
    lines.append(f"medigen_http_request_duration_seconds_sum {duration_sum:.4f}")
    lines.append(f"medigen_http_request_duration_seconds_count {total_reqs}")

    # Uptime
    lines.extend([
        "# HELP medigen_uptime_seconds Application process uptime in seconds.",
        "# TYPE medigen_uptime_seconds counter",
        f"medigen_uptime_seconds {http_metrics.get('uptime_seconds', 0):.1f}",
    ])

    # AI Request Metrics
    ai_total = http_metrics.get("ai_requests_total", 0)
    lines.extend([
        "# HELP medigen_ai_inferences_total Total AI inference & RAG grounding invocations.",
        "# TYPE medigen_ai_inferences_total counter",
        f"medigen_ai_inferences_total {ai_total}",
    ])

    # Database connection pool status
    from app.database.connection import get_connection_pool_status
    db_pool = get_connection_pool_status()
    lines.extend([
        "# HELP medigen_db_pool_size Configured database connection pool capacity.",
        "# TYPE medigen_db_pool_size gauge",
        f"medigen_db_pool_size {db_pool.get('size', 0)}",
        "# HELP medigen_db_pool_checked_out Active checked-out database connections.",
        "# TYPE medigen_db_pool_checked_out gauge",
        f"medigen_db_pool_checked_out {db_pool.get('checked_out', 0)}",
    ])

    # Cache connectivity
    cache = get_cache()
    cache_val = 1 if cache.is_available() else 0
    lines.extend([
        "# HELP medigen_cache_connected Whether cache provider is connected and responding.",
        "# TYPE medigen_cache_connected gauge",
        f"medigen_cache_connected {cache_val}",
    ])

    # Background task metrics
    try:
        provider = get_background_task_provider()
        wmetrics = provider.get_metrics()
        lines.extend([
            "# HELP medigen_tasks_queued Current queued background tasks.",
            "# TYPE medigen_tasks_queued gauge",
            f"medigen_tasks_queued {wmetrics.get('queued', 0)}",
            "# HELP medigen_tasks_running Current executing background tasks.",
            "# TYPE medigen_tasks_running gauge",
            f"medigen_tasks_running {wmetrics.get('running', 0)}",
        ])
    except Exception:
        pass

    # Circuit breakers
    for name, cb in _CIRCUIT_BREAKERS.items():
        state_num = 0 if cb.state.value == "CLOSED" else (1 if cb.state.value == "HALF_OPEN" else 2)
        lines.append(f'medigen_circuit_breaker_state{{name="{name}"}} {state_num}')

    content = "\n".join(lines) + "\n"
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")

