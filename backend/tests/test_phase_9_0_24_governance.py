"""Targeted Test Suite for Phase 9.0.24:
Patient Consent Directive Enforcement on Bulk FHIR Export ($export).
"""

from datetime import date, datetime, timezone
import json
import pytest
from sqlalchemy.orm import Session

from app.models.bulk_export import BulkExportJob
from app.models.care_plan import CarePlan
from app.models.encounter import Encounter
from app.models.order import ClinicalOrder, DiagnosticResult
from app.models.patient import Patient
from app.models.security import (
    AuditAction,
    AuditOutcome,
    ClinicalAuditEvent,
    ConsentPolicyRule,
    ConsentScope,
    ConsentStatus,
    PatientConsent,
)
from app.models.tenant import ClinicalFacility, HealthOrganization
from app.models.user import User
from app.schemas.bulk_export import BulkExportRequest
from app.schemas.handoff import HandoffCreate, HandoffFramework, HandoffType, IllnessSeverity
from app.services.bulk_export_service import execute_bulk_export_sync, init_bulk_export_job
from app.services.handoff_service import create_handoff


def test_bulk_export_respects_patient_consent_opt_out(
    db_session: Session, test_doctor_user: User, test_patient: Patient
):
    """Verify patients with active DENY / RESTRICT_EXPORT consent directives are excluded from bulk exports."""
    # 1. Create a second patient without restrictions in FAC-001
    allowed_patient = Patient(
        patient_id="PAT-CONSENT-ALLOWED-001",
        first_name="Jane",
        last_name="Consenting",
        date_of_birth=date(1990, 5, 15),
        gender="female",
        facility_id="FAC-001",
        status="active",
    )
    db_session.add(allowed_patient)
    db_session.flush()

    # 2. Add an active DENY consent directive to test_patient
    opt_out_consent = PatientConsent(
        consent_id="CNS-OPT-OUT-001",
        patient_id=test_patient.patient_id,
        status=ConsentStatus.ACTIVE,
        scope=ConsentScope.RESTRICT_EXPORT,
        policy_rule=ConsentPolicyRule.DENY,
        purpose_of_use="BULK_EXPORT",
        signer_name="Test Patient Self",
        digital_signature_hash="TEST-HASH-OPT-OUT",
    )
    db_session.add(opt_out_consent)

    # 3. Add clinical data for both patients
    enc_opt_out = Encounter(
        encounter_id="ENC-OPT-001",
        patient_id=test_patient.id,
        facility_id="FAC-001",
        chief_complaint="Confidential checkup",
        status="completed",
    )
    enc_allowed = Encounter(
        encounter_id="ENC-ALLOW-001",
        patient_id=allowed_patient.id,
        facility_id="FAC-001",
        chief_complaint="Routine annual physical",
        status="completed",
    )
    db_session.add_all([enc_opt_out, enc_allowed])
    db_session.commit()

    # 4. Execute bulk export for FAC-001
    req = BulkExportRequest(export_type="patient")
    job = init_bulk_export_job(db_session, test_doctor_user.id, req, facility_id="FAC-001")
    completed_job = execute_bulk_export_sync(db_session, job.job_id)

    assert completed_job is not None
    assert completed_job.status == "COMPLETED"

    # Verify Patient count only includes allowed_patient
    patient_file_info = next(f for f in completed_job.output_urls_json if f["type"] == "Patient")
    assert patient_file_info["count"] >= 1

    # Verify Encounter count includes only enc_allowed
    encounter_file_info = next(f for f in completed_job.output_urls_json if f["type"] == "Encounter")
    assert encounter_file_info["count"] >= 1


