import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.models.patient import Patient
from app.models.encounter import Encounter
from app.services.patient_service import get_patient_by_patient_id


def test_import_fhir_patient_resource(client: TestClient, db_session, test_admin):
    """Verify POST /api/v1/fhir/import successfully creates a new internal patient from FHIR Patient."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "resourceType": "Patient",
        "name": [{"family": "Adams", "given": ["John"]}],
        "gender": "male",
        "birthDate": "1980-11-22",
        "telecom": [
            {"system": "phone", "value": "+1-555-4321"},
            {"system": "email", "value": "john.adams@example.com"},
        ],
        "address": [{"text": "742 Evergreen Terrace, Springfield"}],
    }

    res = client.post("/api/v1/fhir/import", json=payload, headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["success"] is True
    assert data["status"] == "created"
    assert data["resource_type"] == "Patient"
    assert data["internal_id"].startswith("PAT-")

    # Verify created in DB
    pat = get_patient_by_patient_id(db_session, data["internal_id"])
    assert pat is not None
    assert pat.first_name == "John"
    assert pat.last_name == "Adams"


def test_import_fhir_patient_update_existing(client: TestClient, db_session, test_admin, test_patient):
    """Verify importing FHIR Patient with existing ID updates the patient record."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "resourceType": "Patient",
        "id": test_patient.patient_id,
        "name": [{"family": "UpdatedLast", "given": [test_patient.first_name]}],
        "gender": "male",
        "birthDate": test_patient.date_of_birth.isoformat(),
        "telecom": [{"system": "phone", "value": "+1-555-9999"}],
    }

    res = client.post("/api/v1/fhir/import", json=payload, headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["success"] is True
    assert data["status"] == "updated"
    assert data["internal_id"] == test_patient.patient_id


def test_import_fhir_encounter(client: TestClient, db_session, test_admin, test_patient):
    """Verify POST /api/v1/fhir/import successfully creates an encounter for an existing patient."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "resourceType": "Encounter",
        "status": "finished",
        "subject": {"reference": f"Patient/{test_patient.patient_id}"},
        "reasonCode": [{"text": "Severe headache and dizziness"}],
        "diagnosis": [{"condition": {"display": "Migraine without aura"}}],
    }

    res = client.post("/api/v1/fhir/import", json=payload, headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["success"] is True
    assert data["status"] == "created"
    assert data["resource_type"] == "Encounter"
    assert data["internal_id"].startswith("ENC-")


def test_import_fhir_invalid_resource_type(client: TestClient, db_session, test_admin):
    """Verify importing unsupported resourceType is rejected with structured errors."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "resourceType": "Device",
        "id": "DEV-001",
    }

    res = client.post("/api/v1/fhir/import", json=payload, headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["success"] is False
    assert data["status"] == "failed"
    assert "Unsupported FHIR resourceType" in data["validation_errors"][0]


def test_import_fhir_encounter_missing_subject(client: TestClient, db_session, test_admin):
    """Verify encounter without subject reference is rejected by validator."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "resourceType": "Encounter",
        "status": "finished",
    }

    res = client.post("/api/v1/fhir/import", json=payload, headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["success"] is False
    assert any("subject.reference" in err for err in data["validation_errors"])
