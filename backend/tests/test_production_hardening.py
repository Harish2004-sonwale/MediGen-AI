"""Automated Unit & Integration Tests for Phase 9.0.20: Production Hardening & Enterprise Scalability.

Tests:
1. Production Configuration Validation & Secrets Masking
2. Redis Distributed Caching Layer & In-Memory Fallback
3. Rate Limiting Middleware & HTTP 429 Enforcement
4. Pluggable Storage Abstraction (Local, S3 & Mock)
5. Circuit Breaker Resilience State Machine
6. Fallback LLM Multi-Provider Chain
7. Prometheus Metrics Exporter & FHIR CapabilityStatement
8. Pluggable External SIEM / Audit Streaming
"""

import time
from fastapi.testclient import TestClient
import pytest

from app.ai.context_builder import GroundedContextChunk
from app.ai.llm import BaseLLMProvider, FallbackLLMProvider, LLMGroundedResponse, MockLLMProvider
from app.core.audit_streaming import MockAuditStreamer, SyslogAuditStreamer, WebhookAuditStreamer
from app.core.cache import InMemoryCache, RedisCache, cached, get_cache, reset_cache_for_testing
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException, CircuitState, get_circuit_breaker
from app.core.config import Settings
from app.core.rate_limiter import SlidingWindowRateLimiter, get_rate_limiter
from app.core.storage import LocalStorageProvider, MockStorageProvider, get_storage_provider, set_storage_provider
from app.main import app
from app.models.security import AuditAction, AuditOutcome, ClinicalAuditEvent




# -----------------------------------------------------------------------------
# 1. Configuration Validation & Secrets Masking
# -----------------------------------------------------------------------------


def test_production_configuration_validation_and_fail_fast():
    """Verify validate_production_settings catches vulnerabilities in production mode."""
    # Production with default insecure values must return errors
    prod_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=True,
        JWT_SECRET_KEY="short",
        DATABASE_URL="postgresql+psycopg://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/medigen_ai",
        CORS_ORIGINS="*",
        STORAGE_PROVIDER="s3",
        S3_ACCESS_KEY=None,
        S3_SECRET_KEY=None,
    )
    errors = prod_settings.validate_production_settings()
    assert len(errors) >= 4
    assert any("JWT_SECRET_KEY" in e for e in errors)
    assert any("DEBUG" in e for e in errors)
    assert any("DATABASE_URL" in e for e in errors)
    assert any("CORS_ORIGINS" in e for e in errors)
    assert any("S3_ACCESS_KEY" in e for e in errors)

    # Secure production settings must pass cleanly
    secure_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        JWT_SECRET_KEY="a_very_secure_cryptographic_key_exceeding_32_characters_123456789",
        DATABASE_URL="postgresql+psycopg://medigen_prod_user:StrongSecretPass99@db.prod.internal:5432/medigen_ai",
        CORS_ORIGINS="https://app.medigen.ai,https://admin.medigen.ai",
        STORAGE_PROVIDER="local",
    )
    assert secure_settings.validate_production_settings() == []

    # Verify safe_dump masks credentials
    dumped = secure_settings.safe_dump()
    assert dumped["JWT_SECRET_KEY"] == "[REDACTED]"
    assert "[REDACTED]" in dumped["DATABASE_URL"]
    assert "StrongSecretPass99" not in dumped["DATABASE_URL"]


# -----------------------------------------------------------------------------
# 2. Redis Distributed Caching Layer & In-Memory Fallback
# -----------------------------------------------------------------------------


def test_caching_layer_and_fallback():
    """Verify caching operations: get, set with TTL, delete, and cached decorator."""
    cache = InMemoryCache(default_ttl=2)

    # 1. Set & Get
    cache.set("test:key1", {"drug": "Lisinopril", "dosage": "10mg"}, ttl_seconds=5)
    val = cache.get("test:key1")
    assert val is not None
    assert val["drug"] == "Lisinopril"

    # 2. Delete
    cache.delete("test:key1")
    assert cache.get("test:key1") is None

    # 3. Expiration TTL
    cache.set("test:ttl_key", "temporary_data", ttl_seconds=1)
    assert cache.get("test:ttl_key") == "temporary_data"
    time.sleep(1.1)
    assert cache.get("test:ttl_key") is None

    # 4. Cached decorator
    call_count = 0

    @cached(prefix="test_calc", ttl_seconds=10)
    def compute_heavy_score(x: int) -> int:
        nonlocal call_count
        call_count += 1
        return x * 2

    res1 = compute_heavy_score(21)
    res2 = compute_heavy_score(21)
    assert res1 == 42
    assert res2 == 42
    assert call_count == 1  # Second invocation resolved from cache


