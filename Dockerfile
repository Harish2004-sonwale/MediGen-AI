# ==============================================================================
# MediGen AI - Production Docker Container
# Multi-stage / Hardened Non-Root ASGI Deployment Image
# ==============================================================================

FROM python:3.11-slim AS builder

WORKDIR /build

# Install system build dependencies if necessary
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements into wheels
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ==============================================================================
# Final Production Image
# ==============================================================================
FROM python:3.11-slim AS final

# Create a non-root unprivileged service user for security
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

WORKDIR /app

# Install runtime PostgreSQL client library
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app/backend

# Create runtime directories with non-root ownership
RUN mkdir -p /app/backend/data/medical_documents /app/backend/data/vector_db && \
    chown -R appuser:appgroup /app

# Copy application source code
COPY --chown=appuser:appgroup backend/ /app/backend/

# Switch to unprivileged non-root user
USER appuser

# Expose standard ASGI application port
EXPOSE 8000

# Container Healthcheck verifying /health liveness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Production ASGI Entrypoint
WORKDIR /app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
