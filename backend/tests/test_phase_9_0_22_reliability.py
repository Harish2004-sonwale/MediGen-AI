"""Comprehensive Test Suite for Phase 9.0.22 Enterprise Reliability, Concurrency, Interoperability and Security."""

import json
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.allergy_cross_reactivity_provider import get_allergy_cross_reactivity_provider
from app.core.idempotency import compute_request_hash
from app.models.alert import ClinicalAlert
from app.models.idempotency import IdempotencyRecord
from app.models.order import ClinicalOrder
from app.models.outbox import OutboxEvent
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.alert import AlertSeverity, AlertStatus
from app.services.alert_escalation_service import scan_and_escalate_unacknowledged_alerts
from app.services.mfa_service import (
    _generate_totp_code,
    disable_mfa,
    enable_mfa,
    get_mfa_status,
    setup_mfa,
    verify_mfa_code,
)
from app.services.outbox_service import (
    fetch_pending_outbox_events,
    get_outbox_metrics,
    mark_outbox_event_failed,
    mark_outbox_event_published,
    record_outbox_event,
    replay_dead_letter_events,
)


@pytest.fixture
def auth_headers(test_admin: User) -> dict[str, str]:
    from app.core.security import create_access_token
    token = create_access_token(subject=test_admin.id, role=test_admin.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_transactional_outbox_service_and_dlq_lifecycle(db_session: Session) -> None:
    """Test outbox event recording, publishing, exponential backoff failure, and DLQ replay."""
    # 1. Record event
    event = record_outbox_event(
        db=db_session,
        event_type="TEST_EVENT",
        aggregate_type="PATIENT",
        aggregate_id="PAT-999",
        payload={"note": "Test outbox event payload"},
        facility_id="FAC-001",
        max_attempts=3,
    )
    db_session.commit()
    assert event.status == "PENDING"
    assert event.attempts == 0

    # 2. Fetch pending
    pending = fetch_pending_outbox_events(db_session)
    assert any(e.event_id == event.event_id for e in pending)

    # 3. Simulate failure 1
    mark_outbox_event_failed(db_session, event.event_id, error_message="Network timeout")
    db_session.refresh(event)
    assert event.status == "FAILED"
    assert event.attempts == 1
    assert event.retry_after is not None

    # 4. Simulate failure 2 & 3 (reaching max_attempts -> DEAD_LETTER)
    mark_outbox_event_failed(db_session, event.event_id, error_message="Network timeout 2")
    mark_outbox_event_failed(db_session, event.event_id, error_message="Network timeout 3")
    db_session.refresh(event)
    assert event.status == "DEAD_LETTER"
    assert event.attempts == 3

    # 5. Replay DLQ
    replayed_count = replay_dead_letter_events(db_session, event_ids=[event.event_id])
    assert replayed_count == 1
    db_session.refresh(event)
    assert event.status == "PENDING"
    assert event.attempts == 0

    # 6. Mark published
    mark_outbox_event_published(db_session, event.event_id)
    db_session.refresh(event)
    assert event.status == "PUBLISHED"
    assert event.published_at is not None

    # 7. Metrics
    metrics = get_outbox_metrics(db_session)
    assert metrics["total"] >= 1
    assert metrics["published"] >= 1


def test_idempotency_and_cpoe_duplicate_protection(client: TestClient, db_session: Session, auth_headers: dict) -> None:
    """Test CPOE request deduplication with X-Idempotency-Key and payload hash verification."""
    # Create patient
    p_resp = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Idempotent",
            "last_name": "Patient",
            "date_of_birth": "1980-05-15",
            "gender": "male",
        },
        headers=auth_headers,
    )
    assert p_resp.status_code == 201
    patient_id = p_resp.json()["patient_id"]

    idempotency_key = "IDEM-KEY-2026-ALPHA-01"
    headers_with_idempotency = {**auth_headers, "X-Idempotency-Key": idempotency_key}

    order_payload = {
        "order_category": "laboratory",
        "order_type": "complete_blood_count",
        "priority": "routine",
        "clinical_indication": "Annual physical baseline evaluation",
    }

    # First call: executes mutation and stores response
    res1 = client.post(
        f"/api/v1/patients/{patient_id}/orders",
        json=order_payload,
        headers=headers_with_idempotency,
    )
    assert res1.status_code == 201
    order1 = res1.json()
    assert order1["order_type"] == "complete_blood_count"

    # Second call with identical idempotency key: should return cached response with IDEMPOTENT-HIT
    res2 = client.post(
        f"/api/v1/patients/{patient_id}/orders",
        json=order_payload,
        headers=headers_with_idempotency,
    )
    assert res2.status_code == 201
    assert res2.headers.get("X-Cache-Lookup") == "IDEMPOTENT-HIT"
    assert res2.json()["order_id"] == order1["order_id"]

    # Third call with SAME key but DIFFERENT payload: must raise 422 Unprocessable Entity
    different_payload = {
        "order_category": "imaging",
        "order_type": "chest_xray_pa",
        "priority": "stat",
        "clinical_indication": "Acute dyspnea",
    }
    res3 = client.post(
        f"/api/v1/patients/{patient_id}/orders",
        json=different_payload,
        headers=headers_with_idempotency,
    )
    assert res3.status_code == 422
    assert "previously used with a different request payload" in res3.json()["detail"]


