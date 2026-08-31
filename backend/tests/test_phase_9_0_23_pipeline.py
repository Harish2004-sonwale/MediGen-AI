"""Comprehensive Test Suite for Phase 9.0.23:
Event Pipeline Integration, Concurrency, Patient Compartment Bulk FHIR Export, Celery Beat & Retention.
"""

from datetime import datetime, timedelta, timezone
import json
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import app
from app.models.care_plan import CarePlan
from app.models.encounter import Encounter
from app.models.fhir_subscription import FHIRSubscription
from app.models.handoff import ClinicalHandoff
from app.models.order import DiagnosticResult
from app.models.outbox import OutboxEvent
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.care_plan import CarePlanCategory, CarePlanCreate, CarePlanUpdate
from app.schemas.handoff import HandoffCreate, HandoffFramework, HandoffType, HandoffUpdate, IllnessSeverity
from app.schemas.patient import Gender
from app.services import care_plan_service, handoff_service, outbox_service
from app.services.bulk_export_service import execute_bulk_export_sync, init_bulk_export_job
from app.schemas.bulk_export import BulkExportRequest
from app.tasks.outbox_tasks import process_outbox_events_sync
from app.worker import celery_app


def test_care_plan_optimistic_concurrency(db_session: Session, test_doctor_user: User, test_patient: Patient):
    """Verify care plan optimistic locking checks version and returns HTTP 409 on version conflict."""
    # 1. Create a care plan
    plan_create = CarePlanCreate(
        title="Hypertension Protocol Phase 9.0.23",
        category=CarePlanCategory.CHRONIC_DISEASE_MANAGEMENT,
        description="Daily BP tracking and lisinopril titration.",
    )
    plan_res = care_plan_service.create_care_plan(db_session, test_patient.patient_id, plan_create, test_doctor_user)
    assert plan_res.version == 1

    # 2. Update with matching version token (version=1 -> version=2)
    update_1 = CarePlanUpdate(
        title="Hypertension Protocol Phase 9.0.23 (Updated)",
        version=1,
    )
    res_1 = care_plan_service.update_care_plan(db_session, plan_res.plan_id, update_1, test_doctor_user)
    assert res_1.version == 2
    assert res_1.title == "Hypertension Protocol Phase 9.0.23 (Updated)"

    # 3. Concurrent stale update with version=1 must raise HTTP 409 Conflict
    stale_update = CarePlanUpdate(
        title="Stale Update Overwrite Attempt",
        version=1,
    )
    with pytest.raises(HTTPException) as exc_info:
        care_plan_service.update_care_plan(db_session, plan_res.plan_id, stale_update, test_doctor_user)
    assert exc_info.value.status_code == 409
    assert "Conflict" in exc_info.value.detail

    # 4. Valid update with current version=2 succeeds -> version=3
    valid_update = CarePlanUpdate(
        title="Hypertension Protocol Phase 9.0.23 (Final)",
        version=2,
    )
    res_2 = care_plan_service.update_care_plan(db_session, plan_res.plan_id, valid_update, test_doctor_user)
    assert res_2.version == 3


def test_handoff_optimistic_concurrency(db_session: Session, test_doctor_user: User, test_patient: Patient):
    """Verify clinical handoff optimistic locking checks version and returns HTTP 409 on conflict."""
    # 1. Create handoff
    h_create = HandoffCreate(
        framework=HandoffFramework.IPASS,
        handoff_type=HandoffType.SHIFT_CHANGE,
        illness_severity=IllnessSeverity.STABLE,
        summary="Patient stable post-op overnight monitoring.",
    )
    h_res = handoff_service.create_handoff(db_session, test_patient.patient_id, h_create, test_doctor_user)
    assert h_res.version == 1

    # 2. First update with version=1 -> succeeds to version=2
    update_1 = HandoffUpdate(
        summary="Patient stable, scheduled for physical therapy.",
        version=1,
    )
    res_1 = handoff_service.update_handoff(db_session, h_res.handoff_id, update_1, test_doctor_user)
    assert res_1.version == 2

    # 3. Concurrent stale update with version=1 -> raises HTTP 409 Conflict
    stale_update = HandoffUpdate(
        summary="Stale shift handover overwrite.",
        version=1,
    )
    with pytest.raises(HTTPException) as exc_info:
        handoff_service.update_handoff(db_session, h_res.handoff_id, stale_update, test_doctor_user)
    assert exc_info.value.status_code == 409
    assert "Conflict" in exc_info.value.detail

    # 4. Update with correct version=2 succeeds -> version=3
    valid_update = HandoffUpdate(
        summary="Patient ready for afternoon discharge evaluation.",
        version=2,
    )
    res_2 = handoff_service.update_handoff(db_session, h_res.handoff_id, valid_update, test_doctor_user)
    assert res_2.version == 3


