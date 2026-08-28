from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app

# In-memory SQLite engine for deterministic unit testing without requiring live PostgreSQL
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine
)


def override_get_db_success():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_health_check_db_success():
    """Verify GET /health/db returns 200 OK and healthy status when query succeeds."""
    app.dependency_overrides[get_db] = override_get_db_success
    with TestClient(app) as client:
        response = client.get("/health/db")
        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "database": "connected",
        }
    app.dependency_overrides.clear()


def test_health_check_db_sqlalchemy_error():
    """Verify GET /health/db returns 503 and safe error message when query execution fails."""
    mock_session = MagicMock()
    mock_session.execute.side_effect = OperationalError(
        "Connection refused", params=None, orig=Exception("Could not connect")
    )

    def override_get_db_error():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db_error
    with TestClient(app) as client:
        response = client.get("/health/db")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert data["detail"] == "Database is unreachable or query execution failed"
    app.dependency_overrides.clear()


def test_health_check_db_general_exception():
    """Verify GET /health/db returns 503 and does not expose sensitive details on unexpected errors."""
    mock_session = MagicMock()
    mock_session.execute.side_effect = Exception("Unexpected connection error")

    def override_get_db_general_error():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db_general_error
    with TestClient(app) as client:
        response = client.get("/health/db")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert data["detail"] == "Database is unreachable or query execution failed"
    app.dependency_overrides.clear()