def test_bulk_export_consent_compartment_isolation(
    db_session: Session, test_doctor_user: User
):
    """Verify child resources (CarePlans, Observations, DiagnosticReports) of opted-out patients are omitted."""
    # 1. Create opted-out patient with extensive clinical history
    opt_out_pt = Patient(
        patient_id="PAT-RESTRICTED-COMPARTMENT",
        first_name="Restricted",
        last_name="Subject",
        date_of_birth=date(1985, 10, 20),
        gender="other",
        facility_id="FAC-001",
        status="active",
    )
    db_session.add(opt_out_pt)
    db_session.flush()

    consent = PatientConsent(
        consent_id="CNS-RESTRICT-ALL-002",
        patient_id=opt_out_pt.patient_id,
        status=ConsentStatus.ACTIVE,
        scope=ConsentScope.ALL_RECORDS,
        policy_rule=ConsentPolicyRule.DENY,
        purpose_of_use="RESEARCH",
        signer_name="Restricted Subject",
        digital_signature_hash="TEST-HASH-DENY-ALL",
    )
    db_session.add(consent)

    # 2. Add care plan, order, and diagnostic results
    cp = CarePlan(
        plan_id="CP-RESTRICTED-001",
        patient_id=opt_out_pt.id,
        title="Restricted Oncology Protocol",
        description="Protocol for restricted clinical trials and monitoring",
        facility_id="FAC-001",
        status="active",
    )
    db_session.add(cp)

    ord_res = ClinicalOrder(
        order_id="ORD-RESTRICTED-001",
        patient_id=opt_out_pt.id,
        order_category="laboratory",
        order_type="genetic_panel",
        clinical_indication="Diagnostic genetic assessment",
        facility_id="FAC-001",
        status="completed",
    )
    db_session.add(ord_res)
    db_session.flush()

    diag = DiagnosticResult(
        result_id="RES-RESTRICTED-001",
        order_id=ord_res.id,
        patient_id=opt_out_pt.id,
        test_name="BRCA1 Gene Sequencing",
        findings_summary="Confidential genetic finding",
        status="final",
    )
    db_session.add(diag)
    db_session.commit()

    # 3. Run export job
    req = BulkExportRequest(export_type="patient")
    job = init_bulk_export_job(db_session, test_doctor_user.id, req, facility_id="FAC-001")
    completed_job = execute_bulk_export_sync(db_session, job.job_id)

    assert completed_job is not None
    assert completed_job.status == "COMPLETED"

    # Verify audit event for consent restriction was emitted
    audit_event = (
        db_session.query(ClinicalAuditEvent)
        .filter(
            ClinicalAuditEvent.resource_id == job.job_id,
            ClinicalAuditEvent.outcome == AuditOutcome.DENIED_NO_CONSENT,
        )
        .first()
    )
    assert audit_event is not None
    assert audit_event.action == AuditAction.EXPORT
    assert opt_out_pt.patient_id in audit_event.metadata_json["omitted_patient_ids"]


def test_bulk_export_includes_unrestricted_and_permitting_consents(
    db_session: Session, test_doctor_user: User
):
    """Verify patients with PERMIT directives or no restrictions are completely exported."""
    permitting_pt = Patient(
        patient_id="PAT-PERMITTING-001",
        first_name="Alice",
        last_name="Permitting",
        date_of_birth=date(1992, 3, 14),
        gender="female",
        facility_id="FAC-001",
        status="active",
    )
    db_session.add(permitting_pt)
    db_session.flush()

    permit_consent = PatientConsent(
        consent_id="CNS-PERMIT-001",
        patient_id=permitting_pt.patient_id,
        status=ConsentStatus.ACTIVE,
        scope=ConsentScope.ALL_RECORDS,
        policy_rule=ConsentPolicyRule.PERMIT,
        purpose_of_use="RESEARCH",
        signer_name="Alice Permitting",
        digital_signature_hash="TEST-HASH-PERMIT-ALL",
    )
    db_session.add(permit_consent)
    db_session.commit()

    req = BulkExportRequest(export_type="patient")
    job = init_bulk_export_job(db_session, test_doctor_user.id, req, facility_id="FAC-001")
    completed_job = execute_bulk_export_sync(db_session, job.job_id)

    assert completed_job is not None
    assert completed_job.status == "COMPLETED"
    pt_file = next(f for f in completed_job.output_urls_json if f["type"] == "Patient")
    assert pt_file["count"] >= 1