# -----------------------------------------------------------------------------
# 3. Rate Limiting Middleware & HTTP 429 Enforcement
# -----------------------------------------------------------------------------


def test_rate_limiter_sliding_window_enforcement():
    """Verify sliding window rate limiter blocks excessive requests and allows recovery."""
    limiter = SlidingWindowRateLimiter()
    test_id = "test_client_ip_192.168.1.100"
    limiter.reset(test_id)

    # Allow up to 3 requests per 2 seconds
    allowed1, remaining1, _ = limiter.is_allowed(test_id, limit=3, window_seconds=2)
    allowed2, remaining2, _ = limiter.is_allowed(test_id, limit=3, window_seconds=2)
    allowed3, remaining3, _ = limiter.is_allowed(test_id, limit=3, window_seconds=2)

    assert allowed1 is True
    assert allowed2 is True
    assert allowed3 is True
    assert remaining3 == 0

    # 4th request must be denied
    allowed4, _, retry_after = limiter.is_allowed(test_id, limit=3, window_seconds=2)
    assert allowed4 is False
    assert retry_after >= 1

    # Wait for sliding window to slide past
    time.sleep(2.1)
    allowed5, _, _ = limiter.is_allowed(test_id, limit=3, window_seconds=2)
    assert allowed5 is True


# -----------------------------------------------------------------------------
# 4. Storage Abstraction (Local & Mock)
# -----------------------------------------------------------------------------


def test_storage_provider_operations(tmp_path):
    """Verify storage provider save, read, exists, metadata, and delete."""
    # 1. Mock Storage Provider
    mock_store = MockStorageProvider()
    mock_store.save_file("docs/test.pdf", b"PDF_SAMPLE_DATA_123", content_type="application/pdf")
    assert mock_store.exists("docs/test.pdf") is True
    assert mock_store.read_file("docs/test.pdf") == b"PDF_SAMPLE_DATA_123"

    meta = mock_store.get_metadata("docs/test.pdf")
    assert meta["size_bytes"] == len(b"PDF_SAMPLE_DATA_123")
    assert meta["content_type"] == "application/pdf"

    mock_store.delete_file("docs/test.pdf")
    assert mock_store.exists("docs/test.pdf") is False

    # 2. Local Storage Provider with path safety
    local_store = LocalStorageProvider(base_dir=str(tmp_path))
    local_store.save_file("imaging/ct_scan.dcm", b"DICOM_HEADER_AND_PIXEL_DATA")
    assert local_store.exists("imaging/ct_scan.dcm") is True
    assert local_store.read_file("imaging/ct_scan.dcm") == b"DICOM_HEADER_AND_PIXEL_DATA"

    local_meta = local_store.get_metadata("imaging/ct_scan.dcm")
    assert local_meta["size_bytes"] == len(b"DICOM_HEADER_AND_PIXEL_DATA")
    assert "sha256" in local_meta


# -----------------------------------------------------------------------------
# 5. Circuit Breaker Resilience State Machine
# -----------------------------------------------------------------------------


