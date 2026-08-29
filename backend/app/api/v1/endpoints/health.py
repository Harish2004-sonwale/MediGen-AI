"""Health, Readiness, and Operational Diagnostics API Endpoints.

Phase 9.0.4: Production Observability, Reliability & Operational Monitoring.

Endpoints:
- GET /api/v1/health/live   : Lightweight liveness probe
- GET /api/v1/health/ready  : Deep readiness probe verifying database, vector store, and task worker
- GET /api/v1/health/metrics: In-memory operational metrics snapshot (request latency, error rates, queue depth)
"""

import os
from typing import Any
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.ai.task_worker import get_background_task_provider
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
    """Deep readiness probe verifying critical dependencies: database, vector store, and worker pool."""
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

    # 2. Probe Vector Store path accessibility
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

    # 3. Probe Background Task Worker
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

    # 4. Probe Drug Knowledge Configuration
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
