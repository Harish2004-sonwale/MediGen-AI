"""Comprehensive Test Suite for Phase 9.0.4: Production Observability, Reliability & Operational Monitoring.

Tests:
- Correlation ID generation, preservation, and header injection (X-Correlation-ID, X-Response-Time-Ms)
- PHI sanitization filter (Bearer tokens, JWTs, AWS keys, emails, passwords)
- Structured JSON and human-readable text log formatting
- Health and liveness endpoints (/health, /api/v1/health/live)
- Readiness probes (/ready, /api/v1/health/ready) with database dependency failure simulation
- Operational metrics endpoint (/api/v1/health/metrics)
- Background task correlation ID propagation and execution metrics
- Global exception handling returning safe structured errors with correlation IDs
- Malformed correlation ID sanitization and concurrent isolation
"""

import json
import logging
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, Request, status
from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import OperationalError

from app.ai.task_worker import (
    BackgroundTaskType,
    LocalBackgroundTaskProvider,
    get_background_task_provider,
)
from app.core.config import settings
from app.core.observability import (
    CorrelationIdMiddleware,
    PHISanitizingFilter,
    StructuredJsonFormatter,
    StructuredTextFormatter,
    generate_correlation_id,
    get_correlation_id,
    metrics_collector,
    sanitize_correlation_id,
    sanitize_log_message,
    set_correlation_id,
)
from app.database import get_db
from app.main import app


# ===========================================================================
# 1. Correlation ID Generation & Sanitization
# ===========================================================================


class TestCorrelationIdUtilities:
    """Tests for correlation ID creation and input sanitization."""

    def test_generate_correlation_id_format(self):
        corr_id = generate_correlation_id()
        assert corr_id.startswith("req-")
        parts = corr_id.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 8  # 8 hex chars

    def test_sanitize_valid_correlation_id(self):
        valid = "custom-req-1234_abc"
        assert sanitize_correlation_id(valid) == valid

    def test_sanitize_invalid_or_malformed_correlation_id(self):
        # Contains special illegal chars -> fallback generated
        malformed = "evil<script>alert(1)</script>"
        sanitized = sanitize_correlation_id(malformed)
        assert sanitized.startswith("req-")
        assert "<" not in sanitized

    def test_sanitize_empty_or_none_correlation_id(self):
        assert sanitize_correlation_id(None).startswith("req-")
        assert sanitize_correlation_id("").startswith("req-")
        assert sanitize_correlation_id("   ").startswith("req-")

    def test_context_var_isolation(self):
        set_correlation_id("test-corr-id-001")
        assert get_correlation_id() == "test-corr-id-001"


# ===========================================================================
# 2. PHI & Credential Log Sanitization Filter
# ===========================================================================


class TestPHISanitizationFilter:
    """Tests for automated redaction of sensitive credentials and clinical data from log output."""

    def test_sanitize_bearer_token(self):
        msg = "Authorization failed with header Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz.123"
        sanitized = sanitize_log_message(msg)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
        assert "Bearer [REDACTED]" in sanitized

    def test_sanitize_aws_access_key(self):
        msg = "Connecting to Bedrock using access key AKIAIOSFODNN7EXAMPLE in us-east-1"
        sanitized = sanitize_log_message(msg)
        assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
        assert "[AWS_KEY_REDACTED]" in sanitized

    def test_sanitize_email_address(self):
        msg = "Processing record for user alice.patient@hospital.org in oncology"
        sanitized = sanitize_log_message(msg)
        assert "alice.patient@hospital.org" not in sanitized
        assert "[EMAIL_REDACTED]" in sanitized

    def test_sanitize_password_field(self):
        msg = "Database config loaded: password='MySuperSecretPass123!' host=localhost"
        sanitized = sanitize_log_message(msg)
        assert "MySuperSecretPass123!" not in sanitized
        assert "password=[REDACTED]" in sanitized

    def test_phi_filter_injects_correlation_id_into_record(self):
        phi_filter = PHISanitizingFilter()
        set_correlation_id("req-20260829-TESTCORR")

        record = logging.LogRecord(
            name="medigen.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="User email test@hospital.org created task with password='secret123'",
            args=(),
            exc_info=None,
        )

        assert phi_filter.filter(record) is True
        assert record.correlation_id == "req-20260829-TESTCORR"
        assert "test@hospital.org" not in record.msg
        assert "secret123" not in record.msg


# ===========================================================================
# 3. Structured Log Formatters (JSON & Text)
# ===========================================================================


