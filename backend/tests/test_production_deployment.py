"""Comprehensive Test Suite for Phase 9.0.5: Advanced Production Deployment & Scalability.

Tests:
- Production configuration validation and security constraints (JWT secret strength, DEBUG mode, CORS restriction)
- Safe development defaults (offline mock providers, permissive dev CORS, non-blocking startup)
- CORS origin parsing and sanitization across comma-separated lists and JSON arrays
- Safe configuration dump redacting credentials, API keys, and connection passwords
- ASGI Lifespan lifecycle management (startup initialization, graceful worker shutdown)
- Container configuration validation (Dockerfile non-root user, healthcheck instruction, .dockerignore)
- Background task worker pool scalability & concurrency bounds
"""

from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.ai.task_worker import (
    BackgroundTaskType,
    LocalBackgroundTaskProvider,
    get_background_task_provider,
)
from app.core.config import Settings, settings
from app.main import app, lifespan


# ===========================================================================
# 1. Production Configuration & Environment Validation
# ===========================================================================


class TestProductionConfigurationValidation:
    """Tests environment-driven configuration validation and production hardening rules."""

    def test_safe_development_defaults(self):
        dev_settings = Settings(ENVIRONMENT="development")
        assert dev_settings.is_production() is False
        errors = dev_settings.validate_production_settings()
        assert len(errors) == 0

    def test_valid_hardened_production_configuration(self):
        prod_settings = Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET_KEY="A_Very_Long_And_Cryptographically_Secure_Secret_Key_2026!",
            DATABASE_URL="postgresql+psycopg://medigen_admin:ComplexProdPass987!@db.internal:5432/medigen_ai",
            CORS_ORIGINS="https://app.medigen.ai,https://portal.medigen.ai",
        )
        assert prod_settings.is_production() is True
        errors = prod_settings.validate_production_settings()
        assert len(errors) == 0

    def test_production_rejects_insecure_default_jwt_secret(self):
        insecure_settings = Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET_KEY="YOUR_JWT_SECRET_KEY_CHANGE_IN_PRODUCTION",
            DATABASE_URL="postgresql+psycopg://postgres:pass@db.internal:5432/medigen_ai",
            CORS_ORIGINS="https://app.medigen.ai",
        )
        errors = insecure_settings.validate_production_settings()
        assert any("Insecure JWT_SECRET_KEY" in err for err in errors)

    def test_production_rejects_short_jwt_secret(self):
        insecure_settings = Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET_KEY="short-secret",
            DATABASE_URL="postgresql+psycopg://postgres:pass@db.internal:5432/medigen_ai",
            CORS_ORIGINS="https://app.medigen.ai",
        )
        errors = insecure_settings.validate_production_settings()
        assert any("at least 32 characters" in err for err in errors)

    def test_production_rejects_debug_mode_enabled(self):
        insecure_settings = Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            JWT_SECRET_KEY="Valid_Cryptographically_Secure_Production_Secret_Key_123456",
            DATABASE_URL="postgresql+psycopg://postgres:pass@db.internal:5432/medigen_ai",
            CORS_ORIGINS="https://app.medigen.ai",
        )
        errors = insecure_settings.validate_production_settings()
        assert any("DEBUG mode must be set to False" in err for err in errors)

    def test_production_rejects_placeholder_database_password(self):
        insecure_settings = Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET_KEY="Valid_Cryptographically_Secure_Production_Secret_Key_123456",
            DATABASE_URL="postgresql+psycopg://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/medigen_ai",
            CORS_ORIGINS="https://app.medigen.ai",
        )
        errors = insecure_settings.validate_production_settings()
        assert any("placeholder password" in err for err in errors)

    def test_production_rejects_wildcard_cors(self):
        insecure_settings = Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            JWT_SECRET_KEY="Valid_Cryptographically_Secure_Production_Secret_Key_123456",
            DATABASE_URL="postgresql+psycopg://postgres:ValidPass123!@db.internal:5432/medigen_ai",
            CORS_ORIGINS="*",
        )
        errors = insecure_settings.validate_production_settings()
        assert any("CORS_ORIGINS cannot be wildcard" in err for err in errors)


# ===========================================================================
# 2. CORS Origins Parsing
# ===========================================================================


