import pytest
from datetime import datetime, timezone
from fastapi import status
from fastapi.testclient import TestClient

from app.services.fhir_mapper_service import FHIRMedicationStatementMapper


def test_fhir_medication_statement_mapping(test_patient):
    """Verify construction of FHIR R4 MedicationStatement from medication data."""
    med = FHIRMedicationStatementMapper.to_fhir(
        medication_id="MED-TEST-001",
        medication_name="Metformin 500mg Oral Tablet",
        patient_id=test_patient.patient_id,
        status="active",
        effective_date=datetime.now(timezone.utc),
        dosage_text="Take 1 tablet by mouth twice daily with meals",
        notes="Patient tolerating well without GI distress",
    )

    assert med.resourceType == "MedicationStatement"
    assert med.id == "MED-TEST-001"
    assert med.status == "active"
    assert med.medicationCodeableConcept.text == "Metformin 500mg Oral Tablet"
    assert med.subject.reference == f"Patient/{test_patient.patient_id}"
    assert len(med.dosage) == 1
    assert med.dosage[0].text == "Take 1 tablet by mouth twice daily with meals"
    assert len(med.note) == 1


def test_export_fhir_medication_endpoint(client: TestClient, db_session, test_admin, test_patient):
    """Verify GET /api/v1/fhir/MedicationStatement/{medication_id} endpoint."""
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "AdminPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    med_id = f"MED-{test_patient.patient_id}-001"
    res = client.get(f"/api/v1/fhir/MedicationStatement/{med_id}", headers=headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["resourceType"] == "MedicationStatement"
    assert data["id"] == med_id
    assert data["subject"]["reference"] == f"Patient/{test_patient.patient_id}"
