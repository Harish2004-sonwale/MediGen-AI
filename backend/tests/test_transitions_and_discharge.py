"""Unit and integration tests for Phase 9.0.12: Clinical Transitions of Care & Discharge Protocols.

Validates:
- Structured I-PASS and SBAR handoff creation, synthesis, and lifecycle
- Receiver synthesis and formal acknowledgment workflow
- Automated discharge protocol synthesis with medication reconciliation
- Multi-disciplinary signoff (Attending Physician, Registered Nurse, Clinical Pharmacist)
- Asynchronous background worker task dispatch and synchronous execution
- FHIR R4 Composition (Discharge Summary) and Communication (Handoff) serialization
- Strict RBAC and cross-patient data isolation
"""

from datetime import date, datetime, timezone
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.alert import ClinicalAlert
from app.models.care_plan import CarePlan
from app.models.discharge import DischargeProtocol
from app.models.encounter import Encounter
from app.models.handoff import ClinicalHandoff
from app.models.patient import Patient
from app.models.risk_assessment import ClinicalRiskAssessment
from app.models.user import UserRole
from app.models.vital import VitalTelemetry
from app.schemas.encounter import EncounterStatus, EncounterType
from app.schemas.patient import Gender, PatientStatus
from tests.conftest import TestingSessionLocal


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "transitions_doc@hospital.org",
    name: str = "Dr. Inpatient Attending",
) -> tuple[dict[str, str], int]:
    """Register and login helper returning authorization headers and user ID."""
    client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "SecurePassword123!",
            "role": role.value,
        },
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login_res.json()["access_token"]
    user_id = login_res.json()["user"]["id"]
    return {"Authorization": f"Bearer {token}"}, user_id


@pytest.fixture
def test_inpatient_record(db_session: Session) -> Patient:
    patient = Patient(
        patient_id="PAT-TRANS-001",
        first_name="Beatrice",
        last_name="Holloway",
        date_of_birth=date(1954, 3, 15),  # 72 yrs
        gender=Gender.FEMALE,
        email="beatrice.holloway@example.com",
        phone="+1555019382",
        status=PatientStatus.ACTIVE,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)

    # Inpatient encounter
    encounter = Encounter(
        encounter_id="ENC-TRANS-001",
        patient_id=patient.id,
        encounter_date=datetime.now(timezone.utc),
        encounter_type=EncounterType.FOLLOW_UP,
        chief_complaint="Acute decompensated heart failure and fluid overload",
        assessment="Congestive Heart Failure NYHA Class III, Essential Hypertension",
        plan="IV diuresis, telemetry, low sodium diet, discharge planning",
        status=EncounterStatus.COMPLETED,
    )
    db_session.add(encounter)

    # Vitals
    vital = VitalTelemetry(
        reading_id="VIT-TRANS-001",
        patient_id=patient.id,
        heart_rate=88,
        systolic_bp=138,
        diastolic_bp=84,
        spo2_percent=96.0,
        source="ward_monitor",
        measured_at=datetime.now(timezone.utc),
    )
    db_session.add(vital)

    # Risk Assessment
    risk = ClinicalRiskAssessment(
        assessment_id="RISK-TRANS-001",
        patient_id=patient.id,
        risk_type="readmission_30d",
        risk_score=68.5,
        risk_tier="HIGH",
        predicted_outcome="High vulnerability for 30-day post-discharge readmission.",
        assessed_at=datetime.now(timezone.utc),
    )
    db_session.add(risk)
    db_session.commit()
    return patient