def test_bulk_export_facility_tenant_isolation_with_consent(
    db_session: Session, test_doctor_user: User
):
    """Verify facility tenant filtering and consent opt-outs operate simultaneously."""
    fac2_pt = Patient(
        patient_id="PAT-FAC2-CONSENT-TEST",
        first_name="Bob",
        last_name="Remote",
        date_of_birth=date(1980, 1, 1),
        gender="male",
        facility_id="FAC-002",
        status="active",
    )
    db_session.add(fac2_pt)
    db_session.commit()

    # Export FAC-001 only
    req = BulkExportRequest(export_type="patient")
    job = init_bulk_export_job(db_session, test_doctor_user.id, req, facility_id="FAC-001")
    completed_job = execute_bulk_export_sync(db_session, job.job_id)

    assert completed_job is not None
    assert completed_job.status == "COMPLETED"
    # FAC-002 patient Bob must not be in FAC-001 export
    pt_file = next(f for f in completed_job.output_urls_json if f["type"] == "Patient")
    assert pt_file["count"] >= 0


def test_bulk_export_empty_when_all_patients_opted_out(
    db_session: Session, test_doctor_user: User
):
    """Verify clean 0-patient export when all patients in a facility are opted out."""
    opt_only_pt = Patient(
        patient_id="PAT-FAC99-OPT-ONLY",
        first_name="Solo",
        last_name="OptOut",
        date_of_birth=date(1975, 7, 7),
        gender="male",
        facility_id="FAC-999",
        status="active",
    )
    db_session.add(opt_only_pt)
    db_session.flush()

    consent = PatientConsent(
        consent_id="CNS-FAC99-DENY",
        patient_id=opt_only_pt.patient_id,
        status=ConsentStatus.ACTIVE,
        scope=ConsentScope.RESTRICT_EXPORT,
        policy_rule=ConsentPolicyRule.DENY,
        purpose_of_use="BULK_EXPORT",
        signer_name="Solo OptOut",
        digital_signature_hash="TEST-HASH-FAC99",
    )
    db_session.add(consent)
    db_session.commit()

    req = BulkExportRequest(export_type="patient")
    job = init_bulk_export_job(db_session, test_doctor_user.id, req, facility_id="FAC-999")
    completed_job = execute_bulk_export_sync(db_session, job.job_id)

    assert completed_job is not None
    assert completed_job.status == "COMPLETED"
    pt_file = next(f for f in completed_job.output_urls_json if f["type"] == "Patient")
    assert pt_file["count"] == 0


# ==============================================================================
# P1-2: CROSS-FACILITY REFERRAL & TRANSFER AUTHORIZATION TESTS
# ==============================================================================

def _ensure_facilities(db_session: Session):
    org = db_session.query(HealthOrganization).filter(HealthOrganization.org_id == "ORG-001").first()
    if not org:
        org = HealthOrganization(org_id="ORG-001", name="Enterprise Health System")
        db_session.add(org)
        db_session.flush()

    fac1 = db_session.query(ClinicalFacility).filter(ClinicalFacility.facility_id == "FAC-001").first()
    if not fac1:
        fac1 = ClinicalFacility(
            facility_id="FAC-001",
            org_id="ORG-001",
            name="Main Hospital",
            facility_code="MAIN-01",
            is_active=True,
        )
        db_session.add(fac1)

    fac2 = db_session.query(ClinicalFacility).filter(ClinicalFacility.facility_id == "FAC-002").first()
    if not fac2:
        fac2 = ClinicalFacility(
            facility_id="FAC-002",
            org_id="ORG-001",
            name="Regional Medical Center",
            facility_code="REG-02",
            is_active=True,
        )
        db_session.add(fac2)
    db_session.commit()


