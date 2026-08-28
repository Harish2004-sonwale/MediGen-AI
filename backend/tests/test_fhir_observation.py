import pytest
from datetime import datetime, timezone
from fastapi import status
from fastapi.testclient import TestClient

from app.services.fhir_mapper_service import FHIRObservationMapper


def test_fhir_observation_mapping(test_patient):
    """Verify construction of FHIR R4 Observation from clinical measurement data."""
    obs = FHIRObservationMapper.to_fhir(
        observation_id="OBS-TEST-001",
        test_name="Hemoglobin A1c",
        patient_id=test_patient.patient_id,
        value_quantity=7.4,
        unit="%",
        status="final",
        category_code="laboratory",
        effective_date=datetime.now(timezone.utc),
        notes="HbA1c controlled on Metformin",
    )

    assert obs.resourceType == "Observation"
    assert obs.id == "OBS-TEST-001"
    assert obs.status == "final"
    assert obs.code.text == "Hemoglobin A1c"
    assert obs.subject.reference == f"Patient/{test_patient.patient_id}"
    assert obs.valueQuantity.value == 7.4
    assert obs.valueQuantity.unit == "%"
    assert obs.category[0].coding[0].code == "laboratory"


def test_export_fhir_observation_endpoint(client: TestClient, db_session, test_admin, test_patient):
    """Verify GET /api/v1/fhir/Observation/{observation_id} endpoint."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    obs_id = f"OBS-{test_patient.patient_id}-001"
    res = client.get(f"/api/v1/fhir/Observation/{obs_id}", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["resourceType"] == "Observation"
    assert data["id"] == obs_id
    assert data["subject"]["reference"] == f"Patient/{test_patient.patient_id}"