def test_bulk_export_patient_compartment_completeness(db_session: Session, test_doctor_user: User, test_patient: Patient):
    """Verify Bulk FHIR Export streams Patient, Encounter, CarePlan, Observation, and DiagnosticReport NDJSONs."""
    # Create associated clinical resources
    enc = Encounter(
        encounter_id="ENC-P23-001",
        patient_id=test_patient.patient_id,
        facility_id="FAC-001",
        chief_complaint="Cough and fever",
        assessment="Acute bronchitis",
        clinical_notes="Patient presented with cough and fever.",
    )
    db_session.add(enc)

    from app.models.order import ClinicalOrder
    order = ClinicalOrder(
        order_id="ORD-P23-001",
        patient_id=test_patient.id,
        order_category="laboratory",
        order_type="comprehensive_metabolic_panel",
        clinical_indication="Routine renal monitoring",
        status="completed",
        facility_id="FAC-001",
    )
    db_session.add(order)
    db_session.flush()

    diag = DiagnosticResult(
        result_id="RES-P23-001",
        order_id=order.id,
        patient_id=test_patient.id,
        test_name="Serum Creatinine",
        numeric_value=1.1,
        unit_of_measure="mg/dL",
        findings_summary="Normal renal function.",
        status="final",
    )
    db_session.add(diag)
    db_session.commit()

    # Initialize and execute bulk export
    req = BulkExportRequest(export_type="patient")
    job = init_bulk_export_job(db_session, test_doctor_user.id, req, facility_id="FAC-001")
    completed_job = execute_bulk_export_sync(db_session, job.job_id)

    assert completed_job is not None
    assert completed_job.status == "COMPLETED"
    output_types = [item["type"] for item in completed_job.output_urls_json]
    assert "Patient" in output_types
    assert "Encounter" in output_types
    assert "CarePlan" in output_types
    assert "Observation" in output_types
    assert "DiagnosticReport" in output_types


def test_outbox_subscription_fanout(db_session: Session):
    """Verify outbox dispatcher successfully executes matching active FHIR subscription deliveries."""
    # Register an active subscription
    sub = FHIRSubscription(
        subscription_id=f"SUB-TEST-{datetime.now(timezone.utc).timestamp()}",
        facility_id="FAC-001",
        topic="clinical-alert-triggered",
        criteria="ClinicalAlert?severity=critical",
        channel_type="WEBSOCKET",
        status="ACTIVE",
    )
    db_session.add(sub)

    # Record matching domain event in transactional outbox
    event = outbox_service.record_outbox_event(
        db=db_session,
        event_type="clinical-alert-triggered",
        aggregate_type="ClinicalAlert",
        aggregate_id="ALT-9001",
        payload={"alert_id": "ALT-9001", "severity": "critical", "message": "High HR detected"},
        facility_id="FAC-001",
    )
    db_session.commit()

    # Run synchronous dispatcher
    metrics = process_outbox_events_sync(batch_size=10)
    assert metrics["processed"] >= 1

    # Event status should now be PUBLISHED
    db_session.refresh(event)
    assert event.status == "PUBLISHED"
    assert event.published_at is not None


