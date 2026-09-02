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
_TRACE_ID_CTX: ContextVar[str] = ContextVar("trace_id", default="")
_SPAN_ID_CTX: ContextVar[str] = ContextVar("span_id", default="")

# Safe correlation ID pattern: alphanumeric with hyphens/underscores, 4-64 chars
_CORRELATION_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]{4,64}$")
_TRACEPARENT_REGEX = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$", re.IGNORECASE)

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


def generate_trace_id() -> str:
    """Generate W3C 128-bit hex trace ID."""
    return secrets.token_hex(16).lower()


def generate_span_id() -> str:
    """Generate W3C 64-bit hex span ID."""
    return secrets.token_hex(8).lower()


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


def get_trace_id() -> str:
    """Get active W3C trace ID or generate on demand."""
    tid = _TRACE_ID_CTX.get()
    if not tid:
        tid = generate_trace_id()
        _TRACE_ID_CTX.set(tid)
    return tid


def set_trace_context(trace_id: str, span_id: str) -> None:
    """Set active OpenTelemetry trace and span IDs."""
    _TRACE_ID_CTX.set(trace_id)
    _SPAN_ID_CTX.set(span_id)


def get_traceparent_header() -> str:
    """Generate standard W3C traceparent header value (00-{trace_id}-{span_id}-01)."""
    tid = get_trace_id()
    sid = _SPAN_ID_CTX.get() or generate_span_id()
    return f"00-{tid}-{sid}-01"


# ---------------------------------------------------------------------------
# OpenTelemetry Distributed Tracing Lightweight Span Context
# ---------------------------------------------------------------------------


class TraceSpan:
    """Context manager for distributed tracing spans with timing and attributes."""

    def __init__(self, operation_name: str, attributes: Optional[dict[str, Any]] = None):
        self.operation_name = operation_name
        self.attributes = attributes or {}
        self.trace_id = get_trace_id()
        self.span_id = generate_span_id()
        self.parent_span_id = _SPAN_ID_CTX.get()
        self.start_time: float = 0.0
        self.duration_ms: float = 0.0
        self._prev_span_id: str = ""

    def __enter__(self):
        self._prev_span_id = _SPAN_ID_CTX.get()
        _SPAN_ID_CTX.set(self.span_id)
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration_ms = (time.perf_counter() - self.start_time) * 1000.0
        _SPAN_ID_CTX.set(self._prev_span_id)
        if exc_val:
            self.attributes["error"] = True
            self.attributes["error.type"] = exc_type.__name__ if exc_type else "Error"
        return False


def trace_operation(operation_name: str, attributes: Optional[dict[str, Any]] = None):
    """Context manager for distributed tracing operations."""
    return TraceSpan(operation_name, attributes)


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

        # Inject trace_id onto log record if available
        if not hasattr(record, "trace_id"):
            record.trace_id = _TRACE_ID_CTX.get()

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


# ---------------------------------------------------------------------------
# Structured Log Formatters
# ---------------------------------------------------------------------------


class StructuredJsonFormatter(logging.Formatter):
    """Production JSON log formatter conforming to enterprise observability standards."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", get_correlation_id()),
            "trace_id": getattr(record, "trace_id", _TRACE_ID_CTX.get()),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


class StructuredTextFormatter(logging.Formatter):
    """Human-readable structured text formatter for local development and stdout streaming."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        corr_id = getattr(record, "correlation_id", get_correlation_id())
        msg = record.getMessage()
        formatted = f"[{ts}] [{record.levelname:<5}] [{corr_id}] [{record.name}] {msg}"
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        return formatted


# ---------------------------------------------------------------------------
# Operational Metrics Collector (In-Memory, Prometheus histogram buckets)
# ---------------------------------------------------------------------------

LATENCY_HISTOGRAM_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


def categorize_path(path: str) -> str:
    """Categorize URL path for operational metrics aggregation."""
    if "/auth" in path:
        return "auth"
    elif "/fhir" in path:
        return "fhir"
    elif "/chat" in path or "/rag" in path or "/agents" in path or "/scribe" in path:
        return "ai"
    elif "/pacs/waveforms" in path:
        return "waveforms"
    elif "/pacs" in path:
        return "pacs"
    elif "/patients" in path:
        return "patients"
    elif "/emar" in path or "/orders" in path or "/encounters" in path or "/clinical-trials" in path:
        return "clinical"
    elif "/health" in path:
        return "health"
    return "general"


class OperationalMetricsCollector:
    """Thread-safe lightweight operational metrics collector for production readiness."""

    def __init__(self):
        self._start_time = datetime.now(timezone.utc)
        self._request_count = 0
        self._error_count_4xx = 0
        self._error_count_5xx = 0
        self._total_response_time_ms = 0.0
        self._requests_by_status: dict[int, int] = {}
        self._requests_by_category: dict[str, int] = {}
        self._latency_buckets: dict[float, int] = {b: 0 for b in LATENCY_HISTOGRAM_BUCKETS}
        self._ai_requests_total = 0
        self._ai_duration_sum_ms = 0.0

    def record_request(self, status_code: int, duration_ms: float, path: str = "/") -> None:
        self._request_count += 1
        self._total_response_time_ms += duration_ms
        self._requests_by_status[status_code] = self._requests_by_status.get(status_code, 0) + 1

        cat = categorize_path(path)
        self._requests_by_category[cat] = self._requests_by_category.get(cat, 0) + 1

        duration_sec = duration_ms / 1000.0
        for b in LATENCY_HISTOGRAM_BUCKETS:
            if duration_sec <= b:
                self._latency_buckets[b] += 1

        if 400 <= status_code < 500:
            self._error_count_4xx += 1
        elif status_code >= 500:
            self._error_count_5xx += 1

    def record_ai_inference(self, duration_ms: float) -> None:
        self._ai_requests_total += 1
        self._ai_duration_sum_ms += duration_ms

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
            "avg_duration_ms": round(avg_latency, 2),
            "requests_by_status": self._requests_by_status,
            "requests_by_category": self._requests_by_category,
            "latency_histogram_buckets": self._latency_buckets,
            "ai_requests_total": self._ai_requests_total,
            "ai_avg_duration_ms": round(
                self._ai_duration_sum_ms / self._ai_requests_total if self._ai_requests_total > 0 else 0.0, 2
            ),
        }


metrics_collector = OperationalMetricsCollector()


# ---------------------------------------------------------------------------
# Correlation & Request Timing Middleware
# ---------------------------------------------------------------------------


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware that manages correlation IDs, OpenTelemetry headers, and response timing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate correlation ID
        raw_corr_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID")
        correlation_id = sanitize_correlation_id(raw_corr_id)

        # Extract or parse W3C traceparent
        raw_traceparent = request.headers.get("traceparent")
        if raw_traceparent and _TRACEPARENT_REGEX.match(raw_traceparent.strip()):
            m = _TRACEPARENT_REGEX.match(raw_traceparent.strip())
            if m:
                set_trace_context(trace_id=m.group(1), span_id=m.group(2))
        else:
            set_trace_context(trace_id=generate_trace_id(), span_id=generate_span_id())

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
            response.headers["traceparent"] = get_traceparent_header()

            # Record metrics
            metrics_collector.record_request(
                status_code=response.status_code,
                duration_ms=duration_ms,
                path=safe_path,
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
            metrics_collector.record_request(status_code=500, duration_ms=duration_ms, path=safe_path)
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

