# Phase 9.0.4 Implementation Plan: Production Observability, Reliability & Operational Monitoring

## 1. Overview & Current Gaps

MediGen AI has completed Milestones 1–8 and Phases 9.0.1–9.0.3 (FHIR R4 interoperability, drug knowledge adapter, and background asynchronous task workers).
Current gaps in production operational readiness include:
- **Request Tracing**: Lack of end-to-end correlation IDs connecting API HTTP requests to service calls, background tasks, and error logs.
- **Structured Logging**: Need for uniform, machine-readable JSON logging format with correlation context, timestamps, and log levels.
- **PHI & Credential Sanitization**: Automated safeguard filter in the logging pipeline to prevent accidental logging of PHI, passwords, and tokens.
- **Comprehensive Health & Readiness Probes**: Existing `/health` is a simple liveness check; need `/ready` and `/health/ready` that probe database connectivity, vector store health, and background worker state.
- **Worker & System Metrics**: Visibility into background worker queue statistics, task execution timings, and error rates.
- **Standardized Error Handling**: Uniform operational error responses returning `correlation_id` for developer diagnostics without leaking internal implementation details.

---

## 2. Architecture & Design

```
                   Incoming Client Request (with optional X-Correlation-ID)
                                         |
                                         v
                         +-------------------------------+
                         |   CorrelationIdMiddleware     |
                         |  - Extract / generate ID      |
                         |  - Bind contextvars context   |
                         |  - Measure response timing    |
                         +-------------------------------+
                                         |
                                         v
                         +-------------------------------+
                         |   Structured Logging Engine   |
                         |  - JSON / Text Formatters     |
                         |  - PHISanitizingFilter        |
                         |  - Auto correlation_id binding|
                         +-------------------------------+
                                         |
            +----------------------------+----------------------------+
            |                                                         |
            v                                                         v
+-------------------------------+                         +-------------------------------+
|  Health & Readiness Probes    |                         |   Background Task Worker      |
|  - GET /health (Liveness)     |                         |  - Task queue observability   |
|  - GET /ready (Readiness)     |                         |  - Propagate correlation_id   |
|  - GET /health/ready          |                         |  - Execution timing & metrics |
|  - GET /health/metrics        |                         |  - Safe failure diagnostics   |
+-------------------------------+                         +-------------------------------+
```

---

## 3. Planned Components

### A. Core Observability Module (`backend/app/core/observability.py`)
- `get_correlation_id()`, `set_correlation_id()` using Python's standard `contextvars`.
- `CorrelationIdMiddleware`: FastAPI middleware that extracts or generates correlation IDs, tracks request duration in milliseconds, and injects `X-Correlation-ID` and `X-Response-Time-Ms` headers.
- `PHISanitizingFilter`: `logging.Filter` that masks sensitive data patterns (e.g. Bearer tokens, passwords, email addresses, SSN/MRN patterns) and prevents accidental PHI logging.
- `StructuredJsonFormatter`: Outputs standardized JSON log lines containing `timestamp`, `level`, `logger`, `message`, `correlation_id`, and operational extras.
- `configure_logging(log_level, log_format)`: Configures the root logger with the sanitizing filter and structured formatter.

### B. Health & Readiness Endpoints (`backend/app/api/v1/endpoints/health.py` and `backend/app/main.py`)
- `GET /health` / `GET /health/live`: Liveness check (process alive, version, environment).
- `GET /ready` / `GET /health/ready`: Readiness check probing:
  - Database connectivity (`SELECT 1`)
  - Background worker availability (`get_background_task_provider()`)
  - Vector store status
  - Drug knowledge provider status
- `GET /health/metrics`: In-memory operational metrics snapshot (request counts, active workers, task execution statistics).

### C. Task Worker Integration (`backend/app/ai/task_worker.py`)
- Propagate `correlation_id` from the submitting context to the executing worker thread.
- Add `get_metrics()` to `BaseBackgroundTaskProvider` to inspect queue depth, total completed, total failed, and active workers.

### D. Global Error Handlers (`backend/app/main.py`)
- Catch unhandled server exceptions, log with `correlation_id` and stack trace internally, but return a clean, safe JSON response with `correlation_id`, `error_code="INTERNAL_SERVER_ERROR"`, and no PHI or secrets.

---

## 4. Security & Privacy Boundaries

- **Zero PHI in Logs**: Strict adherence to healthcare logging standards. Logs contain only public entity IDs, task IDs, durations, HTTP codes, and sanitized metadata.
- **Zero Credentials**: Passwords, JWT secrets, AWS keys, and openFDA keys are masked by `PHISanitizingFilter` and never logged.
- **Safe Diagnostics**: Public API error responses never expose database schema details, stack traces, or internal server paths.

---

## 5. Testing Strategy (`backend/tests/test_observability.py`)

1. Correlation ID generation when omitted by client
2. Correlation ID preservation when provided in `X-Correlation-ID`
3. Response header validation (`X-Correlation-ID`, `X-Response-Time-Ms`)
4. Context variable propagation across async calls
5. `PHISanitizingFilter` pattern masking (Bearer tokens, passwords, emails)
6. Liveness probe `/health` and `/health/live` returns 200
7. Readiness probe `/ready` and `/health/ready` returns 200 when dependencies are healthy
8. Readiness probe returns 503 with disconnected status when DB check fails
9. Metrics probe `/health/metrics` returns operational statistics
10. Background task execution logs and metrics correlation
11. Global exception handler returns sanitized JSON with `correlation_id`
12. Concurrent requests maintain isolated correlation IDs without cross-talk

---

## 6. Configuration Additions

In `backend/app/core/config.py` and `backend/.env.example`:
```bash
LOG_LEVEL="INFO"
LOG_FORMAT="json"
METRICS_ENABLED=True
```
