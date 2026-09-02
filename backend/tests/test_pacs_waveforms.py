from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.pacs_waveforms import (
    ArrhythmiaEventType,
    ClinicianReviewStatus,
    DICOMModality,
)
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import Gender, PatientStatus
from app.schemas.user import UserRole


@pytest.fixture
def auth_radiologist_headers(db_session: Session):
    rad = db_session.query(User).filter(User.email == "radiologist.pacs@hospital.org").first()
    if not rad:
        rad = User(
            email="radiologist.pacs@hospital.org",
            name="Dr. Allison Cameron, MD",
            password_hash="mockradhash",
            role=UserRole.DOCTOR,
            is_active=True,
            default_facility_id="FAC-METRO-MAIN",
        )
        db_session.add(rad)
        db_session.commit()
        db_session.refresh(rad)
    token = create_access_token(subject=str(rad.id), role=rad.role.value)
    return {"Authorization": f"Bearer {token}"}, rad


@pytest.fixture
def setup_pacs_patient(db_session: Session):
    patient = db_session.query(Patient).filter(Patient.patient_id == "PAT-PACS-001").first()
    if not patient:
        patient = Patient(
            patient_id="PAT-PACS-001",
            first_name="Eleanor",
            last_name="Vance",
            date_of_birth=date(1979, 7, 24),
            gender=Gender.FEMALE,
            status=PatientStatus.ACTIVE,
            facility_id="FAC-METRO-MAIN",
        )
        db_session.add(patient)
        db_session.commit()
        db_session.refresh(patient)
    return patient


def test_create_and_query_dicom_studies_qido(
    client: TestClient, auth_radiologist_headers, setup_pacs_patient, db_session: Session
):
    headers, _ = auth_radiologist_headers
    patient = setup_pacs_patient

    create_payload = {
        "patient_id": patient.patient_id,
        "study_description": "High-Resolution Chest CT with Contrast",
        "modality": "CT",
        "body_site": "CHEST",
        "referring_physician": "Dr. Gregory House, MD",
        "performing_institution": "MetroHealth Advanced Imaging",
    }

    create_resp = client.post("/api/v1/pacs/studies", json=create_payload, headers=headers)
    assert create_resp.status_code == 201
    study_data = create_resp.json()
    assert study_data["study_instance_uid"].startswith("1.2.840.113619.2.55.3.")
    assert len(study_data["series_list"]) >= 1
    assert len(study_data["series_list"][0]["instances"]) >= 1

    # QIDO-RS Query
    query_resp = client.get(f"/api/v1/pacs/studies?patient_id={patient.patient_id}&modality=CT", headers=headers)
    assert query_resp.status_code == 200
    query_data = query_resp.json()
    assert query_data["total"] >= 1
    assert any(s["study_description"] == "High-Resolution Chest CT with Contrast" for s in query_data["studies"])


def test_get_dicom_study_metadata_wado(
    client: TestClient, auth_radiologist_headers, setup_pacs_patient, db_session: Session
):
    headers, _ = auth_radiologist_headers
    patient = setup_pacs_patient

    from app.services.pacs_waveform_service import PACSWaveformService
    study = PACSWaveformService.create_dicom_study(
        db=db_session,
        patient_id=patient.patient_id,
        study_description="Brain MRI Diffusion Sequence",
        modality=DICOMModality.MR,
        body_site="HEAD_BRAIN",
    )

    resp = client.get(f"/api/v1/pacs/studies/{study.study_instance_uid}/metadata", headers=headers)
    assert resp.status_code == 200
    meta = resp.json()
    assert meta["0020000D"]["Value"][0] == study.study_instance_uid
    assert meta["00080060"]["Value"][0] == "MR"
    assert len(meta["Series"]) >= 1
    assert len(meta["Series"][0]["Instances"]) >= 1


