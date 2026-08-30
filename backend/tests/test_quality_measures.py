"""Automated test suite for Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting.

Phase 9.0.14: Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting Engine.
"""

from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.care_plan import CarePlan
from app.models.care_task import CareTask
from app.models.encounter import Encounter
from app.models.order import ClinicalOrder, DiagnosticResult
from app.models.patient import Patient
from app.models.user import UserRole
from app.models.vital import VitalTelemetry
from app.schemas.patient import Gender, PatientStatus
from tests.conftest import TestingSessionLocal


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "quality_doc@hospital.org",
    name: str = "Dr. Quality Physician",
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


def _create_patient(db: Session, identifier: str, email: str | None = None) -> Patient:
    p = Patient(
        patient_id=identifier,
        first_name="Eleanor",
        last_name="Vance",
        date_of_birth=date(1958, 4, 12),
        gender=Gender.FEMALE,
        status=PatientStatus.ACTIVE,
        email=email or f"{identifier.lower()}@hospital.org",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p



def test_quality_measures_seeding_and_list(client: TestClient, db_session: Session):
    """Verify default CQM measure seeding and filtering by domain."""
    doc_headers, _ = get_auth_headers(client, UserRole.DOCTOR, "doc_qm_1@example.com", "Dr. Quality")

    res = client.get("/api/v1/quality/measures", headers=doc_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 5
    measure_ids = [m["measure_id"] for m in data["items"]]
    assert "CQM-001-DM-HBA1C" in measure_ids
    assert "CQM-002-HTN-BP" in measure_ids
    assert "CQM-003-TOC-MEDREC" in measure_ids
    assert "CQM-004-CP-ADHERENCE" in measure_ids
    assert "CQM-005-CRIT-LAB" in measure_ids

    # Filter by domain
    res_domain = client.get("/api/v1/quality/measures?domain=chronic_disease_management", headers=doc_headers)
    assert res_domain.status_code == 200
    for item in res_domain.json()["items"]:
        assert item["domain"] == "chronic_disease_management"


def test_patient_quality_evaluation_diabetes_and_hypertension(client: TestClient, db_session: Session):
    """Verify patient-level CQM evaluation for diabetes control and blood pressure control."""
    doc_headers, doc_id = get_auth_headers(client, UserRole.DOCTOR, "doc_qm_eval@example.com", "Dr. Evaluator")
    patient = _create_patient(db_session, "PAT-CQM-001")

    # 1. Add encounter with Diabetes and Hypertension diagnoses
    enc = Encounter(
        encounter_id="ENC-CQM-001",
        patient_id=patient.id,
        attending_user_id=doc_id,
        chief_complaint="Essential hypertension and Type 2 diabetes mellitus",
        assessment="Essential hypertension (I10), Type 2 diabetes mellitus without complications (E11.9)",
        clinical_notes="Patient undergoing routine chronic care assessment.",
    )
    db_session.add(enc)

    # 2. Add controlled HbA1c result (7.2% < 8.0%)
    order = ClinicalOrder(
        order_id="ORD-CQM-001",
        patient_id=patient.id,
        ordering_user_id=doc_id,
        order_category="laboratory",
        order_type="glycated_hemoglobin",
        clinical_indication="Diabetes monitoring",
    )
    db_session.add(order)
    db_session.flush()

    res_lab = DiagnosticResult(
        result_id="RES-CQM-001",
        order_id=order.id,
        patient_id=patient.id,
        test_name="Hemoglobin A1c",
        numeric_value=7.2,
        unit_of_measure="%",
        abnormal_flag="normal",
        findings_summary="Adequate glycemic control.",
    )
    db_session.add(res_lab)

    # 3. Add uncontrolled blood pressure (155/95 mmHg)
    vital = VitalTelemetry(
        reading_id="VIT-CQM-001",
        patient_id=patient.id,
        systolic_bp=155,
        diastolic_bp=95,
        heart_rate=78,
        measured_at=datetime.now(timezone.utc),
    )
    db_session.add(vital)
    db_session.commit()


    # Evaluate measures
    eval_res = client.post(f"/api/v1/quality/patients/{patient.patient_id}/evaluate", headers=doc_headers)
    assert eval_res.status_code == 200
    results = eval_res.json()["items"]

    dm_res = next(r for r in results if r["measure_code"] == "CQM-001-DM-HBA1C")
    assert dm_res["is_eligible"] is True
    assert dm_res["is_numerator_compliant"] is True
    assert dm_res["compliance_status"] == "compliant"
    assert dm_res["evidence_json"]["latest_hba1c_value"] == 7.2

    htn_res = next(r for r in results if r["measure_code"] == "CQM-002-HTN-BP")
    assert htn_res["is_eligible"] is True
    assert htn_res["is_numerator_compliant"] is False
    assert htn_res["compliance_status"] == "non_compliant"
    assert "155/95" in htn_res["gap_reason"]


def test_care_gap_detection_and_care_task_creation(client: TestClient, db_session: Session):
    """Verify care gap detection and conversion into an active CareTask."""
    doc_headers, doc_id = get_auth_headers(client, UserRole.DOCTOR, "doc_qm_gaps@example.com", "Dr. GapManager")
    patient = _create_patient(db_session, "PAT-CQM-002")

    # Add diagnosis for diabetes without HbA1c lab (missing data gap)
    enc = Encounter(
        encounter_id="ENC-CQM-002",
        patient_id=patient.id,
        attending_user_id=doc_id,
        chief_complaint="Type 2 diabetes mellitus follow-up",
        assessment="Type 2 diabetes mellitus",
        clinical_notes="Newly established diabetic patient.",
    )

    db_session.add(enc)
    db_session.commit()

    # Evaluate
    client.post(f"/api/v1/quality/patients/{patient.patient_id}/evaluate", headers=doc_headers)

    # Fetch gaps
    gaps_res = client.get(f"/api/v1/quality/gaps?patient_id={patient.patient_id}", headers=doc_headers)
    assert gaps_res.status_code == 200
    gaps = gaps_res.json()["items"]
    assert len(gaps) >= 1
    dm_gap = next(g for g in gaps if g["measure_code"] == "CQM-001-DM-HBA1C")
    assert dm_gap["status"] == "open"
    assert dm_gap["severity"] == "HIGH"

    # Convert to CareTask
    task_res = client.post(f"/api/v1/quality/gaps/{dm_gap['gap_id']}/create-care-task", headers=doc_headers)
    assert task_res.status_code == 200
    updated_gap = task_res.json()
    assert updated_gap["status"] == "in_remediation"
    assert updated_gap["linked_care_task_id"] is not None

    # Verify CareTask in DB
    care_task = db_session.query(CareTask).filter(CareTask.id == updated_gap["linked_care_task_id"]).first()
    assert care_task is not None
    assert "CQM Remediation" in care_task.title



def test_compliance_report_generation_and_audit(client: TestClient, db_session: Session):
    """Verify population compliance audit report synthesis and data provenance tracking."""
    admin_headers, _ = get_auth_headers(client, UserRole.ADMIN, "admin_qm_rep@example.com", "Admin Quality Director")
    patient = _create_patient(db_session, "PAT-CQM-003")

    # Generate population report
    report_res = client.post(
        "/api/v1/quality/reports/generate",
        json={"title": "Q3 2026 Executive Compliance Audit", "report_scope": "organization"},
        headers=admin_headers,
    )
    assert report_res.status_code == 201
    rep_data = report_res.json()
    assert rep_data["report_id"].startswith("QRP-")
    assert "Q3 2026 Executive Compliance Audit" in rep_data["title"]
    assert rep_data["audit_metadata_json"] is not None
    assert rep_data["audit_metadata_json"]["provenance_hash"] is not None
    assert rep_data["audit_metadata_json"]["total_measures_evaluated"] >= 5

    # Retrieve report by ID
    get_res = client.get(f"/api/v1/quality/reports/{rep_data['report_id']}", headers=admin_headers)
    assert get_res.status_code == 200
    assert get_res.json()["report_id"] == rep_data["report_id"]


def test_quality_rbac_patient_isolation(client: TestClient, db_session: Session):
    """Verify RBAC and cross-patient isolation on quality endpoints."""
    doc_headers, _ = get_auth_headers(client, UserRole.DOCTOR, "doc_qm_rbac@example.com", "Dr. Isolation")
    pat_headers_1, pat_user_1_id = get_auth_headers(client, UserRole.PATIENT, "pat1_qm@example.com", "Patient One")
    pat_headers_2, pat_user_2_id = get_auth_headers(client, UserRole.PATIENT, "pat2_qm@example.com", "Patient Two")

    patient_1 = _create_patient(db_session, "PAT-CQM-ISO-1", email="pat1_qm@example.com")
    patient_2 = _create_patient(db_session, "PAT-CQM-ISO-2", email="pat2_qm@example.com")


    # Patient 1 can view own results
    res1 = client.get(f"/api/v1/quality/patients/{patient_1.patient_id}/results", headers=pat_headers_1)
    assert res1.status_code == 200

    # Patient 1 cannot view Patient 2's results
    res1_on_2 = client.get(f"/api/v1/quality/patients/{patient_2.patient_id}/results", headers=pat_headers_1)
    assert res1_on_2.status_code == 403

    # Patient cannot generate population reports
    rep_res = client.post("/api/v1/quality/reports/generate", json={}, headers=pat_headers_1)
    assert rep_res.status_code == 403


def test_fhir_measure_and_measure_report_export(client: TestClient, db_session: Session):
    """Verify FHIR R4 Measure and MeasureReport serialization."""
    doc_headers, _ = get_auth_headers(client, UserRole.DOCTOR, "doc_qm_fhir@example.com", "Dr. FHIR Quality")

    # 1. Export FHIR Measure
    m_res = client.get("/api/v1/fhir/Measure/CQM-001-DM-HBA1C", headers=doc_headers)
    assert m_res.status_code == 200
    m_fhir = m_res.json()
    assert m_fhir["resourceType"] == "Measure"
    assert m_fhir["id"] == "CQM-001-DM-HBA1C"
    assert "Diabetes" in m_fhir["title"]

    # 2. Export FHIR MeasureReport
    admin_headers, _ = get_auth_headers(client, UserRole.ADMIN, "admin_qm_fhir@example.com", "Admin FHIR")
    rep_res = client.post("/api/v1/quality/reports/generate", json={"title": "FHIR Test Report"}, headers=admin_headers)
    assert rep_res.status_code == 201
    rep_id = rep_res.json()["report_id"]

    mr_res = client.get(f"/api/v1/fhir/MeasureReport/{rep_id}", headers=doc_headers)
    assert mr_res.status_code == 200
    mr_fhir = mr_res.json()
    assert mr_fhir["resourceType"] == "MeasureReport"
    assert mr_fhir["id"] == rep_id
    assert len(mr_fhir["group"]) >= 5


def test_async_quality_calculation_task(client: TestClient, db_session: Session, monkeypatch):
    """Verify async task worker dispatch for quality calculations."""
    monkeypatch.setattr("app.services.quality_service.SessionLocal", TestingSessionLocal)

    doc_headers, _ = get_auth_headers(client, UserRole.DOCTOR, "doc_qm_async@example.com", "Dr. Async Quality")
    patient = _create_patient(db_session, "PAT-CQM-ASYNC-1")

    res = client.post(f"/api/v1/quality/tasks/calculate?patient_id={patient.patient_id}", headers=doc_headers)
    assert res.status_code == 202
    data = res.json()
    assert data["task_type"] == "quality_measure_calculation"
    assert data["status"] in ["queued", "running", "completed"]