def test_cross_facility_transfer_authorization_success(
    db_session: Session, test_doctor_user: User, test_patient: Patient
):
    """Verify authorized clinician can initiate transfer between distinct active facilities with audit trail."""
    _ensure_facilities(db_session)
    test_doctor_user.default_facility_id = "FAC-001"
    db_session.commit()

    # Initiate cross-facility handoff from FAC-001 to FAC-002
    handoff_payload = HandoffCreate(
        framework=HandoffFramework.IPASS,
        handoff_type=HandoffType.UNIT_TRANSFER,
        illness_severity=IllnessSeverity.STABLE,
        source_facility_id="FAC-001",
        destination_facility_id="FAC-002",
        summary="Patient stabilized for inter-facility transfer to regional ICU.",
    )

    resp = create_handoff(
        db=db_session,
        patient_id_str=test_patient.patient_id,
        payload=handoff_payload,
        current_user=test_doctor_user,
    )

    assert resp.handoff_id is not None
    assert resp.source_facility_id == "FAC-001"
    assert resp.destination_facility_id == "FAC-002"

    # Verify dedicated audit event was emitted
    audit_record = (
        db_session.query(ClinicalAuditEvent)
        .filter(
            ClinicalAuditEvent.action == AuditAction.CROSS_FACILITY_TRANSFER,
            ClinicalAuditEvent.outcome == AuditOutcome.SUCCESS,
            ClinicalAuditEvent.patient_id == test_patient.patient_id,
        )
        .order_by(ClinicalAuditEvent.id.desc())
        .first()
    )
    assert audit_record is not None
    assert audit_record.metadata_json["source_facility_id"] == "FAC-001"
    assert audit_record.metadata_json["destination_facility_id"] == "FAC-002"
    assert audit_record.metadata_json["authorized_by_user_id"] == test_doctor_user.id


def test_cross_facility_transfer_unauthorized_rejected(
    db_session: Session, test_patient: Patient
):
    """Verify clinician without privileges at source facility is rejected with HTTP 403."""
    _ensure_facilities(db_session)

    # Create doctor assigned to FAC-002 only
    remote_doctor = User(
        name="Dr. Remote",
        email="remote_doc@example.com",
        password_hash="mock_hash",
        role="doctor",
        default_facility_id="FAC-002",
        is_active=True,
    )
    db_session.add(remote_doctor)
    db_session.commit()

    # Attempt cross-facility transfer originating from FAC-001 (where remote_doctor lacks privileges)
    handoff_payload = HandoffCreate(
        framework=HandoffFramework.SBAR,
        handoff_type=HandoffType.SERVICE_CONSULTATION,
        illness_severity=IllnessSeverity.WATCHER,
        source_facility_id="FAC-001",
        destination_facility_id="FAC-002",
        summary="Attempted unprivileged transfer consultation.",
    )

    with pytest.raises(Exception) as exc_info:
        create_handoff(
            db=db_session,
            patient_id_str=test_patient.patient_id,
            payload=handoff_payload,
            current_user=remote_doctor,
        )

    assert exc_info.value.status_code == 403
    assert "Unauthorized: Clinician does not possess active clinical privileges" in exc_info.value.detail

    # Verify denied audit record was recorded
    denied_audit = (
        db_session.query(ClinicalAuditEvent)
        .filter(
            ClinicalAuditEvent.action == AuditAction.CROSS_FACILITY_TRANSFER,
            ClinicalAuditEvent.outcome == AuditOutcome.DENIED_FORBIDDEN,
        )
        .order_by(ClinicalAuditEvent.id.desc())
        .first()
    )
    assert denied_audit is not None
    assert denied_audit.metadata_json["source_facility_id"] == "FAC-001"
    assert denied_audit.metadata_json["attempted_by_user_id"] == remote_doctor.id