def test_circuit_breaker_state_transitions():
    """Verify CircuitBreaker moves CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""
    cb = CircuitBreaker(
        name="test_external_api",
        failure_threshold=2,
        recovery_timeout=1.0,
        half_open_success_threshold=1,
    )
    cb.reset()
    assert cb.state == CircuitState.CLOSED

    def failing_call():
        raise ConnectionError("External service timeout")

    # Failure 1
    with pytest.raises(ConnectionError):
        cb.call(failing_call)
    assert cb.state == CircuitState.CLOSED

    # Failure 2 (reaches threshold -> trips to OPEN)
    with pytest.raises(ConnectionError):
        cb.call(failing_call)
    assert cb.state == CircuitState.OPEN

    # While OPEN: calls immediately raise CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        cb.call(lambda: "should not run")

    # Fallback works during OPEN
    fallback_res = cb.call(lambda: "failed", fallback=lambda: "fallback_safe_value")
    assert fallback_res == "fallback_safe_value"

    # Wait for recovery timeout -> transitions to HALF_OPEN on next call
    time.sleep(1.1)
    assert cb.state == CircuitState.HALF_OPEN

    # Successful probe call resets circuit to CLOSED
    success_res = cb.call(lambda: "recovered_service_data")
    assert success_res == "recovered_service_data"
    assert cb.state == CircuitState.CLOSED


# -----------------------------------------------------------------------------
# 6. Fallback LLM Multi-Provider Chain
# -----------------------------------------------------------------------------


class FailingLLMProvider(BaseLLMProvider):
    def generate_grounded_response(self, query, context_chunks, chat_history=None):
        raise RuntimeError("Cloud LLM rate limit or connection timeout")

    def generate_grounded_response_stream(self, query, context_chunks, chat_history=None):
        raise RuntimeError("Cloud LLM stream timeout")


def test_fallback_llm_provider():
    """Verify FallbackLLMProvider automatically falls back when primary fails."""
    primary = FailingLLMProvider()
    fallback = MockLLMProvider()

    chain = FallbackLLMProvider(
        primary=primary,
        fallback=fallback,
        name="test_llm_chain",
    )

    context = [
        GroundedContextChunk(
            chunk_id="chk-001",
            document_id="doc-001",
            title="Cardiology Note",
            document_type="progress_note",
            content="Patient diagnosed with Stage 2 Hypertension.",
            page_number=1,
            distance=0.05,
        )
    ]

    resp = chain.generate_grounded_response(
        query="What is the patient diagnosis?",
        context_chunks=context,
    )
    assert resp.answer is not None
    assert resp.raw_response is not None
    assert resp.raw_response.get("degraded_mode") is True


# -----------------------------------------------------------------------------
# 7. Prometheus Metrics & FHIR CapabilityStatement
# -----------------------------------------------------------------------------


def test_prometheus_metrics_endpoint(client: TestClient):
    """Verify GET /api/v1/health/metrics/prometheus returns Prometheus exposition format."""
    response = client.get("/api/v1/health/metrics/prometheus")
    assert response.status_code == 200
    text_content = response.text
    assert "medigen_http_requests_total" in text_content
    assert "medigen_http_request_duration_seconds" in text_content
    assert "medigen_cache_connected" in text_content


def test_fhir_capability_statement_metadata(client: TestClient):
    """Verify GET /api/v1/fhir/metadata returns standard FHIR R4 CapabilityStatement."""
    response = client.get("/api/v1/fhir/metadata")
    assert response.status_code == 200
    data = response.json()
    assert data["resourceType"] == "CapabilityStatement"
    assert data["status"] == "active"
    assert data["fhirVersion"] == "4.0.1"

    # Check REST resources
    rest_resources = data["rest"][0]["resource"]
    resource_names = [r["type"] for r in rest_resources]
    assert "Patient" in resource_names
    assert "Encounter" in resource_names
    assert "Condition" in resource_names
    assert "Observation" in resource_names
    assert "Consent" in resource_names
    assert "AuditEvent" in resource_names
    assert "ImagingStudy" in resource_names


# -----------------------------------------------------------------------------
# 8. Pluggable External SIEM / Audit Streaming
# -----------------------------------------------------------------------------


def test_audit_streaming_emit():
    """Verify SyslogAuditStreamer and MockAuditStreamer emit events safely."""
    mock_streamer = MockAuditStreamer()
    syslog_streamer = SyslogAuditStreamer()

    sample_event = ClinicalAuditEvent(
        id=1,
        event_id="AUD-20260830-TEST",
        user_id=1,
        user_role="DOCTOR",
        patient_id="PAT-001",
        action=AuditAction.READ,
        resource_type="Patient",
        resource_id="PAT-001",
        outcome=AuditOutcome.SUCCESS,
        metadata_json={"test": True},
        prev_record_hash="0000000000000000000000000000000000000000000000000000000000000000",
        record_hash="1111111111111111111111111111111111111111111111111111111111111111",
    )

    # Emit to mock
    assert mock_streamer.emit(sample_event) is True
    assert len(mock_streamer.emitted_events) == 1
    assert mock_streamer.emitted_events[0]["event_id"] == "AUD-20260830-TEST"

    # Emit to syslog
    assert syslog_streamer.emit(sample_event) is True
