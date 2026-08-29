# Phase 9.0.4 — Production Observability, Reliability & Operational Monitoring

## 1. Purpose

Phase 9.0.4 delivers enterprise-grade **Production Observability, Reliability & Operational Monitoring** for MediGen AI.

As a healthcare-critical clinical decision support platform, the system must guarantee:
- End-to-end request tracing and correlation across API calls, business services, and asynchronous task workers.
- Strict **Zero-PHI and zero-credential leakage** guarantees across all application and operational logs.
- Automated sanitization filters intercepting Bearer tokens, JWTs, AWS credentials, email addresses, and clinical identifiers.
- Deep readiness probes verifying critical dependencies (PostgreSQL database, ChromaDB vector store, background task worker pool).
- Real-time in-memory operational metrics collection (request latencies, error distributions, task queue depth) with zero external SaaS dependencies.
- Standardized, safe operational error responses returning correlation IDs without leaking internal stack traces or secrets.

---

## 2. Architecture Overview

```
                      Client HTTP Request (optional X-Correlation-ID)
                                         |
                                         v
                         +-------------------------------+
                         |   CorrelationIdMiddleware     |
                         |  - Extract / sanitize ID      |
                         |  - Bind contextvars context   |
                         |  - Track latency (perf_counter)|
                         |  - Inject response headers    |
                         +-------------------------------+
                                         |
                                         v
                         +-------------------------------+
                         |   Structured Logging Engine   |
                         |  - PHISanitizingFilter        |
                         |  - Auto correlation_id binding|
                         |  - JSON & Text formatters     |
                         +-------------------------------+
                                         |
            +----------------------------+----------------------------+
            |                                                         |
            v                                                         v
+-------------------------------+                         +-------------------------------+
|  Health & Readiness Probes    |                         |  Background Task Workers      |
|  - GET /health (Liveness)     |                         |  - Contextvars correlation    |
|  - GET /ready (Readiness)     |                         |  - Task queue metrics         |
|  - GET /api/v1/health/live    |                         |  - Execution timing & status  |
|  - GET /api/v1/health/ready   |                         +-------------------------------+
|  - GET /api/v1/health/metrics |
+-------------------------------+
```

---

## 3. Request Correlation Tracing

### `CorrelationIdMiddleware`

- Intercepts incoming HTTP requests.
- Inspects `X-Correlation-ID` and `X-Request-ID` headers.
- If present, validates against alphanumeric/hyphen/underscore format (4–64 characters).
- If absent or invalid, automatically generates a unique identifier: `req-YYYYMMDD-XXXXXXXX`.
- Uses Python `contextvars` (`_CORRELATION_ID_CTX`) to maintain asynchronous context across coroutines, thread pool workers, and service calls.
- Injects standard response headers:
  - `X-Correlation-ID: <id>`
  - `X-Response-Time-Ms: <duration_ms>`

---

## 4. Zero-PHI & Credential Sanitization

### `PHISanitizingFilter`

An automated `logging.Filter` attached to all handlers that intercepts and sanitizes log output before emission:
- **Bearer Tokens**: `Bearer [REDACTED]`
- **JSON Web Tokens (JWT)**: `[JWT_REDACTED]`
- **AWS Credentials**: `[AWS_KEY_REDACTED]`
- **Email Addresses**: `[EMAIL_REDACTED]`
- **Passwords & Keys**: `password=[REDACTED]`, `api_key=[REDACTED]`, `secret=[REDACTED]`
- Automatically attaches `record.correlation_id` to every emitted log record.

---

## 5. Structured Formatters

| Formatter | Description | Use Case |
|---|---|---|
| `StructuredJsonFormatter` | Standard single-line JSON log output containing `timestamp`, `level`, `logger`, `message`, `correlation_id`, and operational extras. | Production cloud log aggregation (CloudWatch, Datadog, ELK). |
| `StructuredTextFormatter` | Formatted human-readable output: `[timestamp] [LEVEL] [correlation_id] [logger] message`. | Local development, terminal consoles, and debugging. |

---

## 6. Health, Readiness & Metrics Endpoints

| Endpoint | Probe Type | Purpose | Status Codes |
|---|---|---|---|
| `GET /health` | Liveness | Lightweight probe verifying HTTP server process is running | `200 OK` |
| `GET /api/v1/health/live` | Liveness | API-namespaced process liveness check | `200 OK` |
| `GET /ready` | Readiness | Root readiness probe verifying PostgreSQL database connectivity | `200 OK` / `503 Unavailable` |
| `GET /api/v1/health/ready` | Deep Readiness | Comprehensive dependency probe (database, vector store, task worker pool, drug knowledge) | `200 OK` / `503 Unavailable` |
| `GET /api/v1/health/metrics` | Observability | In-memory operational metrics (uptime, request counts, 4xx/5xx errors, avg latency, task queue counts) | `200 OK` |

### Sample Response: `GET /api/v1/health/ready`

```json
{
  "status": "ready",
  "ready": true,
  "service": "MediGen AI",
  "version": "0.1.0",
  "components": {
    "database": { "status": "connected", "healthy": true },
    "vector_store": { "status": "available", "healthy": true, "provider": "mock", "collection": "medical_documents" },
    "task_worker": { "status": "ready", "healthy": true, "provider": "local", "metrics": { "queued": 0, "running": 0, "completed": 5, "failed": 0, "total": 5, "max_workers": 4 } },
    "drug_knowledge": { "provider": "mock", "healthy": true }
  },
  "correlation_id": "req-20260829-A1B2C3D4"
}
```

---

## 7. Global Safe Error Handling

Unhandled exceptions are intercepted by a global exception handler in FastAPI:
- Logged internally with full stack trace, exception type, and active `correlation_id`.
- Public response returns HTTP 500 with safe, sanitized JSON:
  ```json
  {
    "status": "error",
    "error_code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected internal server error occurred. Please reference the correlation ID for support.",
    "correlation_id": "req-20260829-A1B2C3D4"
  }
  ```
- Sensitive connection strings, database passwords, and internal file paths are strictly prevented from appearing in public error responses.

---

## 8. Configuration

```bash
# Production Observability Configuration (Phase 9.0.4)
LOG_LEVEL="INFO"
LOG_FORMAT="text"  # 'text' | 'json'
METRICS_ENABLED=True
```

---

## 9. Verification & Testing

The Phase 9.0.4 test suite (`backend/tests/test_observability.py`) contains 23 tests verifying:
- Correlation ID generation, preservation, and sanitization
- Context variable isolation across concurrent calls
- `PHISanitizingFilter` regex masking (tokens, passwords, emails, AWS keys)
- Structured JSON and text formatter outputs
- Correlation ID and response time header injection
- Liveness and readiness endpoints (including simulated database outage returning 503)
- Operational metrics collection snapshot
- Background task correlation ID propagation
- Global exception handler returning sanitized JSON with correlation IDs
