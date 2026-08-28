import pytest
from datetime import datetime, timezone
from fastapi import status
from fastapi.testclient import TestClient

from app.models.encounter import Encounter
from app.models.patient import Patient
from app.schemas.encounter import EncounterCreate, EncounterStatus, EncounterType
from app.services.encounter_service import create_encounter
from app.services.fhir_mapper_service import FHIREncounterMapper


def test_internal_encounter_to_fhir_encounter_mapping(db_session, test_patient, test_doctor_user):
    """Verify mapping internal Encounter to FHIR R4 Encounter resource."""
    enc_in = EncounterCreate(
        encounter_type=EncounterType.INITIAL_CONSULTATION,
        chief_complaint="Chest pain on exertion",
        clinical_notes="Patient reports 2-week history of retrosternal pressure.",
        assessment="Angina Pectoris",
        plan="Prescribe Nitroglycerin PRN, schedule stress test.",
        status=EncounterStatus.COMPLETED,
    )
    enc = create_encounter(db_session, test_patient.patient_id, enc_in, test_doctor_user.id)

    fhir_enc = FHIREncounterMapper.to_fhir(enc, test_patient)

    assert fhir_enc.resourceType == "Encounter"
    assert fhir_enc.id == enc.encounter_id
    assert fhir_enc.status == "finished"
    assert fhir_enc.subject.reference == f"Patient/{test_patient.patient_id}"
    assert fhir_enc.reasonCode[0].text == "Chest pain on exertion"
    assert len(fhir_enc.diagnosis) == 1
    assert fhir_enc.diagnosis[0].condition.display == "Angina Pectoris"


def test_export_fhir_encounter_endpoint(client: TestClient, db_session, test_admin, test_patient, test_doctor_user):
    """Verify GET /api/v1/fhir/Encounter/{encounter_id} endpoint."""
    enc_in = EncounterCreate(
        encounter_type=EncounterType.FOLLOW_UP,
        chief_complaint="Hypertension follow up",
        clinical_notes="Blood pressure stable on current regimen.",
        assessment="Essential Hypertension",
        plan="Continue Lisinopril 10mg.",
    )
    enc = create_encounter(db_session, test_patient.patient_id, enc_in, test_doctor_user.id)

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/fhir/Encounter/{enc.encounter_id}", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["resourceType"] == "Encounter"
    assert data["id"] == enc.encounter_id
    assert data["status"] == "finished"
    assert data["subject"]["reference"] == f"Patient/{test_patient.patient_id}"