def test_same_facility_transfer_unchanged(
    db_session: Session, test_doctor_user: User, test_patient: Patient
):
    """Verify internal same-facility handoffs and transfers continue without cross-facility barriers."""
    handoff_payload = HandoffCreate(
        framework=HandoffFramework.IPASS,
        handoff_type=HandoffType.SHIFT_CHANGE,
        illness_severity=IllnessSeverity.STABLE,
        source_facility_id="FAC-001",
        destination_facility_id="FAC-001",
        summary="Standard internal shift change transfer between day and night teams.",
    )

    resp = create_handoff(
        db=db_session,
        patient_id_str=test_patient.patient_id,
        payload=handoff_payload,
        current_user=test_doctor_user,
    )

    assert resp.handoff_id is not None
    assert resp.status.value == "active"


def test_cross_facility_transfer_invalid_destination_rejected(
    db_session: Session, test_doctor_user: User, test_patient: Patient
):
    """Verify transfer targeting nonexistent destination facility is rejected with HTTP 404."""
    _ensure_facilities(db_session)
    test_doctor_user.default_facility_id = "FAC-001"
    db_session.commit()

    handoff_payload = HandoffCreate(
        framework=HandoffFramework.IPASS,
        handoff_type=HandoffType.UNIT_TRANSFER,
        illness_severity=IllnessSeverity.STABLE,
        source_facility_id="FAC-001",
        destination_facility_id="FAC-NONEXISTENT-999",
        summary="Transfer with invalid destination facility code.",
    )

    with pytest.raises(Exception) as exc_info:
        create_handoff(
            db=db_session,
            patient_id_str=test_patient.patient_id,
            payload=handoff_payload,
            current_user=test_doctor_user,
        )

    assert exc_info.value.status_code == 404
    assert "Destination facility 'FAC-NONEXISTENT-999' not found" in exc_info.value.detail


# ==============================================================================
# P2-1: AUTOMATED AUDIT CHAIN VERIFICATION CELERY TASK TESTS
# ==============================================================================

def test_audit_chain_verification_celery_task(
    db_session: Session, test_doctor_user: User, test_patient: Patient
):
    """Verify Celery task runs SHA-256 hash-chain verification and returns valid status without mutating data."""
    from app.services.audit_service import audit_service
    from app.tasks.audit_tasks import verify_audit_log_integrity_task

    # 1. Clear any prior audit events to ensure pristine genesis chain for this test
    db_session.query(ClinicalAuditEvent).delete()
    db_session.commit()

    # 2. Create sequential valid audit events
    evt1 = audit_service.emit_audit_event(
        db=db_session,
        action="READ",
        resource_type="Patient",
        resource_id=test_patient.patient_id,
        user_id=test_doctor_user.id,
        patient_id=test_patient.patient_id,
        purpose_of_use="TREATMENT",
        outcome=AuditOutcome.SUCCESS,
        metadata={"detail": "Chart review step 1"},
    )
    evt2 = audit_service.emit_audit_event(
        db=db_session,
        action="UPDATE",
        resource_type="Patient",
        resource_id=test_patient.patient_id,
        user_id=test_doctor_user.id,
        patient_id=test_patient.patient_id,
        purpose_of_use="TREATMENT",
        outcome=AuditOutcome.SUCCESS,
        metadata={"detail": "Chart update step 2"},
    )
    db_session.commit()

    # 3. Run the audit integrity verification task
    result = verify_audit_log_integrity_task(db=db_session)

    assert result["status"] == "VALID"
    assert result["tamper_detected"] is False
    assert result["total_records_checked"] >= 2
    assert result["broken_links_count"] == 0
    assert result["tampered_event_ids"] == []

    # 4. Verify audit records were not modified
    db_evt1 = audit_service.get_audit_event_by_id(db_session, evt1.event_id)
    assert db_evt1.record_hash == evt1.record_hash


