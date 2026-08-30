"""Integration and Unit Tests for Clinical Security, Auditability, Consent & Compliance Governance.

Phase 9.0.19: Clinical Security, Auditability, Consent & Compliance Governance.
"""

from datetime import datetime, timezone
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.security import (
    AuditAction,
    AuditOutcome,
    ClinicalAuditEvent,
    ConsentPolicyRule,
    ConsentScope,
    ConsentStatus,
    DataRetentionPolicy,
    HoldStatus,
    IncidentSeverity,
    IncidentStatus,
    LegalClinicalHold,
    PatientConsent,
    SecurityIncident,
)
from app.models.user import User, UserRole
from app.schemas.patient import Gender, PatientStatus


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.ADMIN,
    email: str = "security_admin@hospital.org",
    name: str = "Chief Information Security Officer",
) -> tuple[dict[str, str], int]:
    """Helper to register/login a user and get JWT Bearer headers."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123!",
            "name": name,
            "role": role.value,
        },
    )

    res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    data = res.json()
    token = data["access_token"]
    user_id = data.get("user", {}).get("id", 1)
    return {"Authorization": f"Bearer {token}"}, user_id


@pytest.fixture
def test_patient(db_session: Session) -> Patient:
    """Fixture ensuring a patient exists in the test DB."""
    patient = db_session.query(Patient).filter_by(patient_id="PAT-SEC-001").first()
    if not patient:
        patient = Patient(
            patient_id="PAT-SEC-001",
            first_name="Eleanor",
            last_name="Vance",
            date_of_birth=datetime(1988, 4, 12).date(),
            gender=Gender.FEMALE,
            phone="+1-555-0199",
            email="eleanor.vance@example.org",
            address="742 Evergreen Terrace",
            status=PatientStatus.ACTIVE,
        )
        db_session.add(patient)
        db_session.commit()
        db_session.refresh(patient)
    return patient


def test_audit_event_emission_and_tamper_integrity(
    client: TestClient, db_session: Session
):
    """Test cryptographic SHA-256 hash chaining and tamper detection in audit trail."""
    admin_headers, admin_id = get_auth_headers(client, role=UserRole.ADMIN, email="audit_admin@hospital.org")

    # 1. Verify audit integrity on fresh state
    res = client.post("/api/v1/audit/verify-integrity", headers=admin_headers)
    assert res.status_code == status.HTTP_200_OK, res.text
    data = res.json()
    assert data["status"] == "VALID"
    assert data["tamper_detected"] is False

    # 2. Query audit events
    res_query = client.get("/api/v1/audit/events?page=1&page_size=10", headers=admin_headers)
    assert res_query.status_code == status.HTTP_200_OK
    assert "events" in res_query.json()

    # 3. Simulate tamper detection by inserting an event with mismatched hash
    tampered_event = ClinicalAuditEvent(
        event_id="AUD-TAMPER-001",
        timestamp=datetime.now(timezone.utc),
        user_id=admin_id,
        user_role="ADMIN",
        action="UPDATE",
        resource_type="Patient",
        resource_id="PAT-SEC-001",
        outcome=AuditOutcome.SUCCESS,
        metadata_json={"modified": "unauthorized"},
        prev_record_hash="INVALID_HASH_VALUE_0000000000000000000000000000000000000000000000",
        record_hash="CORRUPTED_HASH_VALUE_000000000000000000000000000000000000000000000",
    )
    db_session.add(tampered_event)
    db_session.commit()

    # 4. Verify integrity detects the broken chain
    res_tamper = client.post("/api/v1/audit/verify-integrity", headers=admin_headers)
    assert res_tamper.status_code == status.HTTP_200_OK
    tamper_data = res_tamper.json()
    assert tamper_data["tamper_detected"] is True
    assert tamper_data["status"] == "COMPROMISED"
    assert "AUD-TAMPER-001" in tamper_data["tampered_event_ids"]

    # Cleanup tampered event
    db_session.delete(tampered_event)
    db_session.commit()


def test_patient_consent_lifecycle_and_enforcement(
    client: TestClient, db_session: Session, test_patient: Patient
):
    """Test granting, policy evaluation, category restrictions, and immediate revocation of patient consent."""
    doc_headers, doc_id = get_auth_headers(
        client, role=UserRole.DOCTOR, email="consent_doc@hospital.org", name="Dr. Consent Officer"
    )

    # 1. Grant consent with DENY policy for GENOMICS
    consent_payload = {
        "scope": ConsentScope.GENOMICS_ONLY,
        "policy_rule": ConsentPolicyRule.DENY,
        "purpose_of_use": "RESEARCH",
        "data_category": "GENOMICS",
        "signed_by_patient": True,
        "signer_name": "Eleanor Vance",
        "signer_relationship": "SELF",
    }
    res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/consents",
        json=consent_payload,
        headers=doc_headers,
    )
    assert res.status_code == status.HTTP_201_CREATED, res.text
    consent_data = res.json()
    assert consent_data["patient_id"] == test_patient.patient_id
    assert consent_data["policy_rule"] == "DENY"
    assert consent_data["status"] == "ACTIVE"
    assert consent_data["digital_signature_hash"] != "UNVERIFIED"
    consent_id = consent_data["consent_id"]

    # 2. Verify consent evaluation blocks GENOMICS research
    verify_res = client.post(
        "/api/v1/consents/verify",
        json={
            "patient_id": test_patient.patient_id,
            "resource_type": "GenomicProfile",
            "action": "READ",
            "purpose_of_use": "RESEARCH",
            "data_category": "GENOMICS",
        },
        headers=doc_headers,
    )
    assert verify_res.status_code == status.HTTP_200_OK
    assert verify_res.json()["is_permitted"] is False
    assert "DENY" in verify_res.json()["reason"]

    # 3. Verify standard treatment without category restriction is permitted
    verify_treat_res = client.post(
        "/api/v1/consents/verify",
        json={
            "patient_id": test_patient.patient_id,
            "resource_type": "Observation",
            "action": "READ",
            "purpose_of_use": "TREATMENT",
            "data_category": "GENERAL_CLINICAL",
        },
        headers=doc_headers,
    )
    assert verify_treat_res.status_code == status.HTTP_200_OK
    assert verify_treat_res.json()["is_permitted"] is True

    # 4. Verify emergency override protocol
    emergency_res = client.post(
        "/api/v1/consents/verify",
        json={
            "patient_id": test_patient.patient_id,
            "resource_type": "GenomicProfile",
            "action": "READ",
            "purpose_of_use": "EMERGENCY_OVERRIDE",
            "data_category": "GENOMICS",
        },
        headers=doc_headers,
    )
    assert emergency_res.status_code == status.HTTP_200_OK
    assert emergency_res.json()["is_permitted"] is True
    assert emergency_res.json()["is_emergency_override"] is True

    # 5. Revoke consent with immediate effect
    revoke_res = client.post(
        f"/api/v1/consents/{consent_id}/revoke",
        json={"revocation_reason": "Patient requested withdrawal of research restriction"},
        headers=doc_headers,
    )
    assert revoke_res.status_code == status.HTTP_200_OK
    assert revoke_res.json()["status"] == "REVOKED"
    assert revoke_res.json()["revocation_reason"] == "Patient requested withdrawal of research restriction"


def test_security_anomaly_detection_and_incident_creation(
    client: TestClient, db_session: Session
):
    """Test deterministic security anomaly scanner and incident tracking workflow."""
    admin_headers, admin_id = get_auth_headers(
        client, role=UserRole.ADMIN, email="incident_admin@hospital.org"
    )

    # 1. Trigger proactive security scan
    scan_res = client.post("/api/v1/security/scan?lookback_minutes=60", headers=admin_headers)
    assert scan_res.status_code == status.HTTP_200_OK
    scan_data = scan_res.json()
    assert "events_analyzed" in scan_data
    assert "anomalies_detected" in scan_data

    # 2. Manually register a high-severity security incident
    incident_res = client.post(
        "/api/v1/security/incidents",
        json={
            "severity": IncidentSeverity.HIGH,
            "event_type": "SUSPICIOUS_BULK_EXPORT",
            "description": "User requested multiple bulk FHIR exports outside authorized clinic hours",
            "ip_address": "192.168.1.105",
            "evidence_metadata": {"export_count": 5, "timeframe_min": 10},
        },
        headers=admin_headers,
    )
    assert incident_res.status_code == status.HTTP_201_CREATED
    incident_data = incident_res.json()
    assert incident_data["severity"] == "HIGH"
    assert incident_data["status"] == "OPEN"
    incident_id = incident_data["incident_id"]

    # 3. Triage & investigate incident
    patch_res = client.patch(
        f"/api/v1/security/incidents/{incident_id}",
        json={
            "status": IncidentStatus.INVESTIGATING,
            "assigned_to_user_id": admin_id,
            "resolution_notes": "Contacted attending provider to verify research protocol access.",
        },
        headers=admin_headers,
    )
    assert patch_res.status_code == status.HTTP_200_OK
    assert patch_res.json()["status"] == "INVESTIGATING"

    # 4. Resolve incident
    resolve_res = client.patch(
        f"/api/v1/security/incidents/{incident_id}",
        json={
            "status": IncidentStatus.RESOLVED,
            "resolution_notes": "Legitimate institutional audit verified. No breach occurred.",
        },
        headers=admin_headers,
    )
    assert resolve_res.status_code == status.HTTP_200_OK
    assert resolve_res.json()["status"] == "RESOLVED"
    assert resolve_res.json()["resolved_at"] is not None


def test_data_retention_and_legal_hold_safeguards(
    client: TestClient, db_session: Session, test_patient: Patient
):
    """Test regulatory retention policy schedule and legal/clinical hold enforcement."""
    admin_headers, admin_id = get_auth_headers(
        client, role=UserRole.ADMIN, email="governance_admin@hospital.org"
    )

    # 1. List data retention policies
    ret_res = client.get("/api/v1/security/retention/policies", headers=admin_headers)
    assert ret_res.status_code == status.HTTP_200_OK
    policies = ret_res.json()
    assert len(policies) >= 3

    # 2. Place legal hold on patient records
    hold_res = client.post(
        "/api/v1/security/holds",
        json={
            "patient_id": test_patient.patient_id,
            "scope_category": "ALL_RECORDS",
            "reason": "Active Clinical Trial Follow-Up & Regulatory Retention Requirement",
            "notes": "Hold prevents disposition until clinical trial phase 3 completes.",
        },
        headers=admin_headers,
    )
    assert hold_res.status_code == status.HTTP_201_CREATED
    hold_data = hold_res.json()
    assert hold_data["patient_id"] == test_patient.patient_id
    assert hold_data["status"] == "ACTIVE"
    hold_id = hold_data["hold_id"]

    # 3. List active holds
    list_holds_res = client.get("/api/v1/security/holds?status=ACTIVE", headers=admin_headers)
    assert list_holds_res.status_code == status.HTTP_200_OK
    assert any(h["hold_id"] == hold_id for h in list_holds_res.json())

    # 4. Release legal hold
    release_res = client.post(
        f"/api/v1/security/holds/{hold_id}/release",
        json={"notes": "Trial protocol concluded. Standard retention schedule resumed."},
        headers=admin_headers,
    )
    assert release_res.status_code == status.HTTP_200_OK
    assert release_res.json()["status"] == "RELEASED"
    assert release_res.json()["released_at"] is not None


def test_fhir_consent_and_audit_event_interoperability(
    client: TestClient, db_session: Session, test_patient: Patient
):
    """Test standard FHIR R4 Consent and AuditEvent resource exports."""
    admin_headers, admin_id = get_auth_headers(
        client, role=UserRole.ADMIN, email="fhir_security_admin@hospital.org"
    )

    # 1. Create a patient consent directive
    consent_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/consents",
        json={
            "scope": ConsentScope.RESEARCH_ONLY,
            "policy_rule": ConsentPolicyRule.PERMIT,
            "purpose_of_use": "RESEARCH",
            "data_category": "GENOMICS",
            "signed_by_patient": True,
            "signer_name": "Eleanor Vance",
            "signer_relationship": "SELF",
        },
        headers=admin_headers,
    )
    assert consent_res.status_code == status.HTTP_201_CREATED
    consent_id = consent_res.json()["consent_id"]

    # 2. Export FHIR Consent resource
    fhir_consent_res = client.get(f"/api/v1/fhir/Consent/{consent_id}", headers=admin_headers)
    assert fhir_consent_res.status_code == status.HTTP_200_OK, fhir_consent_res.text
    fhir_consent = fhir_consent_res.json()
    assert fhir_consent["resourceType"] == "Consent"
    assert fhir_consent["id"] == consent_id
    assert fhir_consent["patient"]["reference"] == f"Patient/{test_patient.patient_id}"
    assert fhir_consent["provision"]["type"] == "permit"

    # 3. Export FHIR Patient Consents Bundle
    bundle_res = client.get(f"/api/v1/fhir/patients/{test_patient.patient_id}/consents", headers=admin_headers)
    assert bundle_res.status_code == status.HTTP_200_OK
    bundle = bundle_res.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert len(bundle["entry"]) >= 1

    # 4. Fetch latest audit event and export as FHIR AuditEvent
    audit_list = client.get("/api/v1/audit/events?page=1&page_size=1", headers=admin_headers).json()["events"]
    if audit_list:
        latest_audit_id = audit_list[0]["event_id"]
        fhir_audit_res = client.get(f"/api/v1/fhir/AuditEvent/{latest_audit_id}", headers=admin_headers)
        assert fhir_audit_res.status_code == status.HTTP_200_OK
        fhir_audit = fhir_audit_res.json()
        assert fhir_audit["resourceType"] == "AuditEvent"
        assert fhir_audit["id"] == latest_audit_id
        assert len(fhir_audit["agent"]) >= 1


def test_compliance_summary_and_async_background_tasks(
    client: TestClient, db_session: Session
):
    """Test system compliance summary calculation and asynchronous task enqueuing."""
    admin_headers, admin_id = get_auth_headers(
        client, role=UserRole.ADMIN, email="compliance_summary_admin@hospital.org"
    )

    # 1. Get real-time compliance summary
    summary_res = client.get("/api/v1/security/compliance/summary", headers=admin_headers)
    assert summary_res.status_code == status.HTTP_200_OK
    summary = summary_res.json()
    assert "compliance_score_percent" in summary
    assert summary["compliance_score_percent"] >= 0.0
    assert summary["audit_tamper_integrity_status"] in ["VALID", "COMPROMISED"]
    assert summary["status"] in ["COMPLIANT", "WARNING", "NON_COMPLIANT"]

    # 2. Enqueue background audit integrity task
    task_res1 = client.post("/api/v1/tasks/security/audit-integrity", headers=admin_headers)
    assert task_res1.status_code == status.HTTP_202_ACCEPTED
    assert task_res1.json()["task_type"] == "audit_log_integrity_check"

    # 3. Enqueue background security anomaly scan
    task_res2 = client.post("/api/v1/tasks/security/anomaly-scan?lookback_minutes=60", headers=admin_headers)
    assert task_res2.status_code == status.HTTP_202_ACCEPTED
    assert task_res2.json()["task_type"] == "security_anomaly_scan"

    # 4. Enqueue background compliance report task
    task_res3 = client.post("/api/v1/tasks/security/compliance-report", headers=admin_headers)
    assert task_res3.status_code == status.HTTP_202_ACCEPTED
    assert task_res3.json()["task_type"] == "compliance_report_generation"
