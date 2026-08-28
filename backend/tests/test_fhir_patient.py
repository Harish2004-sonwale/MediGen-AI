import pytest
from datetime import date
from fastapi import status
from fastapi.testclient import TestClient

from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import Gender, PatientStatus
from app.services.fhir_mapper_service import FHIRPatientMapper


def test_internal_patient_to_fhir_patient_mapping(db_session, test_patient):
    """Verify bidirectional mapping from internal Patient model to FHIR R4 Patient."""
    fhir_patient = FHIRPatientMapper.to_fhir(test_patient)

    assert fhir_patient.resourceType == "Patient"
    assert fhir_patient.id == test_patient.patient_id
    assert fhir_patient.active is True
    assert len(fhir_patient.name) == 1
    assert fhir_patient.name[0].family == test_patient.last_name
    assert fhir_patient.name[0].given == [test_patient.first_name]
    assert fhir_patient.gender == "male"
    assert fhir_patient.birthDate == test_patient.date_of_birth.isoformat()
    assert any(tc.system == "phone" and tc.value == test_patient.phone for tc in fhir_patient.telecom)
    assert any(tc.system == "email" and tc.value == test_patient.email for tc in fhir_patient.telecom)


def test_fhir_patient_to_internal_patient_mapping():
    """Verify mapping from FHIR R4 Patient JSON payload to internal PatientCreate schema."""
    fhir_data = {
        "resourceType": "Patient",
        "id": "PAT-TEST-001",
        "active": True,
        "name": [{"family": "Smith", "given": ["Jane"]}],
        "gender": "female",
        "birthDate": "1992-05-15",
        "telecom": [
            {"system": "phone", "value": "+1-555-0199"},
            {"system": "email", "value": "jane.smith@example.com"},
        ],
        "address": [{"text": "123 Medical Center Dr, Boston, MA"}],
    }

    patient_create = FHIRPatientMapper.to_internal(fhir_data)

    assert patient_create.first_name == "Jane"
    assert patient_create.last_name == "Smith"
    assert patient_create.gender == Gender.FEMALE
    assert patient_create.date_of_birth == date(1992, 5, 15)
    assert patient_create.phone == "+1-555-0199"
    assert patient_create.email == "jane.smith@example.com"
    assert patient_create.status == PatientStatus.ACTIVE


def test_export_fhir_patient_endpoint(client: TestClient, db_session, test_admin, test_patient):
    """Verify GET /api/v1/fhir/Patient/{patient_id} returns valid FHIR R4 Patient."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/fhir/Patient/{test_patient.patient_id}", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["resourceType"] == "Patient"
    assert data["id"] == test_patient.patient_id
    assert data["name"][0]["family"] == test_patient.last_name
    assert data["gender"] == "male"


def test_export_fhir_patient_not_found(client: TestClient, db_session, test_admin):
    """Verify GET /api/v1/fhir/Patient/{patient_id} returns 404 for nonexistent patient."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/fhir/Patient/PAT-NONEXISTENT-999", headers=headers)
    assert res.status_code == status.HTTP_404_NOT_FOUND