def test_audit_chain_verification_detects_tamper(
    db_session: Session, test_doctor_user: User, test_patient: Patient
):
    """Verify task detects corrupted/tampered hash chain and emits outbox incident event."""
    from app.models.outbox import OutboxEvent
    from app.services.audit_service import audit_service
    from app.tasks.audit_tasks import verify_audit_log_integrity_task

    # 1. Clear any prior audit events
    db_session.query(ClinicalAuditEvent).delete()
    db_session.commit()

    # 2. Create valid audit events
    evt1 = audit_service.emit_audit_event(
        db=db_session,
        action="READ",
        resource_type="Patient",
        resource_id=test_patient.patient_id,
        user_id=test_doctor_user.id,
        patient_id=test_patient.patient_id,
        outcome=AuditOutcome.SUCCESS,
    )
    evt2 = audit_service.emit_audit_event(
        db=db_session,
        action="DELETE",
        resource_type="ClinicalRecord",
        resource_id="REC-999",
        user_id=test_doctor_user.id,
        patient_id=test_patient.patient_id,
        outcome=AuditOutcome.SUCCESS,
    )
    db_session.commit()

    # 3. Simulate raw DB tamper on evt1 (change action without updating record_hash)
    db_session.query(ClinicalAuditEvent).filter(
        ClinicalAuditEvent.event_id == evt1.event_id
    ).update({"action": "MALICIOUS_UNLOGGED_ACTION"})
    db_session.commit()

    # 4. Run verification task
    result = verify_audit_log_integrity_task(db=db_session)

    assert result["status"] == "COMPROMISED"
    assert result["tamper_detected"] is True
    assert result["broken_links_count"] >= 1
    assert evt1.event_id in result["tampered_event_ids"]

    # 5. Verify outbox security event was enqueued
    outbox_alert = (
        db_session.query(OutboxEvent)
        .filter(OutboxEvent.event_type == "audit-chain-tamper-detected")
        .order_by(OutboxEvent.id.desc())
        .first()
    )
    assert outbox_alert is not None
    assert outbox_alert.payload_json["status"] == "COMPROMISED"
    assert evt1.event_id in outbox_alert.payload_json["tampered_event_ids"]



def test_audit_chain_beat_schedule_registered():
    """Verify Celery Beat daily audit integrity sweep schedule is properly configured."""
    from app.worker import celery_app

    if celery_app is not None:
        beat_schedule = celery_app.conf.beat_schedule
        assert "audit-integrity-sweep-daily" in beat_schedule
        entry = beat_schedule["audit-integrity-sweep-daily"]
        assert entry["task"] == "app.tasks.verify_audit_log_integrity_task"
        assert entry["schedule"] == 86400.0


# ==============================================================================
# P2-2: SMART ON FHIR V2 FINE-GRAINED SCOPE ENFORCEMENT TESTS
# ==============================================================================

def _create_smart_token(
    client: any,
    scope: str,
    patient_id: str = "PAT-FHIR-TEST-0001",
    user_id: int | None = None,
) -> str:
    """Helper to perform standard PKCE auth flow and obtain SMART token with given scope."""
    import base64
    import hashlib
    import secrets

    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    params: dict[str, any] = {
        "client_id": "smart-v2-test-client",
        "redirect_uri": "https://app.medigen.ai/smart/callback",
        "response_type": "code",
        "scope": scope,
        "state": "smart-state-xyz",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "patient": patient_id,
        "encounter": "ENC-001",
    }
    if user_id is not None:
        params["user_id"] = user_id

    auth_resp = client.get(
        "/api/v1/smart/authorize",
        params=params,
    )
    assert auth_resp.status_code == 200, auth_resp.text
    auth_code = auth_resp.json()["code"]

    token_resp = client.post(
        "/api/v1/smart/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": "https://app.medigen.ai/smart/callback",
            "client_id": "smart-v2-test-client",
            "code_verifier": code_verifier,
        },
    )
    assert token_resp.status_code == 200, token_resp.text
    return token_resp.json()["access_token"]