def test_celery_beat_schedule_registration():
    """Verify Celery Beat periodic schedules are registered for outbox, alert escalation, and retention."""
    if celery_app is None:
        pytest.skip("Celery not installed or in standalone mode")

    schedule = celery_app.conf.beat_schedule
    assert "outbox-dispatcher-every-5s" in schedule
    assert schedule["outbox-dispatcher-every-5s"]["schedule"] == 5.0

    assert "alert-escalation-every-60s" in schedule
    assert schedule["alert-escalation-every-60s"]["schedule"] == 60.0

    assert "outbox-retention-daily" in schedule
    assert schedule["outbox-retention-daily"]["schedule"] == 86400.0


def test_outbox_retention_prune_safety(db_session: Session):
    """Verify prune_published_outbox_events safely deletes old PUBLISHED records and preserves others."""
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=45)

    # 1. Old PUBLISHED event -> should be pruned
    evt_old_pub = OutboxEvent(
        event_id=f"EVT-OLD-PUB-{now.timestamp()}",
        event_type="test-event",
        aggregate_type="Test",
        aggregate_id="1",
        payload_json={"test": True},
        status="PUBLISHED",
        published_at=old_time,
        created_at=old_time,
    )
    # 2. Recent PUBLISHED event -> should NOT be pruned
    evt_new_pub = OutboxEvent(
        event_id=f"EVT-NEW-PUB-{now.timestamp()}",
        event_type="test-event",
        aggregate_type="Test",
        aggregate_id="2",
        payload_json={"test": True},
        status="PUBLISHED",
        published_at=now,
        created_at=now,
    )
    # 3. Old PENDING event -> should NOT be pruned
    evt_old_pend = OutboxEvent(
        event_id=f"EVT-OLD-PEND-{now.timestamp()}",
        event_type="test-event",
        aggregate_type="Test",
        aggregate_id="3",
        payload_json={"test": True},
        status="PENDING",
        created_at=old_time,
    )
    # 4. Old DEAD_LETTER event -> should NOT be pruned
    evt_old_dlq = OutboxEvent(
        event_id=f"EVT-OLD-DLQ-{now.timestamp()}",
        event_type="test-event",
        aggregate_type="Test",
        aggregate_id="4",
        payload_json={"test": True},
        status="DEAD_LETTER",
        created_at=old_time,
    )
    db_session.add_all([evt_old_pub, evt_new_pub, evt_old_pend, evt_old_dlq])
    db_session.commit()

    # Execute pruning with 30 day retention
    res = outbox_service.prune_published_outbox_events(db_session, retention_days=30)
    assert res["deleted"] >= 1

    # Verify old published was pruned
    pruned_check = db_session.query(OutboxEvent).filter(OutboxEvent.event_id == evt_old_pub.event_id).first()
    assert pruned_check is None

    # Verify recent published, old pending, and dead-letter remain intact
    assert db_session.query(OutboxEvent).filter(OutboxEvent.event_id == evt_new_pub.event_id).first() is not None
    assert db_session.query(OutboxEvent).filter(OutboxEvent.event_id == evt_old_pend.event_id).first() is not None
    assert db_session.query(OutboxEvent).filter(OutboxEvent.event_id == evt_old_dlq.event_id).first() is not None


def test_outbox_prune_api_endpoint(client: TestClient, test_admin: User, db_session: Session):
    """Verify POST /api/v1/outbox/prune endpoint executes retention pruning for admin."""
    from app.core.security import create_access_token
    token = create_access_token(subject=test_admin.id, role=test_admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    old_time = datetime.now(timezone.utc) - timedelta(days=60)
    evt = OutboxEvent(
        event_id=f"EVT-PRUNE-API-{datetime.now(timezone.utc).timestamp()}",
        event_type="test-prune-api",
        aggregate_type="Test",
        aggregate_id="999",
        payload_json={"api": True},
        status="PUBLISHED",
        published_at=old_time,
        created_at=old_time,
    )
    db_session.add(evt)
    db_session.commit()

    resp = client.post("/api/v1/outbox/prune?retention_days=30", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "deleted" in data
    assert data["deleted"] >= 1
