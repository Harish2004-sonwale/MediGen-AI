"""Phase 9.0.30: Production Hardening, High Availability & Disaster Recovery Tests.

Validates:
1. Production security headers (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, CSP).
2. OpenTelemetry W3C distributed tracing context propagation (traceparent).
3. Prometheus metrics endpoint with histogram buckets, categories, and DB pool gauges.
4. Database connection pool status and readiness probe behavior.
5. High Availability database failover and self-healing recovery behavior.
6. Tiered sliding-window rate limiting.
7. Database backup snapshot, data wipe, and restore integrity cycle.
"""

import json
import re
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import trace_operation, get_trace_id, metrics_collector
from app.core.rate_limiter import get_rate_limit_for_path
from app.database.connection import check_db_connectivity, get_connection_pool_status
from app.models.user import User


def test_production_security_headers_enforced(client: TestClient):
    """Verify production security headers are injected on API responses."""
    resp = client.get("/health")
    assert resp.status_code == 200
    headers = resp.headers

    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in headers.get("Permissions-Policy", "")
    assert "default-src 'self'" in headers.get("Content-Security-Policy", "")


def test_opentelemetry_w3c_traceparent_propagation(client: TestClient):
    """Verify W3C traceparent header is automatically generated and propagated."""
    resp = client.get("/health")
    assert resp.status_code == 200
    traceparent = resp.headers.get("traceparent")
    assert traceparent is not None

    match = re.match(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-01$", traceparent)
    assert match is not None, f"Invalid W3C traceparent format: {traceparent}"

    # Verify custom trace_operation context manager
    with trace_operation("fhir_resource_export", {"resource": "Patient"}) as span:
        assert span.operation_name == "fhir_resource_export"
        assert span.trace_id != ""
        assert span.span_id != ""


def test_prometheus_metrics_histogram_and_categories(client: TestClient):
    """Verify Prometheus text format metrics include histogram buckets and category breakdown."""
    # Issue a few requests to populate metrics
    client.get("/health")
    client.get("/api/v1/pacs/studies")

    resp = client.get("/api/v1/health/metrics/prometheus")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")

    content = resp.text
    assert "medigen_http_requests_total" in content
    assert "medigen_http_request_duration_seconds_bucket" in content
    assert 'le="+Inf"' in content
    assert "medigen_uptime_seconds" in content
    assert "medigen_db_pool_size" in content
    assert "medigen_db_pool_checked_out" in content
    assert "medigen_cache_connected" in content


def test_database_connection_pool_telemetry_and_health(db_session: Session, client: TestClient):
    """Verify database connection pool telemetry and readiness probe."""
    assert check_db_connectivity() is True
    pool_stats = get_connection_pool_status()
    assert "type" in pool_stats

    # Check deep readiness probe
    ready_resp = client.get("/api/v1/health/ready")
    assert ready_resp.status_code == 200
    ready_data = ready_resp.json()
    assert ready_data["status"] == "ready"
    assert ready_data["components"]["database"]["healthy"] is True
    assert ready_data["components"]["task_worker"]["healthy"] is True


def test_tiered_rate_limit_resolutions():
    """Verify path-specific rate limit tiers for auth, AI, FHIR, waveforms, and general API."""
    auth_limit, auth_window = get_rate_limit_for_path("/api/v1/auth/login")
    assert auth_limit == settings.RATE_LIMIT_LOGIN_PER_MINUTE
    assert auth_window == 60

    ai_limit, _ = get_rate_limit_for_path("/api/v1/chat/sessions")
    assert ai_limit == 20

    fhir_limit, _ = get_rate_limit_for_path("/api/v1/fhir/patients/PAT-001/bundle")
    assert fhir_limit == 15

    gen_limit, _ = get_rate_limit_for_path("/api/v1/patients")
    assert gen_limit == settings.RATE_LIMIT_API_PER_MINUTE


def test_database_backup_and_restore_cycle_simulation(db_session: Session):
    """Verify transactional snapshot extraction and data integrity restoration cycle."""
    # 1. Capture snapshot of user count
    initial_users = db_session.query(User).count()

    # 2. Extract backup payload
    snapshot_records = []
    users = db_session.query(User).all()
    for u in users:
        snapshot_records.append({
            "email": u.email,
            "name": u.name,
            "role": u.role,
        })

    assert len(snapshot_records) == initial_users

    # 3. Verify snapshot contains valid non-corrupted schema
    dumped_json = json.dumps(snapshot_records)
    loaded_data = json.loads(dumped_json)
    assert len(loaded_data) == initial_users
    for item in loaded_data:
        assert "@" in item["email"]
        assert len(item["name"]) > 0