def test_review_ai_lesion_finding(
    client: TestClient, auth_radiologist_headers, setup_pacs_patient, db_session: Session
):
    headers, rad = auth_radiologist_headers
    patient = setup_pacs_patient

    from app.services.pacs_waveform_service import PACSWaveformService
    study = PACSWaveformService.create_dicom_study(
        db=db_session,
        patient_id=patient.patient_id,
        study_description="Thoracic CT Angiogram",
        modality=DICOMModality.CT,
        body_site="CHEST",
    )

    finding = study.series_list[0].instances[0].ai_findings[0]
    assert finding.clinician_review_status == ClinicianReviewStatus.PENDING_REVIEW

    review_payload = {
        "status": "confirmed",
        "review_notes": "Confirmed consolidation in right lower lobe consistent with focal pneumonia.",
    }

    resp = client.post(f"/api/v1/pacs/findings/{finding.finding_id}/review", json=review_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["clinician_review_status"] == "confirmed"
    assert data["reviewed_by_user_id"] == rad.id
    assert "consistent with focal pneumonia" in data["review_notes"]


def test_ingest_ecg_session_and_stemi_alert_trigger(
    client: TestClient, auth_radiologist_headers, setup_pacs_patient, db_session: Session
):
    headers, _ = auth_radiologist_headers
    patient = setup_pacs_patient

    session_payload = {
        "patient_id": patient.patient_id,
        "rhythm_state": "stemi_elevation",
        "heart_rate_bpm": 105,
        "lead_configuration": "12_LEAD",
        "sample_rate_hz": 250,
        "duration_seconds": 10,
    }

    resp = client.post("/api/v1/pacs/waveforms/sessions", json=session_payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["current_rhythm_state"] == "stemi_elevation"
    assert len(data["multi_lead_samples_json"]["I"]) == 2500  # 250 Hz * 10s
    assert len(data["multi_lead_samples_json"]["V3"]) == 2500
    assert len(data["alerts"]) >= 1
    alert = data["alerts"][0]
    assert alert["severity"] == "critical"
    assert alert["event_type"] == "stemi_elevation"
    assert alert["st_elevation_mm"] is not None


def test_arrhythmia_alert_debouncing_cooldown(
    client: TestClient, auth_radiologist_headers, setup_pacs_patient, db_session: Session
):
    headers, _ = auth_radiologist_headers
    patient = setup_pacs_patient

    session_payload = {
        "patient_id": patient.patient_id,
        "rhythm_state": "ventricular_tachycardia",
        "heart_rate_bpm": 180,
    }

    # First session -> triggers new critical alert
    resp1 = client.post("/api/v1/pacs/waveforms/sessions", json=session_payload, headers=headers)
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert len(data1["alerts"]) == 1

    # Second session immediately after -> debouncing prevents duplicate alert creation
    resp2 = client.post("/api/v1/pacs/waveforms/sessions", json=session_payload, headers=headers)
    assert resp2.status_code == 201
    data2 = resp2.json()
    assert len(data2["alerts"]) == 0  # No duplicate alert storm


def test_acknowledge_arrhythmia_alert(
    client: TestClient, auth_radiologist_headers, setup_pacs_patient, db_session: Session
):
    headers, rad = auth_radiologist_headers
    patient = setup_pacs_patient

    from app.services.pacs_waveform_service import PACSWaveformService
    session = PACSWaveformService.ingest_ecg_session(
        db=db_session,
        patient_id=patient.patient_id,
        rhythm_state=ArrhythmiaEventType.ATRIAL_FIBRILLATION,
        heart_rate_bpm=135,
    )
    alert = session.alerts[0]

    ack_payload = {
        "clinician_action_taken": "Bedside cardiology notified. IV Diltiazem 20mg administered for rate control.",
        "status": "acknowledged",
    }

    resp = client.post(f"/api/v1/pacs/waveforms/alerts/{alert.alert_id}/acknowledge", json=ack_payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "acknowledged"
    assert data["acknowledged_by_user_id"] == rad.id
    assert "IV Diltiazem 20mg" in data["clinician_action_taken"]