def test_optimistic_locking_concurrency_conflict(client: TestClient, db_session: Session, auth_headers: dict) -> None:
    """Test optimistic concurrency control detecting concurrent order edits and raising HTTP 409."""
    # Create patient
    p_resp = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Locking",
            "last_name": "Tester",
            "date_of_birth": "1975-08-20",
            "gender": "female",
        },
        headers=auth_headers,
    )
    patient_id = p_resp.json()["patient_id"]

    # Create order
    ord_resp = client.post(
        f"/api/v1/patients/{patient_id}/orders",
        json={
            "order_category": "laboratory",
            "order_type": "basic_metabolic_panel",
            "priority": "routine",
            "clinical_indication": "Electrolyte check",
        },
        headers=auth_headers,
    )
    assert ord_resp.status_code == 201
    order_data = ord_resp.json()
    order_id = order_data["order_id"]
    assert order_data["version"] == 1

    # First update: provides version=1 -> succeeds and increments to version=2
    upd1 = client.patch(
        f"/api/v1/orders/{order_id}",
        json={"priority": "urgent", "version": 1},
        headers=auth_headers,
    )
    assert upd1.status_code == 200
    assert upd1.json()["version"] == 2
    assert upd1.json()["priority"] == "urgent"

    # Concurrent stale update: provides stale version=1 -> fails with HTTP 409 Conflict
    upd_stale = client.patch(
        f"/api/v1/orders/{order_id}",
        json={"clinical_indication": "Stale concurrent update attempt", "version": 1},
        headers=auth_headers,
    )
    assert upd_stale.status_code == 409
    assert "Conflict: Clinical order" in upd_stale.json()["detail"]


def test_allergy_class_cross_reactivity_matrix() -> None:
    """Verify pharmacological allergy cross-reactivity warnings."""
    provider = get_allergy_cross_reactivity_provider()

    # Case 1: Penicillin allergy ordering 1st-gen cephalosporin (Cefazolin) -> MODERATE warning
    warnings = provider.evaluate_allergy_cross_reactivity(
        ordered_medication="Cefazolin 1g IV",
        patient_allergies=[{"substance": "Amoxicillin", "severity": "severe"}],
    )
    assert len(warnings) >= 1
    assert warnings[0]["severity"] == "MODERATE"
    assert "Beta-Lactam" in warnings[0]["allergy_class"]

    # Case 2: Aspirin allergy ordering Ibuprofen -> HIGH warning
    nsaid_warnings = provider.evaluate_allergy_cross_reactivity(
        ordered_medication="Ibuprofen 600mg PO",
        patient_allergies=[{"substance": "Aspirin"}],
    )
    assert len(nsaid_warnings) >= 1
    assert nsaid_warnings[0]["severity"] == "HIGH"
    assert "COX-1" in nsaid_warnings[0]["risk_mechanism"]

    # Case 3: Morphine allergy ordering Fentanyl -> LOW_ADVISORY (safe alternative)
    opioid_warnings = provider.evaluate_allergy_cross_reactivity(
        ordered_medication="Fentanyl 50mcg IV",
        patient_allergies=[{"substance": "Morphine"}],
    )
    assert len(opioid_warnings) >= 1
    assert opioid_warnings[0]["severity"] == "LOW_ADVISORY"


def test_clinical_alert_escalation_scanner(db_session: Session) -> None:
    """Test unacknowledged critical alert escalation to Tier 1 and Tier 2 with outbox events."""
    patient = Patient(
        patient_id="PAT-ESC-001",
        first_name="Escalation",
        last_name="Patient",
        date_of_birth=datetime(1960, 1, 1).date(),
        gender="male",
        facility_id="FAC-001",
    )
    db_session.add(patient)
    db_session.commit()

    # Create unacknowledged critical alert created 20 minutes ago
    past_20m = datetime.now(timezone.utc) - timedelta(minutes=20)
    alert = ClinicalAlert(
        alert_id="ALT-ESC-001",
        patient_id=patient.id,
        alert_type="CRITICAL_HYPOXIA",
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACTIVE,
        title="Critical SpO2 Desaturation 82%",
        explanation="Patient oxygen saturation below critical safety threshold.",
        escalation_level=0,
        facility_id="FAC-001",
        created_at=past_20m,
    )
    db_session.add(alert)
    db_session.commit()

    # Run escalation scanner
    escalated = scan_and_escalate_unacknowledged_alerts(db_session, tier1_threshold_minutes=15, tier2_threshold_minutes=30)
    assert len(escalated) >= 1
    db_session.refresh(alert)
    assert alert.escalation_level == 1
    assert "Tier 1 Escalation" in alert.escalation_notes


