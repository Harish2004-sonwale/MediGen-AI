import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database.connection import SessionLocal
from app.main import app


@pytest.mark.integration
def test_live_postgres_connection():
    """Environment-aware integration test verifying live PostgreSQL connectivity when configured."""
    if not os.getenv("RUN_DB_INTEGRATION_TESTS"):
        pytest.skip(
            "Live PostgreSQL integration tests skipped (set RUN_DB_INTEGRATION_TESTS=1 to run)"
        )

    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        db.close()


@pytest.mark.integration
def test_health_check_db_live_endpoint():
    """Environment-aware integration test verifying live GET /health/db endpoint against live PostgreSQL."""
    if not os.getenv("RUN_DB_INTEGRATION_TESTS"):
        pytest.skip(
            "Live PostgreSQL integration tests skipped (set RUN_DB_INTEGRATION_TESTS=1 to run)"
        )

    with TestClient(app) as client:
        response = client.get("/health/db")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