class TestCORSOriginsParsing:
    """Tests dynamic CORS origins parsing for single, comma-separated, and JSON array definitions."""

    def test_parse_wildcard_cors(self):
        s = Settings(CORS_ORIGINS="*")
        assert s.get_cors_origins() == ["*"]

    def test_parse_comma_separated_origins(self):
        s = Settings(CORS_ORIGINS="https://app.medigen.ai, https://admin.medigen.ai,http://localhost:3000")
        assert s.get_cors_origins() == [
            "https://app.medigen.ai",
            "https://admin.medigen.ai",
            "http://localhost:3000",
        ]

    def test_parse_json_array_origins(self):
        s = Settings(CORS_ORIGINS='["https://app.medigen.ai", "https://mobile.medigen.ai"]')
        assert s.get_cors_origins() == [
            "https://app.medigen.ai",
            "https://mobile.medigen.ai",
        ]

    def test_parse_empty_cors_defaults_to_wildcard(self):
        s = Settings(CORS_ORIGINS="")
        assert s.get_cors_origins() == ["*"]


# ===========================================================================
# 3. Safe Configuration Dumping & Redaction
# ===========================================================================


class TestSafeConfigurationDumping:
    """Tests that logging or serializing application configuration redacts all secrets and passwords."""

    def test_safe_dump_redacts_credentials(self):
        s = Settings(
            JWT_SECRET_KEY="SecretJWTKey123456789012345678901234567890",
            DATABASE_URL="postgresql+psycopg://db_user:SuperSecretDBPass123!@postgres.internal:5432/medigen_ai",
            OPENAI_API_KEY="sk-proj-supersecretkey",
            AWS_SECRET_ACCESS_KEY="aws_secret_key_12345",
        )
        dumped = s.safe_dump()

        assert dumped["JWT_SECRET_KEY"] == "[REDACTED]"
        assert dumped["OPENAI_API_KEY"] == "[REDACTED]"
        assert dumped["AWS_SECRET_ACCESS_KEY"] == "[REDACTED]"
        assert "SuperSecretDBPass123!" not in str(dumped)
        assert dumped["DATABASE_URL"] == "postgresql+psycopg://db_user:[REDACTED]@postgres.internal:5432/medigen_ai"
        assert dumped["ENVIRONMENT"] == "development"


# ===========================================================================
# 4. ASGI Lifespan & Graceful Shutdown
# ===========================================================================


class TestASGILifespanLifecycle:
    """Tests startup diagnostics and graceful worker drain upon application termination."""

    @pytest.mark.anyio
    async def test_lifespan_startup_and_shutdown_execution(self):
        test_app = FastAPI(lifespan=lifespan)
        mock_provider = MagicMock()

        with patch("app.main.get_background_task_provider", return_value=mock_provider):
            async with lifespan(test_app):
                # Application is running
                assert test_app.title == "FastAPI"

            # After exit, shutdown must be called
            mock_provider.shutdown.assert_called_once_with(wait=True)


# ===========================================================================
# 5. Container & Deployment Configuration Validation
# ===========================================================================


class TestContainerDeploymentSupport:
    """Tests Dockerfile, .dockerignore, and compose specification for security compliance."""

    def test_dockerfile_exists_and_uses_non_root_user(self):
        root_dir = Path(__file__).resolve().parent.parent.parent
        dockerfile_path = root_dir / "Dockerfile"
        assert dockerfile_path.exists(), "Dockerfile must exist in project root"

        content = dockerfile_path.read_text(encoding="utf-8")
        assert "USER appuser" in content or "10001" in content
        assert "HEALTHCHECK" in content
        assert "EXPOSE 8000" in content

    def test_dockerignore_exists_and_ignores_sensitive_patterns(self):
        root_dir = Path(__file__).resolve().parent.parent.parent
        dockerignore_path = root_dir / ".dockerignore"
        assert dockerignore_path.exists(), ".dockerignore must exist in project root"

        content = dockerignore_path.read_text(encoding="utf-8")
        assert ".env" in content
        assert ".git" in content
        assert "data/" in content or "vector_db" in content

    def test_docker_compose_prod_exists_and_defines_healthchecks(self):
        root_dir = Path(__file__).resolve().parent.parent.parent
        compose_path = root_dir / "docker-compose.prod.yml"
        assert compose_path.exists(), "docker-compose.prod.yml must exist in project root"

        content = compose_path.read_text(encoding="utf-8")
        assert "postgres" in content
        assert "api" in content
        assert "healthcheck" in content
        assert "depends_on" in content


# ===========================================================================
# 6. Background Task Worker Concurrency & Scalability
# ===========================================================================


class TestBackgroundTaskWorkerScalability:
    """Tests background worker concurrency settings and throughput behavior."""

    def test_worker_concurrency_setting(self):
        custom_settings = Settings(BACKGROUND_TASK_WORKERS=8)
        assert custom_settings.BACKGROUND_TASK_WORKERS == 8

        provider = LocalBackgroundTaskProvider(max_workers=custom_settings.BACKGROUND_TASK_WORKERS)
        metrics = provider.get_metrics()
        assert metrics["max_workers"] == 8
        provider.shutdown(wait=True)