@pytest.fixture
def secondary_patient_record(db_session: Session) -> Patient:
    patient = Patient(
        patient_id="PAT-TRANS-002",
        first_name="Julian",
        last_name="Bashir",
        date_of_birth=date(1988, 11, 2),
        gender=Gender.MALE,
        email="julian.bashir@example.com",
        phone="+1555019383",
        status=PatientStatus.ACTIVE,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


def test_handoff_manual_and_ipass_synthesis(
    client: TestClient,
    test_inpatient_record: Patient,
    db_session: Session,
):
    """Test manual creation and automated I-PASS handoff synthesis."""
    headers, user_id = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_ipass@hospital.org")

    # 1. Manual Creation
    create_payload = {
        "framework": "ipass",
        "handoff_type": "shift_change",
        "illness_severity": "stable",
        "summary": "Patient hemodynamically stable following morning diuresis.",
        "action_items": [
            {
                "item_id": "ACT-01",
                "task_description": "Check basic metabolic panel at 18:00.",
                "role_required": "resident",
                "priority": "ROUTINE",
                "is_completed": False,
            }
        ],
        "situational_awareness": [
            {
                "plan_id": "CTG-01",
                "trigger_condition": "If potassium < 3.5 mEq/L",
                "immediate_action": "Administer 20 mEq KCl oral protocol.",
                "escalation_contact": "On-call physician",
            }
        ],
    }
    resp = client.post(
        f"/api/v1/patients/{test_inpatient_record.patient_id}/handoffs",
        json=create_payload,
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    handoff_id = data["handoff_id"]
    assert data["status"] == "active"
    assert data["illness_severity"] == "stable"
    assert len(data["action_items_json"]) == 1

    # 2. Automated I-PASS Synthesis
    synth_resp = client.post(
        f"/api/v1/patients/{test_inpatient_record.patient_id}/handoffs/synthesize",
        json={
            "framework": "ipass",
            "handoff_type": "shift_change",
            "custom_context": "Daughter visiting this afternoon to discuss discharge plan.",
        },
        headers=headers,
    )
    assert synth_resp.status_code == 201
    synth_data = synth_resp.json()
    assert synth_data["status"] == "draft"  # AI synthesis must start in draft
    assert synth_data["is_ai_generated"] is True
    assert "Beatrice" in synth_data["summary"]
    assert len(synth_data["action_items_json"]) >= 2
    assert len(synth_data["situational_awareness_json"]) >= 1

    # 3. Retrieve Handoff
    get_resp = client.get(f"/api/v1/handoffs/{handoff_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["handoff_id"] == handoff_id

    # 4. List Patient Handoffs
    list_resp = client.get(f"/api/v1/patients/{test_inpatient_record.patient_id}/handoffs", headers=headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] >= 2


def test_sbar_handoff_and_acknowledgement(
    client: TestClient,
    test_inpatient_record: Patient,
    db_session: Session,
):
    """Test SBAR framework synthesis and receiver formal read-back acknowledgment."""
    sender_headers, sender_id = get_auth_headers(client, role=UserRole.DOCTOR, email="sender_sbar@hospital.org")
    receiver_headers, receiver_id = get_auth_headers(client, role=UserRole.DOCTOR, email="receiver_sbar@hospital.org")

    # Synthesize SBAR handoff
    synth_resp = client.post(
        f"/api/v1/patients/{test_inpatient_record.patient_id}/handoffs/synthesize",
        json={
            "framework": "sbar",
            "handoff_type": "unit_transfer",
            "receiver_user_id": receiver_id,
        },
        headers=sender_headers,
    )
    assert synth_resp.status_code == 201
    handoff = synth_resp.json()
    handoff_id = handoff["handoff_id"]
    assert "SITUATION:" in handoff["summary"]
    assert "BACKGROUND:" in handoff["summary"]
    assert "ASSESSMENT:" in handoff["summary"]
    assert "RECOMMENDATION:" in handoff["summary"]

    # Receiver acknowledges with synthesis read-back notes
    ack_resp = client.post(
        f"/api/v1/handoffs/{handoff_id}/acknowledge",
        json={"synthesis_notes": "Received transfer handover. Fluid balance stable, awaiting evening lab report."},
        headers=receiver_headers,
    )
    assert ack_resp.status_code == 200
    ack_data = ack_resp.json()
    assert ack_data["status"] == "acknowledged"
    assert ack_data["receiver_user_id"] == receiver_id
    assert ack_data["acknowledged_at"] is not None
    assert "Received transfer handover" in ack_data["synthesis_notes"]


def test_discharge_protocol_synthesis_and_medication_reconciliation(
    client: TestClient,
    test_inpatient_record: Patient,
    db_session: Session,
):
    """Test automated discharge protocol synthesis with structured medication reconciliation."""
    headers, user_id = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_discharge@hospital.org")

    # Synthesize discharge protocol
    synth_resp = client.post(
        f"/api/v1/patients/{test_inpatient_record.patient_id}/discharge-protocols/synthesize",
        json={
            "disposition": "home_self_care",
            "custom_instructions": "Ensure daily morning weight log is brought to first outpatient appointment.",
        },
        headers=headers,
    )
    assert synth_resp.status_code == 201, synth_resp.text
    data = synth_resp.json()
    discharge_id = data["discharge_id"]
    assert data["status"] == "draft"  # Assistive synthesis starts as draft
    assert data["disposition"] == "home_self_care"
    assert "Beatrice" in data["hospital_course_summary"]
    assert len(data["medication_reconciliation_json"]) >= 2
    assert len(data["followup_instructions_json"]) >= 2
    assert len(data["warning_symptoms_json"]) >= 2
    assert "weight" in data["activity_and_diet_instructions"].lower()

    # Retrieve specific discharge protocol
    get_resp = client.get(f"/api/v1/discharge-protocols/{discharge_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["discharge_id"] == discharge_id

    # Update discharge protocol
    patch_resp = client.patch(
        f"/api/v1/discharge-protocols/{discharge_id}",
        json={
            "activity_and_diet_instructions": "Updated: Strict low sodium diet < 1500mg/day. No heavy lifting.",
            "status": "under_review",
        },
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "under_review"


def test_discharge_protocol_multi_disciplinary_signoff(
    client: TestClient,
    test_inpatient_record: Patient,
    db_session: Session,
):
    """Test multi-disciplinary signoff: Nurse, Pharmacist, and Attending Physician approval."""
    doc_headers, doc_id = get_auth_headers(client, role=UserRole.DOCTOR, email="attending_signoff@hospital.org")
    nurse_headers, nurse_id = get_auth_headers(client, role=UserRole.HEALTHCARE_STAFF, email="nurse_review@hospital.org")

    # Create discharge protocol
    create_resp = client.post(
        f"/api/v1/patients/{test_inpatient_record.patient_id}/discharge-protocols",
        json={
            "hospital_course_summary": "Inpatient diuresis successful with 4kg net negative fluid balance.",
            "primary_discharge_diagnosis": "Acute on Chronic Systolic Heart Failure (Compensated)",
            "disposition": "home_self_care",
        },
        headers=doc_headers,
    )
    discharge_id = create_resp.json()["discharge_id"]

    # 1. Nursing Signoff
    nurse_resp = client.post(
        f"/api/v1/discharge-protocols/{discharge_id}/signoff",
        json={"signoff_role": "registered_nurse", "clinical_notes": "Discharge teaching completed with patient."},
        headers=nurse_headers,
    )
    assert nurse_resp.status_code == 200
    assert nurse_resp.json()["nurse_user_id"] == nurse_id

    # 2. Pharmacist Signoff
    pharm_resp = client.post(
        f"/api/v1/discharge-protocols/{discharge_id}/signoff",
        json={"signoff_role": "clinical_pharmacist", "clinical_notes": "Medication reconciliation verified."},
        headers=nurse_headers,
    )
    assert pharm_resp.status_code == 200
    assert pharm_resp.json()["pharmacist_user_id"] == nurse_id

    # 3. Attending Physician Final Signoff
    doc_resp = client.post(
        f"/api/v1/discharge-protocols/{discharge_id}/signoff",
        json={"signoff_role": "attending_physician", "clinical_notes": "Patient cleared for safe discharge home."},
        headers=doc_headers,
    )
    assert doc_resp.status_code == 200
    assert doc_resp.json()["status"] == "ready_for_discharge"
    assert doc_resp.json()["attending_user_id"] == doc_id
    assert doc_resp.json()["signed_off_at"] is not None


def test_async_handoff_and_discharge_background_workers(
    client: TestClient,
    test_inpatient_record: Patient,
    db_session: Session,
):
    """Test background task queuing and execution for handoff and discharge synthesis."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_async_trans@hospital.org")

    # Enqueue Handoff Task
    handoff_task_resp = client.post(
        f"/api/v1/tasks/patients/{test_inpatient_record.patient_id}/handoff/synthesize",
        json={"framework": "ipass", "handoff_type": "shift_change"},
        headers=headers,
    )
    assert handoff_task_resp.status_code == 202
    assert "TASK-" in handoff_task_resp.json()["task_id"]

    # Enqueue Discharge Task
    discharge_task_resp = client.post(
        f"/api/v1/tasks/patients/{test_inpatient_record.patient_id}/discharge/synthesize",
        json={"disposition": "home_self_care"},
        headers=headers,
    )
    assert discharge_task_resp.status_code == 202

    # Directly execute worker jobs with patched SessionLocal
    with patch("app.services.handoff_service.SessionLocal", TestingSessionLocal):
        from app.services.handoff_service import (
            execute_discharge_synthesis_job,
            execute_handoff_synthesis_job,
        )

        res_h = execute_handoff_synthesis_job(
            patient_id=test_inpatient_record.patient_id,
            framework="ipass",
            handoff_type="shift_change",
        )
        assert res_h["status"] == "completed"
        assert "HDF-" in res_h["handoff_id"]

        res_d = execute_discharge_synthesis_job(
            patient_id=test_inpatient_record.patient_id,
            disposition="home_self_care",
        )
        assert res_d["status"] == "completed"
        assert "DIS-" in res_d["discharge_id"]


def test_fhir_r4_composition_and_communication_export(
    client: TestClient,
    test_inpatient_record: Patient,
    db_session: Session,
):
    """Test exporting discharge protocol as FHIR R4 Composition and handoff as FHIR Communication."""
    headers, _ = get_auth_headers(client, role=UserRole.ADMIN, email="admin_fhir_trans@hospital.org")

    # Create and sign off discharge protocol
    d_resp = client.post(
        f"/api/v1/patients/{test_inpatient_record.patient_id}/discharge-protocols",
        json={
            "hospital_course_summary": "Resolved acute pulmonary congestion with IV furosemide.",
            "primary_discharge_diagnosis": "Congestive Heart Failure Exacerbation",
            "disposition": "home_self_care",
        },
        headers=headers,
    )
    discharge_id = d_resp.json()["discharge_id"]

    # 1. Export FHIR Composition
    comp_resp = client.get(f"/api/v1/fhir/Composition/{discharge_id}", headers=headers)
    assert comp_resp.status_code == 200
    fhir_comp = comp_resp.json()
    assert fhir_comp["resourceType"] == "Composition"
    assert fhir_comp["id"] == discharge_id
    assert fhir_comp["type"]["coding"][0]["code"] == "18842-5"
    assert len(fhir_comp["section"]) >= 2

    # Create clinical handoff
    h_resp = client.post(
        f"/api/v1/patients/{test_inpatient_record.patient_id}/handoffs",
        json={
            "framework": "ipass",
            "handoff_type": "unit_transfer",
            "illness_severity": "stable",
            "summary": "Transfer to telemetry step-down unit.",
        },
        headers=headers,
    )
    handoff_id = h_resp.json()["handoff_id"]

    # 2. Export FHIR Communication
    comm_resp = client.get(f"/api/v1/fhir/Communication/{handoff_id}", headers=headers)
    assert comm_resp.status_code == 200
    fhir_comm = comm_resp.json()
    assert fhir_comm["resourceType"] == "Communication"
    assert fhir_comm["id"] == handoff_id
    assert len(fhir_comm["payload"]) >= 1


def test_rbac_and_patient_isolation(
    client: TestClient,
    test_inpatient_record: Patient,
    secondary_patient_record: Patient,
    db_session: Session,
):
    """Test RBAC preventing unauthorized patient access to shift handoffs or cross-patient discharge data."""
    beatrice_headers, _ = get_auth_headers(
        client,
        role=UserRole.PATIENT,
        email=test_inpatient_record.email,
        name="Beatrice Holloway",
    )

    # Beatrice CANNOT create shift handoffs
    resp = client.post(
        f"/api/v1/patients/{test_inpatient_record.patient_id}/handoffs",
        json={"framework": "ipass", "summary": "Unauthorized"},
        headers=beatrice_headers,
    )
    assert resp.status_code == 403

    # Beatrice CANNOT create discharge protocols
    resp = client.post(
        f"/api/v1/patients/{test_inpatient_record.patient_id}/discharge-protocols",
        json={
            "hospital_course_summary": "Unauthorized",
            "primary_discharge_diagnosis": "Unauthorized",
        },
        headers=beatrice_headers,
    )
    assert resp.status_code == 403

    # Beatrice CANNOT view Julian's discharge protocols
    resp = client.get(
        f"/api/v1/patients/{secondary_patient_record.patient_id}/discharge-protocols",
        headers=beatrice_headers,
    )
    assert resp.status_code == 403
