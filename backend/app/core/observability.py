"""Production Observability, Structured Logging, and Correlation Tracing.

Phase 9.0.4: Production Observability, Reliability & Operational Monitoring.

Provides:
- Context-bound request correlation IDs across async executions and worker tasks
- Automated PHI and credential masking logging filter (PHISanitizingFilter)
- Structured JSON and human-readable text log formatters
- Correlation ID and request duration middleware (CorrelationIdMiddleware)
- In-memory operational metrics collector for system readiness and diagnostics
"""

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import re
import secrets
import time
from typing import Any, Callable, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable holding correlation ID for the active request / task
_CORRELATION_ID_CTX: ContextVar[str] = ContextVar("correlation_id", default="")

# Safe correlation ID pattern: alphanumeric with hyphens/underscores, 4-64 chars
_CORRELATION_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]{4,64}$")

# PHI & Secret Sanitization Patterns
_BEARER_TOKEN_RE = re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*", re.IGNORECASE)
_JWT_TOKEN_RE = re.compile(r"\beyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_AWS_KEY_RE = re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")
_PASSWORD_FIELD_RE = re.compile(r"(password|secret|token|api_key)\s*[:=]\s*['\"]?[^\s,'\"]+['\"]?", re.IGNORECASE)


def generate_correlation_id() -> str:
    """Generate unique correlation identifier (e.g. req-20260829-A1B2C3D4)."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    random_part = secrets.token_hex(4).upper()
    return f"req-{date_str}-{random_part}"


def sanitize_correlation_id(raw_id: Optional[str]) -> str:
    """Validate and sanitize an incoming correlation ID; generate new if absent/invalid."""
    if raw_id:
        clean = raw_id.strip()
        if _CORRELATION_ID_REGEX.match(clean):
            return clean
    return generate_correlation_id()


def get_correlation_id() -> str:
    """Get correlation ID from active context or generate fallback."""
    corr_id = _CORRELATION_ID_CTX.get()
    return corr_id if corr_id else "system"


def set_correlation_id(corr_id: str) -> None:
    """Set correlation ID in active context."""
    _CORRELATION_ID_CTX.set(corr_id)


def sanitize_log_message(message: str) -> str:
    """Strip or mask accidental credentials, tokens, and PHI identifiers from log text."""
    if not isinstance(message, str):
        return str(message)
    sanitized = _BEARER_TOKEN_RE.sub("Bearer [REDACTED]", message)
    sanitized = _JWT_TOKEN_RE.sub("[JWT_REDACTED]", sanitized)
    sanitized = _AWS_KEY_RE.sub("[AWS_KEY_REDACTED]", sanitized)
    sanitized = _EMAIL_RE.sub("[EMAIL_REDACTED]", sanitized)
    sanitized = _PASSWORD_FIELD_RE.sub(r"\1=[REDACTED]", sanitized)
    return sanitized


class PHISanitizingFilter(logging.Filter):
    """Logging filter that automatically injects correlation ID and sanitizes messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Inject correlation_id onto log record
        if not hasattr(record, "correlation_id") or not record.correlation_id:
            record.correlation_id = get_correlation_id()

        # Sanitize log message content
        if isinstance(record.msg, str):
            record.msg = sanitize_log_message(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    sanitize_log_message(a) if isinstance(a, str) else a
                    for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: sanitize_log_message(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        return True


class StructuredJsonFormatter(logging.Formatter):
    """Outputs standardized single-line JSON log records for production log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        corr_id = getattr(record, "correlation_id", get_correlation_id())
        now = datetime.now(timezone.utc).isoformat()

        log_data: dict[str, Any] = {
            "timestamp": now,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": corr_id,
        }

        # Include exception details if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include operational metadata extras
        for key, val in record.__dict__.items():
            if key not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "levelname", "levelno", "lineno", "module", "msecs",
                "message", "msg", "name", "pathname", "process", "processName",
                "relativeCreated", "stack_info", "thread", "threadName", "correlation_id",
            ):
                log_data[key] = val

        return json.dumps(log_data)


class StructuredTextFormatter(logging.Formatter):
    """Human-readable formatted log output for local development and console output."""

    def format(self, record: logging.LogRecord) -> str:
        corr_id = getattr(record, "correlation_id", get_correlation_id())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        msg = record.getMessage()
        exc_text = f"\n{self.formatException(record.exc_info)}" if record.exc_info else ""
        return f"[{now}] [{record.levelname:<5}] [{corr_id}] [{record.name}] {msg}{exc_text}"


# ---------------------------------------------------------------------------
# Operational Metrics Collector (In-Memory, zero SaaS dependencies)
# ---------------------------------------------------------------------------


class OperationalMetricsCollector:
    """Thread-safe lightweight operational metrics collector for production readiness."""

    def __init__(self):
        self._start_time = datetime.now(timezone.utc)
        self._request_count = 0
        self._error_count_4xx = 0
        self._error_count_5xx = 0
        self._total_response_time_ms = 0.0

    def record_request(self, status_code: int, duration_ms: float) -> None:
        self._request_count += 1
        self._total_response_time_ms += duration_ms
        if 400 <= status_code < 500:
            self._error_count_4xx += 1
        elif status_code >= 500:
            self._error_count_5xx += 1

    def get_snapshot(self) -> dict[str, Any]:
        uptime_seconds = (datetime.now(timezone.utc) - self._start_time).total_seconds()
        avg_latency = (
            self._total_response_time_ms / self._request_count
            if self._request_count > 0
            else 0.0
        )

        return {
            "uptime_seconds": round(uptime_seconds, 2),
            "started_at": self._start_time.isoformat(),
            "total_requests": self._request_count,
            "client_errors_4xx": self._error_count_4xx,
            "server_errors_5xx": self._error_count_5xx,
            "avg_response_time_ms": round(avg_latency, 2),
        }


metrics_collector = OperationalMetricsCollector()


# ---------------------------------------------------------------------------
# Correlation & Request Timing Middleware
# ---------------------------------------------------------------------------


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware that manages correlation IDs, timing, and response headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate correlation ID
        raw_corr_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID")
        correlation_id = sanitize_correlation_id(raw_corr_id)

        # Bind to contextvars context
        set_correlation_id(correlation_id)

        start_time = time.perf_counter()
        logger = logging.getLogger("medigen.http")

        # Strip query parameters or sensitive URLs from operational access log
        safe_path = request.url.path

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0

            # Inject response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

            # Record metrics
            metrics_collector.record_request(
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            # Operational access log (PHI-free)
            logger.info(
                "HTTP %s %s -> %d (%.2fms)",
                request.method,
                safe_path,
                response.status_code,
                duration_ms,
            )

            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            metrics_collector.record_request(status_code=500, duration_ms=duration_ms)
            logger.error(
                "Unhandled HTTP exception during %s %s: %s (%.2fms)",
                request.method,
                safe_path,
                type(exc).__name__,
                duration_ms,
            )
            raise


# ---------------------------------------------------------------------------
# Logging Configuration Setup
# ---------------------------------------------------------------------------


def configure_logging(log_level: str = "INFO", log_format: str = "text") -> None:
    """Configure root and application loggers with sanitization filters and structured formatters."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Choose formatter
    if log_format.lower() == "json":
        formatter = StructuredJsonFormatter()
    else:
        formatter = StructuredTextFormatter()

    # Add sanitizing filter to all existing handlers
    phi_filter = PHISanitizingFilter()

    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.addFilter(phi_filter)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setFormatter(formatter)
            handler.addFilter(phi_filter)
