import pytest
from datetime import datetime, timezone
from fastapi import status
from fastapi.testclient import TestClient

from app.schemas.encounter import EncounterCreate, EncounterType
from app.services.encounter_service import create_encounter
from app.services.fhir_mapper_service import FHIRConditionMapper


def test_fhir_condition_mapping(test_patient):
    """Verify construction of FHIR R4 Condition from diagnosis data."""
    cond = FHIRConditionMapper.to_fhir(
        condition_id="COND-TEST-001",
        diagnosis_title="Type 2 Diabetes Mellitus",
        patient_id=test_patient.patient_id,
        encounter_id="ENC-20260828-0001",
        clinical_status="active",
        recorded_date=datetime.now(timezone.utc),
        notes="HbA1c 7.8% on Metformin",
    )

    assert cond.resourceType == "Condition"
    assert cond.id == "COND-TEST-001"
    assert cond.clinicalStatus.coding[0].code == "active"
    assert cond.code.text == "Type 2 Diabetes Mellitus"
    assert cond.subject.reference == f"Patient/{test_patient.patient_id}"
    assert cond.encounter.reference == "Encounter/ENC-20260828-0001"
    assert len(cond.note) == 1


def test_export_fhir_condition_endpoint(client: TestClient, db_session, test_admin, test_patient, test_doctor_user):
    """Verify GET /api/v1/fhir/Condition/{condition_id} endpoint."""
    enc_in = EncounterCreate(
        encounter_type=EncounterType.INITIAL_CONSULTATION,
        chief_complaint="Polyuria and fatigue",
        clinical_notes="Fasting blood sugar elevated.",
        assessment="Type 2 Diabetes Mellitus",
        plan="Start Metformin 500mg daily.",
    )
    enc = create_encounter(db_session, test_patient.patient_id, enc_in, test_doctor_user.id)

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/fhir/Condition/{enc.encounter_id}", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["resourceType"] == "Condition"
    assert data["subject"]["reference"] == f"Patient/{test_patient.patient_id}"
    assert data["code"]["text"] == "Type 2 Diabetes Mellitus"