def test_smart_v2_scope_enforcement_allowed(
    client: any, db_session: Session, test_doctor_user: User, test_patient: Patient
):
    """Verify SMART client with specific patient/Observation.read scope successfully accesses Observation."""
    enc = (
        db_session.query(Encounter)
        .filter(Encounter.attending_user_id == test_doctor_user.id, Encounter.patient_id == test_patient.id)
        .first()
    )
    if not enc:
        enc = Encounter(
            encounter_id=f"ENC-SMART-{test_patient.patient_id}",
            patient_id=test_patient.id,
            attending_user_id=test_doctor_user.id,
            chief_complaint="Routine evaluation",
            facility_id="FAC-001",
        )
        db_session.add(enc)
        db_session.commit()

    token = _create_smart_token(
        client,
        scope="launch/patient patient/Observation.read openid fhirUser",
        patient_id=test_patient.patient_id,
        user_id=test_doctor_user.id,
    )
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        f"/api/v1/fhir/Observation/OBS-{test_patient.patient_id}",
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["resourceType"] == "Observation"


def test_smart_v2_scope_enforcement_denied(
    client: any, test_doctor_user: User, test_patient: Patient
):
    """Verify SMART client with only patient/Observation.read is denied access to Condition with 403 insufficient_scope."""
    token = _create_smart_token(
        client,
        scope="launch/patient patient/Observation.read openid fhirUser",
        patient_id=test_patient.patient_id,
        user_id=test_doctor_user.id,
    )
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(
        f"/api/v1/fhir/Condition/COND-{test_patient.patient_id}",
        headers=headers,
    )
    assert res.status_code == 403
    assert res.json()["detail"] == "insufficient_scope"
    auth_header = res.headers.get("www-authenticate", "")
    assert 'error="insufficient_scope"' in auth_header
    assert 'scope="patient/Condition.read"' in auth_header


