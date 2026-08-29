# Phase 9.0.5 — Advanced Production Deployment & Scalability

## 1. Objective

Phase 9.0.5 provides enterprise-grade **Production Deployment & Scalability Architecture** for MediGen AI, ensuring high availability, security hardening, container orchestration readiness, and scalable concurrency across compute, database, vector index, and background processing layers.

---

## 2. Architecture & Deployment Overview

```
                                  [ Internet / Ingress ]
                                            |
                                            v (HTTPS / TLS Termination)
                             +-------------------------------+
                             |    Reverse Proxy / Ingress    |
                             |  - Host & Origin Filtering    |
                             |  - TLS 1.3 Termination        |
                             |  - Ingress Rate Limiting      |
                             +-------------------------------+
                                            |
                                            v (HTTP / Reverse Proxy)
                             +-------------------------------+
                             |    MediGen AI ASGI Cluster    |
                             |  - Non-root container (10001) |
                             |  - Lifespan Manager           |
                             |  - Correlation ID Middleware  |
                             |  - Dynamic CORS Whitelist     |
                             |  - PHI Sanitizing Logger      |
                             +-------------------------------+
                                     |               |
                    +----------------+               +----------------+
                    |                                                 |
                    v                                                 v
    +-------------------------------+                 +-------------------------------+
    |  PostgreSQL Database (v16)    |                 |   Task Worker Architecture    |
    |  - Connection Pool (5-15)     |                 |  - In-memory Thread Pool (dev)|
    |  - Row-level patient scoping  |                 |  - Celery / Redis (prod scale)|
    |  - Prepared statement cache   |                 |  - Graceful shutdown drain    |
    +-------------------------------+                 +-------------------------------+
                    |                                                 |
                    +----------------+               +----------------+
                                     |               |
                                     v               v
                             +-------------------------------+
                             |   ChromaDB Vector Storage     |
                             |  - Persistent volume mount    |
                             |  - In-memory fallback (tests) |
                             |  - Patient chunk isolation    |
                             +-------------------------------+
```

---

## 3. Configuration & Environment Validation

The application strictly validates configuration based on `ENVIRONMENT` (`development` | `staging` | `production` | `test`).

### Production Security Constraints (`validate_production_settings()`)
When running in `production` or `staging`:
1. **JWT Secret Strength**: `JWT_SECRET_KEY` must be cryptographically secure (minimum 32 characters) and cannot contain development placeholder tokens.
2. **Debug Mode Prohibition**: `DEBUG` must be set to `False`.
3. **Database Credentials**: `DATABASE_URL` cannot contain default placeholder passwords.
4. **CORS Restrictions**: `CORS_ORIGINS` cannot be wildcard `*` in production; it must explicitly enumerate authorized client hostnames.

### Safe Configuration Serialization (`safe_dump()`)
All credential fields (`JWT_SECRET_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AWS_SECRET_ACCESS_KEY`, `OPENFDA_API_KEY`, `CELERY_BROKER_URL`, database connection passwords) are automatically masked as `[REDACTED]` whenever configuration is dumped for logging or diagnostics.

---

## 4. Application Deployment & ASGI Lifespan

### Graceful Lifecycle Management (`lifespan`)
FastAPI's modern `@asynccontextmanager` manages the application lifecycle:
- **Startup**:
  - Validates production settings and logs diagnostic status.
  - Initializes background task worker provider.
  - Verifies connection pools and runtime directories (`data/medical_documents`, `data/vector_db`).
- **Shutdown**:
  - Intercepts SIGTERM / SIGINT signals.
  - Gracefully drains active background task workers (`worker_provider.shutdown(wait=True)`).
  - Closes database connection pools safely without dropping active in-flight clinical transactions.

---

## 5. Multi-Worker & Concurrency Scaling

### API Process Concurrency (`ASGI_WORKERS`)
- Production ASGI runner utilizes multiple Uvicorn worker processes:
  $$\text{Workers} = 2 \times \text{CPU Cores} + 1$$
- Database connection pool sizes are tuned per worker:
  $$\text{Total DB Connections} = \text{ASGI\_WORKERS} \times (\text{DB\_POOL\_SIZE} + \text{DB\_MAX\_OVERFLOW})$$

### Background Task Concurrency (`BACKGROUND_TASK_WORKERS`)
- Configurable concurrency bounds for background document OCR and timeline compilation (defaults to 4 worker threads locally).
- For distributed multi-node clusters, `BACKGROUND_TASK_PROVIDER=celery` routes jobs across distributed Redis queues without code changes.

---

## 6. Container Security & Hardening

### `Dockerfile` Specifications
- **Base Image**: Lean Python 3.11 slim image.
- **Unprivileged Non-Root User**: Runs under dedicated service user `appuser` (UID `10001`) to comply with HIPAA security guidelines.
- **Healthcheck Probe**: Automatic container healthchecks querying `/health` liveness probe.
- **Zero Baked Secrets**: No `.env` files, API keys, or database files bundled into the container layer.

### `.dockerignore` Specifications
- Excludes test caches, temporary files, local databases (`*.db`, `*.sqlite3`), raw vector stores, `.git`, and private key materials.

---

## 7. Operational Deployment Checklist

Before deploying MediGen AI to a production cluster:

- [ ] Set `ENVIRONMENT="production"`.
- [ ] Set `DEBUG=False`.
- [ ] Generate and set a cryptographically secure `JWT_SECRET_KEY` (minimum 32 random characters).
- [ ] Configure `DATABASE_URL` pointing to hardened PostgreSQL cluster with SSL enabled.
- [ ] Set explicit allowed web/mobile domains in `CORS_ORIGINS` (e.g., `https://app.medigen.ai,https://admin.medigen.ai`).
- [ ] Mount persistent storage volume for `/app/backend/data`.
- [ ] Set `LOG_FORMAT="json"` for centralized cloud log indexing.
- [ ] Verify readiness probe at `GET /ready` returns HTTP 200.

---

## 8. Verification & Testing

The Phase 9.0.5 test suite (`backend/tests/test_production_deployment.py`) verifies:
- Validation of hardened production configuration rules (100% pass)
- Rejection of insecure default JWT secrets and debug mode in production
- CORS origin parsing across comma-separated lists and JSON arrays
- Safe credential and connection string redaction in `safe_dump()`
- ASGI lifespan startup diagnostics and graceful worker shutdown
- Non-root user compliance and healthcheck definition in `Dockerfile`
- Concurrency limit configuration on task worker providers