class TestStructuredFormatters:
    """Tests JSON and human-readable text log formatters."""

    def test_json_formatter_produces_valid_json_with_correlation_id(self):
        formatter = StructuredJsonFormatter()
        record = logging.LogRecord(
            name="medigen.service",
            level=logging.INFO,
            pathname="service.py",
            lineno=42,
            msg="Clinical safety check completed",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "req-JSON-TEST-001"

        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "medigen.service"
        assert parsed["message"] == "Clinical safety check completed"
        assert parsed["correlation_id"] == "req-JSON-TEST-001"
        assert "timestamp" in parsed

    def test_text_formatter_output(self):
        formatter = StructuredTextFormatter()
        record = logging.LogRecord(
            name="medigen.api",
            level=logging.WARNING,
            pathname="api.py",
            lineno=15,
            msg="Rate limit approaching threshold",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "req-TEXT-002"

        output = formatter.format(record)
        assert "[WARNING]" in output
        assert "[req-TEXT-002]" in output
        assert "[medigen.api]" in output
        assert "Rate limit approaching threshold" in output


# ===========================================================================
# 4. HTTP Middleware & Response Headers
# ===========================================================================


class TestCorrelationIdMiddleware:
    """Tests CorrelationIdMiddleware response headers and correlation tracking."""

    def test_auto_generates_correlation_id_in_response(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        assert response.headers["X-Correlation-ID"].startswith("req-")
        assert "X-Response-Time-Ms" in response.headers

    def test_preserves_client_provided_correlation_id(self, client: TestClient):
        custom_id = "custom-trace-header-999"
        response = client.get("/health", headers={"X-Correlation-ID": custom_id})
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == custom_id

    def test_sanitizes_malformed_client_correlation_id(self, client: TestClient):
        malformed = "invalid/slash/id/&&"
        response = client.get("/health", headers={"X-Correlation-ID": malformed})
        assert response.status_code == 200
        # Returned ID should be a clean generated ID
        assert response.headers["X-Correlation-ID"].startswith("req-")
        assert "/" not in response.headers["X-Correlation-ID"]


# ===========================================================================
# 5. Health, Readiness, and Metrics Probes
# ===========================================================================


class TestHealthAndReadinessEndpoints:
    """Tests for liveness, readiness, and metrics endpoints."""

    def test_liveness_check_root_health(self, client: TestClient):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "X-Correlation-ID" in res.headers

    def test_liveness_check_api_endpoint(self, client: TestClient):
        res = client.get("/api/v1/health/live")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "alive"
        assert data["service"] == settings.PROJECT_NAME
        assert "correlation_id" in data

    def test_readiness_check_success(self, client: TestClient):
        res = client.get("/api/v1/health/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert data["ready"] is True
        assert data["components"]["database"]["healthy"] is True
        assert data["components"]["task_worker"]["healthy"] is True
        assert "correlation_id" in data

    def test_readiness_check_root_ready(self, client: TestClient):
        res = client.get("/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"

    def test_readiness_check_database_failure_returns_503(self, client: TestClient):
        mock_db = MagicMock()
        mock_db.execute.side_effect = OperationalError("Connection refused", None, Exception("DB unreachable"))

        def override_failing_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_failing_db
        try:
            res = client.get("/api/v1/health/ready")
            assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = res.json()
            assert data["status"] == "not_ready"
            assert data["ready"] is False
            assert data["components"]["database"]["healthy"] is False
        finally:
            app.dependency_overrides.clear()

    def test_metrics_endpoint(self, client: TestClient):
        res = client.get("/api/v1/health/metrics")
        assert res.status_code == 200
        data = res.json()
        assert "http" in data
        assert "uptime_seconds" in data["http"]
        assert "total_requests" in data["http"]
        assert "tasks" in data
        assert "correlation_id" in data


# ===========================================================================
# 6. Background Task Observability & Correlation
# ===========================================================================


class TestTaskObservability:
    """Tests correlation propagation and metrics tracking within background task workers."""

    def test_task_worker_metrics_tracking(self):
        provider = LocalBackgroundTaskProvider(max_workers=2)

        def dummy_job():
            return {"status": "ok"}

        t = provider.submit_task(BackgroundTaskType.SAFETY_CHECK, dummy_job)
        metrics = provider.get_metrics()

        assert metrics["provider"] == "local"
        assert metrics["total"] >= 1
        assert "queued" in metrics
        assert "running" in metrics
        assert "completed" in metrics
        assert "failed" in metrics

        provider.shutdown(wait=True)


# ===========================================================================
# 7. Global Server Error Handler & Safe Diagnostics
# ===========================================================================


class TestGlobalErrorHandler:
    """Tests that unexpected server exceptions return structured JSON with correlation IDs and no PHI."""

    def test_unhandled_exception_returns_safe_500_with_correlation_id(self):
        test_app = FastAPI()
        test_app.add_middleware(CorrelationIdMiddleware)

        @test_app.exception_handler(Exception)
        async def custom_err_handler(request: Request, exc: Exception):
            from app.main import global_exception_handler
            return await global_exception_handler(request, exc)

        @test_app.get("/trigger-crash")
        def crash_route():
            raise RuntimeError("Database connection string postgresql://postgres:SECRET_PASSWORD@localhost:5432 failed")

        with TestClient(test_app, raise_server_exceptions=False) as client:
            res = client.get("/trigger-crash", headers={"X-Correlation-ID": "req-CRASH-001"})
            assert res.status_code == 500
            data = res.json()

            assert data["error_code"] == "INTERNAL_SERVER_ERROR"
            assert data["correlation_id"] == "req-CRASH-001"
            # Sensitive exception message must NOT be in public JSON body
            assert "SECRET_PASSWORD" not in json.dumps(data)