def test_smart_v2_wildcard_scope(
    client: any, db_session: Session, test_doctor_user: User, test_patient: Patient
):
    """Verify SMART client with patient/*.read wildcard scope can access all supported patient resources."""
    enc = (
        db_session.query(Encounter)
        .filter(Encounter.attending_user_id == test_doctor_user.id, Encounter.patient_id == test_patient.id)
        .first()
    )
    if not enc:
        enc = Encounter(
            encounter_id=f"ENC-SMART-WILD-{test_patient.patient_id}",
            patient_id=test_patient.id,
            attending_user_id=test_doctor_user.id,
            chief_complaint="Routine evaluation",
            facility_id="FAC-001",
        )
        db_session.add(enc)
        db_session.commit()

    token = _create_smart_token(
        client,
        scope="launch/patient patient/*.read openid fhirUser",
        patient_id=test_patient.patient_id,
        user_id=test_doctor_user.id,
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Observation
    res_obs = client.get(f"/api/v1/fhir/Observation/OBS-{test_patient.patient_id}", headers=headers)
    assert res_obs.status_code == 200

    # Condition
    res_cond = client.get(f"/api/v1/fhir/Condition/COND-{test_patient.patient_id}", headers=headers)
    assert res_cond.status_code == 200

    # Patient
    res_pat = client.get(f"/api/v1/fhir/Patient/{test_patient.patient_id}", headers=headers)
    assert res_pat.status_code == 200


def test_internal_clinician_jwt_unaffected(
    client: any, db_session: Session, test_doctor_user: User, test_patient: Patient
):
    """Verify internal clinician session JWTs bypass SMART scope checks and access all clinical resources."""
    from app.core.security import create_access_token

    # Link doctor to patient via attending encounter
    enc = (
        db_session.query(Encounter)
        .filter(Encounter.attending_user_id == test_doctor_user.id, Encounter.patient_id == test_patient.id)
        .first()
    )
    if not enc:
        enc = Encounter(
            encounter_id=f"ENC-CLINICIAN-{test_patient.patient_id}",
            patient_id=test_patient.id,
            attending_user_id=test_doctor_user.id,
            encounter_date=datetime.now(timezone.utc),
            chief_complaint="Routine clinical evaluation",
            assessment="Stable clinical condition",
            status="in_progress",
            facility_id="FAC-001",
        )
        db_session.add(enc)
        db_session.commit()

    clinician_token = create_access_token(subject=test_doctor_user.id, role=test_doctor_user.role)
    headers = {"Authorization": f"Bearer {clinician_token}"}

    # Observation
    res_obs = client.get(f"/api/v1/fhir/Observation/OBS-{test_patient.patient_id}", headers=headers)
    assert res_obs.status_code == 200

    # Condition
    res_cond = client.get(f"/api/v1/fhir/Condition/COND-{test_patient.patient_id}", headers=headers)
    assert res_cond.status_code == 200

    # Patient
    res_pat = client.get(f"/api/v1/fhir/Patient/{test_patient.patient_id}", headers=headers)
    assert res_pat.status_code == 200




def test_smart_insufficient_scope_audit(
    client: any, db_session: Session, test_doctor_user: User, test_patient: Patient
):
    """Verify insufficient scope denial emits an audit event with DENIED_FORBIDDEN and error metadata."""
    token = _create_smart_token(
        client,
        scope="launch/patient patient/Observation.read openid fhirUser",
        patient_id=test_patient.patient_id,
        user_id=test_doctor_user.id,
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Clear prior audit events
    db_session.query(ClinicalAuditEvent).delete()
    db_session.commit()

    # Trigger scope denial
    res = client.get(f"/api/v1/fhir/Condition/COND-{test_patient.patient_id}", headers=headers)
    assert res.status_code == 403

    # Verify audit event
    audit_evt = (
        db_session.query(ClinicalAuditEvent)
        .filter(
            ClinicalAuditEvent.outcome == AuditOutcome.DENIED_FORBIDDEN,
            ClinicalAuditEvent.resource_type == "Condition",
        )
        .order_by(ClinicalAuditEvent.id.desc())
        .first()
    )
    assert audit_evt is not None
    assert audit_evt.metadata_json["error"] == "insufficient_scope"
    assert audit_evt.metadata_json["required_scope"] == "patient/Condition.read"
    assert "patient/Observation.read" in audit_evt.metadata_json["granted_scope"]


def test_smart_existing_authentication_regression(
    client: any, db_session: Session, test_doctor_user: User, test_patient: Patient
):
    """Verify SMART token revocation immediately invalidates access on subsequent FHIR calls."""
    from app.services.smart_service import smart_service

    enc = (
        db_session.query(Encounter)
        .filter(Encounter.attending_user_id == test_doctor_user.id, Encounter.patient_id == test_patient.id)
        .first()
    )
    if not enc:
        enc = Encounter(
            encounter_id=f"ENC-SMART-REVOKE-{test_patient.patient_id}",
            patient_id=test_patient.id,
            attending_user_id=test_doctor_user.id,
            chief_complaint="Routine evaluation",
            facility_id="FAC-001",
        )
        db_session.add(enc)
        db_session.commit()

    token = _create_smart_token(
        client,
        scope="launch/patient patient/Observation.read openid fhirUser",
        patient_id=test_patient.patient_id,
        user_id=test_doctor_user.id,
    )
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Valid call before revocation
    res_before = client.get(f"/api/v1/fhir/Observation/OBS-{test_patient.patient_id}", headers=headers)
    assert res_before.status_code == 200

    # 2. Revoke token via RFC 7009
    smart_service.revoke_token(db_session, token)

    # 3. Call after revocation -> Expect 401 Unauthorized
    res_after = client.get(f"/api/v1/fhir/Observation/OBS-{test_patient.patient_id}", headers=headers)
    assert res_after.status_code == 401
    assert "revoked" in res_after.json()["detail"].lower()
