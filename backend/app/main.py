from contextlib import asynccontextmanager
import logging
from fastapi import Depends, FastAPI, Request, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import uvicorn

from app.api.v1.api import api_router
from app.ai.task_worker import get_background_task_provider
from app.core.config import settings
from app.core.observability import (
    CorrelationIdMiddleware,
    configure_logging,
    get_correlation_id,
)
from app.database import get_db

# Configure structured logging with PHI sanitization
configure_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
logger = logging.getLogger("medigen.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Production ASGI Lifespan manager: Handles graceful startup diagnostics and worker drain upon shutdown."""
    # 1. Startup phase
    logger.info(
        "Starting %s v%s in [%s] environment (debug=%s, workers=%s)",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
        settings.DEBUG,
        settings.ASGI_WORKERS,
    )

    if settings.is_production():
        prod_errors = settings.validate_production_settings()
        if prod_errors:
            for err in prod_errors:
                logger.error("Production configuration issue detected: %s", err)
            raise RuntimeError(
                f"Critical production configuration errors detected ({len(prod_errors)} issues). "
                "Halting application startup for patient safety and compliance security."
            )

    # Initialize cache and rate limiter
    from app.core.cache import get_cache
    from app.core.rate_limiter import get_rate_limiter

    get_cache()
    get_rate_limiter()

    # Initialize background worker provider
    worker_provider = get_background_task_provider()
    logger.info(
        "Background task provider initialised: provider=%s",
        type(worker_provider).__name__,
    )

    yield

    # 2. Shutdown phase: Gracefully drain background tasks
    logger.info("Application shutdown initiated. Draining background task worker pool...")
    try:
        if hasattr(worker_provider, "shutdown"):
            worker_provider.shutdown(wait=True)
        from app.ai.task_worker import reset_background_task_provider
        reset_background_task_provider()
        logger.info("Background task worker pool shutdown successfully.")
    except Exception as exc:
        logger.warning("Error during background task worker shutdown: %s", exc)
    logger.info("MediGen AI application shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MediGen AI - Clinical Decision Support System API",
    lifespan=lifespan,
)

# 1. Correlation ID, Tracing and Request Timing Middleware
app.add_middleware(CorrelationIdMiddleware)

# 2. Production Security Headers Middleware
from app.core.security_headers import SecurityHeadersMiddleware
app.add_middleware(SecurityHeadersMiddleware)

# 3. Rate Limiting & Abuse Protection Middleware
from app.core.rate_limiter import RateLimiterMiddleware
app.add_middleware(RateLimiterMiddleware)

# 4. CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all global exception handler ensuring safe diagnostics and correlation ID linkage."""
    corr_id = get_correlation_id()
    logger.error(
        "Unhandled server exception on %s %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected internal server error occurred. Please reference the correlation ID for support.",
            "correlation_id": corr_id,
        },
    )


# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

# ------------------------------------------------------------------------------
# Phase 9.0.21: SMART on FHIR 2.0 & CDS Hooks Root Endpoints & WebSockets
# ------------------------------------------------------------------------------
from app.services.smart_service import smart_service
from app.api.v1.endpoints.cds import router as cds_router
from app.api.v1.endpoints.websockets import (
    handle_collaboration_ws,
    handle_telehealth_ws,
    handle_telemetry_ws,
)

# Root SMART on FHIR 2.0 Discovery
@app.get("/.well-known/smart-configuration", tags=["SMART on FHIR 2.0"])
def root_smart_configuration(request: Request):
    """Standard root SMART on FHIR 2.0 discovery document."""
    base_url = str(request.base_url).rstrip("/")
    return smart_service.get_smart_configuration(base_url)

@app.get("/.well-known/jwks.json", tags=["SMART on FHIR 2.0"])
def root_jwks_json():
    """Standard root JSON Web Key Set for token validation."""
    return smart_service.get_jwks()

# Mount CDS Services at root /cds-services per CDS Hooks 2.0 spec
app.include_router(cds_router, prefix="/cds-services", tags=["CDS Hooks 2.0"])

# Real-Time Bi-Directional WebSockets
@app.websocket("/ws/telemetry/{patient_id}")
async def ws_telemetry_endpoint(websocket: WebSocket, patient_id: str, token: str = None):
    await handle_telemetry_ws(websocket, patient_id, token)

@app.websocket("/ws/collaboration/{patient_id}")
async def ws_collaboration_endpoint(websocket: WebSocket, patient_id: str, token: str = None):
    await handle_collaboration_ws(websocket, patient_id, token)

@app.websocket("/ws/telehealth/{session_id}")
async def ws_telehealth_endpoint(websocket: WebSocket, session_id: str, token: str = None):
    await handle_telehealth_ws(websocket, session_id, token)


@app.get("/")
def read_root():
    return {
        "message": "Welcome to MediGen AI API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }


@app.get("/ready")
def readiness_check_root(db: Session = Depends(get_db)):
    """Top-level readiness check verifying application database and core dependencies."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
            "correlation_id": get_correlation_id(),
        }
    except (SQLAlchemyError, Exception):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "database": "disconnected",
                "detail": "Database is unreachable or query execution failed",
                "correlation_id": get_correlation_id(),
            },
        )


@app.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    """Check live connectivity to the PostgreSQL database by executing SELECT 1."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
        }
    except (SQLAlchemyError, Exception):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "detail": "Database is unreachable or query execution failed",
            },
        )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