def test_mfa_totp_lifecycle_and_backup_recovery_codes(db_session: Session, client: TestClient, auth_headers: dict) -> None:
    """Test MFA setup, TOTP enablement, valid verification, backup recovery code usage, and disablement."""
    # 1. Setup MFA
    setup_resp = client.post("/api/v1/auth/mfa/setup", headers=auth_headers)
    assert setup_resp.status_code == 200
    data = setup_resp.json()
    secret = data["secret"]
    backup_codes = data["backup_codes"]
    assert len(secret) >= 16
    assert len(backup_codes) == 10

    # 2. Status should be disabled before verification
    status_resp = client.get("/api/v1/auth/mfa/status", headers=auth_headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["is_enabled"] is False

    # 3. Enable MFA using valid TOTP code
    current_code = _generate_totp_code(secret)
    enable_resp = client.post(
        "/api/v1/auth/mfa/enable",
        json={"code": current_code},
        headers=auth_headers,
    )
    assert enable_resp.status_code == 200
    assert enable_resp.json()["verified"] is True

    # 4. Status should now be enabled with 10 backup codes
    status_resp2 = client.get("/api/v1/auth/mfa/status", headers=auth_headers)
    assert status_resp2.json()["is_enabled"] is True
    assert status_resp2.json()["backup_codes_remaining"] == 10

    # 5. Verify using single-use backup recovery code
    first_backup_code = backup_codes[0]
    verify_backup = client.post(
        "/api/v1/auth/mfa/verify",
        json={"code": first_backup_code},
        headers=auth_headers,
    )
    assert verify_backup.status_code == 200
    assert "Backup recovery code accepted" in verify_backup.json()["message"]

    # 6. Check that backup code was burned (9 remaining)
    status_resp3 = client.get("/api/v1/auth/mfa/status", headers=auth_headers)
    assert status_resp3.json()["backup_codes_remaining"] == 9

    # 7. Disable MFA
    disable_resp = client.post(
        "/api/v1/auth/mfa/disable",
        json={"code": _generate_totp_code(secret)},
        headers=auth_headers,
    )
    assert disable_resp.status_code == 200
    assert disable_resp.json()["verified"] is True


def test_fhir_r4_topic_subscriptions_and_bulk_export(client: TestClient, db_session: Session, auth_headers: dict) -> None:
    """Test FHIR topic subscription registration and async Bulk Data Export ($export)."""
    # 1. Create FHIR subscription
    sub_payload = {
        "topic": "order-created",
        "criteria": "ServiceRequest?status=active",
        "channel_type": "REST_HOOK",
        "endpoint_url": "https://ehr-gateway.metrohealth.org/webhooks/orders",
        "secret_token": "mh-secret-token-2026",
    }
    sub_res = client.post("/api/v1/fhir/Subscription", json=sub_payload, headers=auth_headers)
    assert sub_res.status_code == 201
    sub_id = sub_res.json()["subscription_id"]
    assert sub_res.json()["status"] == "ACTIVE"

    # List subscriptions
    list_res = client.get("/api/v1/fhir/Subscription", headers=auth_headers)
    assert list_res.status_code == 200
    assert any(s["subscription_id"] == sub_id for s in list_res.json())

    # 2. Initiate Bulk FHIR Export ($export)
    export_res = client.post(
        "/api/v1/fhir/Patient/$export",
        headers={**auth_headers, "Prefer": "respond-async"},
    )
    assert export_res.status_code == 202
    assert "Content-Location" in export_res.headers
    job_id = export_res.json()["job_id"]

    # Poll status (synchronously completed in test env)
    status_res = client.get(f"/api/v1/fhir/bulk-export/{job_id}/status", headers=auth_headers)
    assert status_res.status_code == 200
    output_files = status_res.json()["output"]
    assert len(output_files) >= 1
    assert output_files[0]["type"] == "Patient"

    # Download NDJSON file
    dl_res = client.get(f"/api/v1/fhir/bulk-export/{job_id}/files/Patient.ndjson", headers=auth_headers)
    assert dl_res.status_code == 200
    assert dl_res.headers.get("content-type") == "application/fhir+ndjson"
