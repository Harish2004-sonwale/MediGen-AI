import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.schemas.encounter import EncounterCreate, EncounterType
from app.services.encounter_service import create_encounter


def test_export_fhir_patient_bundle(client: TestClient, db_session, test_admin, test_patient, test_doctor_user):
    """Verify exporting complete patient history as a FHIR R4 collection Bundle."""
    enc_in = EncounterCreate(
        encounter_type=EncounterType.INITIAL_CONSULTATION,
        chief_complaint="Chest pain and palpitations",
        clinical_notes="ECG indicates sinus tachycardia.",
        assessment="Sinus Tachycardia",
        plan="Start Beta-blocker.",
    )
    create_encounter(db_session, test_patient.patient_id, enc_in, test_doctor_user.id)

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/fhir/patients/{test_patient.patient_id}/bundle", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["resourceType"] == "Bundle"
    assert data["type"] == "collection"
    assert data["total"] >= 2  # At least Patient + Encounter + Condition
    assert len(data["entry"]) >= 2

    # Check Patient entry
    patient_entry = next((e for e in data["entry"] if e["resource"]["resourceType"] == "Patient"), None)
    assert patient_entry is not None
    assert patient_entry["resource"]["id"] == test_patient.patient_id

    # Check Encounter entry
    encounter_entry = next((e for e in data["entry"] if e["resource"]["resourceType"] == "Encounter"), None)
    assert encounter_entry is not None
    assert encounter_entry["resource"]["subject"]["reference"] == f"Patient/{test_patient.patient_id}"


def test_import_fhir_bundle_batch(client: TestClient, db_session, test_admin, test_patient):
    """Verify POST /api/v1/fhir/Bundle batch import containing patient update and new encounter."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    bundle_payload = {
        "resourceType": "Bundle",
        "type": "batch",
        "entry": [
            {
                "resource": {
                    "resourceType": "Patient",
                    "id": test_patient.patient_id,
                    "name": [{"family": "BundleUpdated", "given": ["Test"]}],
                    "gender": "male",
                    "birthDate": "1990-01-01",
                }
            },
            {
                "resource": {
                    "resourceType": "Encounter",
                    "status": "finished",
                    "subject": {"reference": f"Patient/{test_patient.patient_id}"},
                    "reasonCode": [{"text": "Follow-up visit via bundle import"}],
                    "diagnosis": [{"condition": {"display": "Hypertension controlled"}}],
                }
            },
        ],
    }

    res = client.post("/api/v1/fhir/Bundle", json=bundle_payload, headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["success"] is True
    assert data["imported"] == 2
    assert data["failed"] == 0
    assert len(data["results"]) == 2
