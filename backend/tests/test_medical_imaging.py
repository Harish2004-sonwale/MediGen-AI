"""Integration and Unit Tests for Medical Imaging AI, Multimodal Diagnostics & Radiology Workflow.

Phase 9.0.18: Medical Imaging AI, Multimodal Diagnostics & Radiology Workflow.
"""

from datetime import datetime, timezone
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.imaging import ImagingAsset, ImagingFinding, ImagingStudy, RadiologyReport
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.patient import Gender, PatientStatus


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "imaging_radiologist@hospital.org",
    name: str = "Dr. Imaging Specialist",
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



# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_imaging_patient(db_session: Session) -> Patient:
    """Create a unique patient for imaging workflow tests."""
    patient = Patient(
        patient_id="PAT-IMG-001",
        first_name="Eleanor",
        last_name="Vance",
        date_of_birth=datetime(1975, 4, 12).date(),
        gender=Gender.FEMALE,
        email="eleanor.vance@example.com",
        phone="+1-555-0199",
        status=PatientStatus.ACTIVE,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient


@pytest.fixture
def other_imaging_patient(db_session: Session) -> Patient:
    """Create a second patient to test isolation."""
    patient = Patient(
        patient_id="PAT-IMG-002",
        first_name="Arthur",
        last_name="Pendelton",
        date_of_birth=datetime(1960, 8, 22).date(),
        gender=Gender.MALE,
        email="arthur.p@example.com",
        phone="+1-555-0198",
        status=PatientStatus.ACTIVE,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient




# =============================================================================
# 1. STUDY CREATION & INGESTION TESTS
# =============================================================================

def test_create_imaging_study_success(
    client: TestClient,
    test_imaging_patient: Patient,
):
    """Verify authorized clinician can ingest an imaging study."""
    doc_headers, _ = get_auth_headers(client, UserRole.DOCTOR, "doc_ingest@hospital.org", "Dr. Ingest")
    payload = {
        "patient_id": test_imaging_patient.patient_id,
        "modality": "XRAY",
        "body_site": "CHEST",
        "study_description": "CXR 2 Views PA and Lateral for acute dyspnea and cough",
        "accession_number": "ACC-TEST-001",
        "performing_department": "Radiology Department",
        "referring_provider": "Dr. Gregory House",
        "status": "ORDERED",
        "source": "PACS_IMPORT",
    }
    response = client.post(
        f"/api/v1/patients/{test_imaging_patient.patient_id}/imaging/studies",
        json=payload,
        headers=doc_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["accession_number"] == "ACC-TEST-001"
    assert data["modality"] == "XRAY"
    assert data["body_site"] == "CHEST"
    assert data["study_id"].startswith("STU-")
    assert len(data["provenance_hash"]) == 64


def test_imaging_study_patient_isolation(
    client: TestClient,
    test_imaging_patient: Patient,
    other_imaging_patient: Patient,
):
    """Verify PATIENT role cannot access another patient's imaging studies."""
    pat_headers, _ = get_auth_headers(client, UserRole.PATIENT, test_imaging_patient.email, "Eleanor Vance")
    # Attempt to list another patient's studies
    response = client.get(
        f"/api/v1/patients/{other_imaging_patient.patient_id}/imaging/studies",
        headers=pat_headers,
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# 2. IMAGE ASSETS & MULTIMODAL AI ANALYSIS TESTS
# =============================================================================

def test_add_asset_and_run_ai_analysis(
    client: TestClient,
    test_imaging_patient: Patient,
):
    """Verify asset attachment and deterministic AI multimodal interpretation."""
    doc_headers, _ = get_auth_headers(client, UserRole.DOCTOR, "doc_neuro@hospital.org", "Dr. Neuro")

    # 1. Create study
    study_res = client.post(
        f"/api/v1/patients/{test_imaging_patient.patient_id}/imaging/studies",
        json={
            "patient_id": test_imaging_patient.patient_id,
            "modality": "CT",
            "body_site": "HEAD_BRAIN",
            "study_description": "Non-contrast Head CT for sudden onset severe headache and trauma fall",
            "accession_number": "ACC-HEAD-001",
            "status": "ORDERED",
        },
        headers=doc_headers,
    )
    assert study_res.status_code == status.HTTP_201_CREATED
    study_id = study_res.json()["study_id"]

    # 2. Attach asset
    asset_res = client.post(
        f"/api/v1/imaging/studies/{study_id}/assets",
        json={
            "series_instance_uid": "1.2.840.113619.2.55.3.1",
            "sop_instance_uid": "1.2.840.113619.2.55.3.1.1",
            "series_number": 1,
            "instance_number": 1,
            "series_description": "Axial Brain 5mm Non-Contrast",
            "modality": "CT",
            "body_site": "HEAD_BRAIN",
            "mime_type": "image/png",
            "file_size_bytes": 1048576,
            "storage_path": "/storage/imaging/head_ct_01.png",
        },
        headers=doc_headers,
    )
    assert asset_res.status_code == status.HTTP_201_CREATED
    assert asset_res.json()["asset_id"].startswith("AST-")

    # 3. Run AI interpretation
    ai_res = client.post(
        f"/api/v1/imaging/studies/{study_id}/analyze",
        headers=doc_headers,
    )
    assert ai_res.status_code == status.HTTP_200_OK
    ai_data = ai_res.json()
    assert ai_data["status"] == "COMPLETED"
    assert ai_data["findings_count"] >= 1
    assert ai_data["critical_findings_count"] >= 1  # Severe headache / trauma triggers critical finding
    assert any(f["finding_type"] == "POSSIBLE_HEMORRHAGE" for f in ai_data["findings"])

    # Verify draft report was generated
    assert ai_data["draft_report"] is not None
    assert ai_data["draft_report"]["status"] == "AI_ASSISTED"
    assert "POTENTIALLY CRITICAL AI-ASSISTED FINDING" in ai_data["draft_report"]["critical_findings_summary"]


# =============================================================================
# 3. CLINICIAN REVIEW & REPORT SIGN-OFF WORKFLOW
# =============================================================================

def test_radiology_report_lifecycle_and_signoff(
    client: TestClient,
    test_imaging_patient: Patient,
):
    """Test full report editing, radiologist review, sign-off, and amendment."""
    doc_headers, _ = get_auth_headers(client, UserRole.DOCTOR, "doc_pulm@hospital.org", "Dr. Pulm")
    pat_headers, _ = get_auth_headers(client, UserRole.PATIENT, test_imaging_patient.email, "Eleanor Vance")

    # 1. Ingest chest X-ray study
    study_res = client.post(
        f"/api/v1/patients/{test_imaging_patient.patient_id}/imaging/studies",
        json={
            "patient_id": test_imaging_patient.patient_id,
            "modality": "XRAY",
            "body_site": "CHEST",
            "study_description": "CXR 2 Views for productive cough and fever",
            "accession_number": "ACC-CXR-002",
        },
        headers=doc_headers,
    )
    study_id = study_res.json()["study_id"]

    # 2. Run AI analysis
    ai_res = client.post(
        f"/api/v1/imaging/studies/{study_id}/analyze",
        headers=doc_headers,
    )
    assert ai_res.status_code == status.HTTP_200_OK
    draft_report = ai_res.json()["draft_report"]
    report_id = draft_report["report_id"]
    findings = ai_res.json()["findings"]
    first_finding_id = findings[0]["finding_id"]

    # 3. Clinician reviews individual finding
    review_res = client.post(
        f"/api/v1/imaging/findings/{first_finding_id}/review",
        json={
            "review_status": "confirmed",
            "review_notes": "Agreed with right lower lobe infiltrate.",
        },
        headers=doc_headers,
    )
    assert review_res.status_code == status.HTTP_200_OK
    assert review_res.json()["clinician_review_status"] == "confirmed"
    assert review_res.json()["finding_nature"] == "CLINICIAN_CONFIRMED_FINDING"

    # 4. Edit draft report narrative
    update_res = client.put(
        f"/api/v1/imaging/reports/{report_id}",
        json={
            "clinical_indication": "Evaluated for right lower lobe community acquired pneumonia",
            "impression": "1. Right lower lobe consolidation consistent with bacterial pneumonia.\n2. Small reactive pleural effusion.",
            "recommendations": "Begin empiric oral antibiotics and follow up in 2 weeks.",
        },
        headers=doc_headers,
    )
    assert update_res.status_code == status.HTTP_200_OK
    assert "bacterial pneumonia" in update_res.json()["impression"]

    # 5. Submit for Radiologist review
    sub_res = client.post(
        f"/api/v1/imaging/reports/{report_id}/submit-review",
        headers=doc_headers,
    )
    assert sub_res.status_code == status.HTTP_200_OK
    assert sub_res.json()["status"] == "RADIOLOGIST_REVIEW"

    # 6. Patient cannot finalize report
    pat_fin = client.post(
        f"/api/v1/imaging/reports/{report_id}/finalize",
        json={"signature_notes": "Attempted patient finalization", "confirm_accuracy": True},
        headers=pat_headers,
    )
    assert pat_fin.status_code == status.HTTP_403_FORBIDDEN

    # 7. Doctor signs off and finalizes report
    doc_fin = client.post(
        f"/api/v1/imaging/reports/{report_id}/finalize",
        json={"signature_notes": "Electronically signed after full radiologic image review.", "confirm_accuracy": True},
        headers=doc_headers,
    )
    assert doc_fin.status_code == status.HTTP_200_OK
    fin_data = doc_fin.json()
    assert fin_data["status"] == "FINALIZED"
    assert fin_data["signed_by_user_id"] is not None
    assert fin_data["signed_at"] is not None

    # 8. Create report amendment
    amend_res = client.post(
        f"/api/v1/imaging/reports/{report_id}/amend",
        json={
            "amendment_reason": "Addendum to note clearing on comparative review with prior clinic film.",
            "amended_impression": "1. Mild resolving right lower lobe infiltrate.\n2. No discrete effusion.",
        },
        headers=doc_headers,
    )
    assert amend_res.status_code == status.HTTP_200_OK
    amend_data = amend_res.json()
    assert amend_data["status"] == "FINALIZED"
    assert amend_data["amended_from_report_id"] is not None
    assert "Addendum" in amend_data["amendment_reason"]


# =============================================================================
# 4. TIMELINE & FHIR R4 INTEROPERABILITY TESTS
# =============================================================================

def test_imaging_timeline_and_fhir_interoperability(
    client: TestClient,
    test_imaging_patient: Patient,
):
    """Test longitudinal timeline compilation and FHIR R4 resources export."""
    doc_headers, _ = get_auth_headers(client, UserRole.DOCTOR, "doc_timeline@hospital.org", "Dr. Timeline")

    # Ingest a study first
    client.post(
        f"/api/v1/patients/{test_imaging_patient.patient_id}/imaging/studies",
        json={
            "patient_id": test_imaging_patient.patient_id,
            "modality": "XRAY",
            "body_site": "CHEST",
            "study_description": "Baseline Chest X-Ray for Annual Exam",
            "accession_number": "ACC-BASE-001",
        },
        headers=doc_headers,
    )

    # 1. Retrieve longitudinal imaging timeline
    time_res = client.get(
        f"/api/v1/patients/{test_imaging_patient.patient_id}/imaging/timeline",
        headers=doc_headers,
    )
    assert time_res.status_code == status.HTTP_200_OK
    time_data = time_res.json()
    assert time_data["patient_id"] == test_imaging_patient.patient_id
    assert time_data["total_studies"] >= 1

    study_id = time_data["items"][0]["study_id"]

    # 2. Export FHIR ImagingStudy
    fhir_study_res = client.get(
        f"/api/v1/fhir/ImagingStudy/{study_id}",
        headers=doc_headers,
    )
    assert fhir_study_res.status_code == status.HTTP_200_OK
    fhir_study = fhir_study_res.json()
    assert fhir_study["resourceType"] == "ImagingStudy"
    assert fhir_study["subject"]["reference"] == f"Patient/{test_imaging_patient.patient_id}"

    # 3. Analyze and export FHIR DiagnosticReport for radiology report
    ai_res = client.post(f"/api/v1/imaging/studies/{study_id}/analyze", headers=doc_headers)
    assert ai_res.status_code == status.HTTP_200_OK
    report_id = ai_res.json()["draft_report"]["report_id"]

    fhir_rep_res = client.get(
        f"/api/v1/fhir/ImagingReport/{report_id}",
        headers=doc_headers,
    )
    assert fhir_rep_res.status_code == status.HTTP_200_OK
    fhir_rep = fhir_rep_res.json()
    assert fhir_rep["resourceType"] == "DiagnosticReport"
    assert fhir_rep["category"][0]["coding"][0]["code"] == "RAD"


# =============================================================================
# 5. ASYNC TASK QUEUE TEST
# =============================================================================

def test_enqueue_async_imaging_task(
    client: TestClient,
    test_imaging_patient: Patient,
):
    """Verify asynchronous task submission for heavy imaging analysis."""
    doc_headers, _ = get_auth_headers(client, UserRole.DOCTOR, "doc_async@hospital.org", "Dr. Async")

    # Create study
    study_res = client.post(
        f"/api/v1/patients/{test_imaging_patient.patient_id}/imaging/studies",
        json={
            "patient_id": test_imaging_patient.patient_id,
            "modality": "ULTRASOUND",
            "body_site": "ABDOMEN",
            "study_description": "Abdominal ultrasound for right upper quadrant pain",
            "accession_number": "ACC-US-003",
        },
        headers=doc_headers,
    )
    study_id = study_res.json()["study_id"]

    # Enqueue task
    task_res = client.post(
        f"/api/v1/imaging/tasks/studies/{study_id}/analyze",
        headers=doc_headers,
    )
    assert task_res.status_code == status.HTTP_202_ACCEPTED
    task_data = task_res.json()
    assert task_data["task_id"].startswith("TASK-")
    assert task_data["task_type"] == "imaging_analysis"
