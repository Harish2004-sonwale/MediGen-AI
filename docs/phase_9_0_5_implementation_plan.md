# Phase 9.0.5 Implementation Plan — Advanced Production Deployment & Scalability

## 1. Goal
Implement enterprise production deployment readiness and scalability architecture for MediGen AI without introducing mandatory cloud infrastructure or breaking existing offline workflows.

## 2. Proposed Architecture & Changes

### 2.1 Production Configuration & Environment Validation (`backend/app/core/config.py`)
- Add environment enum/string support: `ENVIRONMENT: "development" | "staging" | "production" | "test"`.
- Add `CORS_ORIGINS: str = "*"` supporting comma-separated list or JSON array for origin whitelisting in production.
- Add `ASGI_WORKERS: int = 1` for tuning uvicorn process workers.
- Implement `validate_production_settings()` method on `Settings`:
  - Rejects default placeholder `JWT_SECRET_KEY` in `production` and `staging`.
  - Rejects `DEBUG=True` when `ENVIRONMENT="production"`.
  - Validates `DATABASE_URL` structure.
  - Safe sanitization method `safe_dump()` that masks passwords, keys, and tokens for logging.
- Update `backend/.env.example` with new deployment settings.

### 2.2 Modern ASGI Lifespan & Lifecycle Management (`backend/app/main.py`)
- Replace legacy event handlers with FastAPI `@asynccontextmanager` `lifespan(app: FastAPI)`:
  - **Startup**: Log sanitized configuration summary (zero secrets/PHI), verify database connection pool, initialize task worker provider.
  - **Shutdown**: Gracefully drain and shut down background task provider thread pool (`provider.shutdown(wait=True)`), log shutdown completion.
- Configure `CORSMiddleware` with `settings.get_cors_origins()` for production host isolation.

### 2.3 Container & Deployment Support (`Dockerfile`, `.dockerignore`, `docker-compose.prod.yml`)
- `Dockerfile`:
  - Lean Python 3.11-slim base.
  - Security hardening: Non-root user (`appuser` with UID 10001).
  - Explicit working directory `/app`.
  - Health check instruction using `/health`.
  - Entrypoint running `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- `.dockerignore`:
  - Exclude `.git`, `.env*`, `data/`, `vector_db/`, `__pycache__`, `.pytest_cache`, virtualenvs, credentials, and logs.
- `docker-compose.prod.yml`:
  - Example production stack with PostgreSQL 16, MediGen AI API container with healthchecks, and optional Redis container.

### 2.4 Tests (`backend/tests/test_production_deployment.py`)
- Production settings validation (insecure JWT rejection in production, debug rejection).
- Safe development defaults preservation.
- CORS origins parsing logic.
- Lifespan startup and shutdown execution.
- Dockerfile non-root security and healthcheck validation.
- Zero credential / secret leakage in config dump and string representations.

### 2.5 Documentation (`docs/phase_9_0_5.md`, `README.md`)
- Detailed architecture, operational checklist, multi-worker scaling, database connection pooling formulas, graceful shutdown, backup/restore, and container deployment guide.
- Update `README.md` to mark Phase 9.0.5 Completed & Verified ✅.

## 3. Verification Plan
1. Run unit & integration tests: `pytest tests/test_production_deployment.py -v --tb=short`
2. Run full regression suite: `pytest -q` (all 300+ tests passing)
3. Validate Alembic migration chain: `alembic upgrade head --sql`
4. Verify clean `git diff --check` and zero secret tracking.
