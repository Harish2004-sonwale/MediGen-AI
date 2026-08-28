import pytest
from datetime import date
from fastapi import status
from fastapi.testclient import TestClient

from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import Gender, PatientStatus
from app.schemas.user import UserRegisterRequest, UserRole
from app.services.user_service import create_user


def test_unauthenticated_fhir_access_rejected(client: TestClient, test_patient):
    """Verify unauthenticated requests to FHIR endpoints are rejected with 401."""
    res = client.get(f"/api/v1/fhir/Patient/{test_patient.patient_id}")
    assert res.status_code == status.HTTP_401_UNAUTHORIZED

    res_bundle = client.get(f"/api/v1/fhir/patients/{test_patient.patient_id}/bundle")
    assert res_bundle.status_code == status.HTTP_401_UNAUTHORIZED

    res_import = client.post("/api/v1/fhir/import", json={"resourceType": "Patient"})
    assert res_import.status_code == status.HTTP_401_UNAUTHORIZED


def test_cross_patient_fhir_isolation(client: TestClient, db_session, test_patient, test_patient_user):
    """Verify Patient A cannot export Patient B's FHIR record."""
    # Create Patient B and User B
    user_b_in = UserRegisterRequest(
        name="Patient B User",
        email="patient_b_fhir@example.com",
        password="PatientBPassword123!",
        role=UserRole.PATIENT,
    )
    user_b = create_user(db_session, user_b_in)

    patient_b = Patient(
        patient_id="PAT-FHIR-SEC-0002",
        first_name="Bob",
        last_name="Patient",
        date_of_birth=date(1995, 5, 5),
        gender=Gender.MALE,
        email="patient_b_fhir@example.com",
        status=PatientStatus.ACTIVE,
    )
    db_session.add(patient_b)
    db_session.commit()
    db_session.refresh(patient_b)

    # Login as User A (linked to test_patient)
    login_a = client.post(
        "/api/v1/auth/login",
        json={"email": test_patient_user.email, "password": "PatientPassword123!"},
    )
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # User A accesses own record -> 200 OK
    res_own = client.get(f"/api/v1/fhir/Patient/{test_patient.patient_id}", headers=headers_a)
    assert res_own.status_code == status.HTTP_200_OK

    # User A accesses Patient B's record -> 403 Forbidden
    res_b = client.get(f"/api/v1/fhir/Patient/{patient_b.patient_id}", headers=headers_a)
    assert res_b.status_code == status.HTTP_403_FORBIDDEN

    # User A attempts to export Patient B's bundle -> 403 Forbidden
    res_bundle_b = client.get(f"/api/v1/fhir/patients/{patient_b.patient_id}/bundle", headers=headers_a)
    assert res_bundle_b.status_code == status.HTTP_403_FORBIDDEN


def test_unrelated_doctor_fhir_access_rejected(client: TestClient, db_session, test_patient):
    """Verify unrelated doctor without active clinical appointment cannot access patient FHIR data."""
    # Create unrelated doctor user
    doc_in = UserRegisterRequest(
        name="Dr. Unrelated FHIR",
        email="unrelated_doc_fhir@example.com",
        password="DoctorPassword123!",
        role=UserRole.DOCTOR,
    )
    doc_user = create_user(db_session, doc_in)

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": doc_user.email, "password": "DoctorPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Access without clinical appointment -> 403 Forbidden
    res = client.get(f"/api/v1/fhir/Patient/{test_patient.patient_id}", headers=headers)
    assert res.status_code == status.HTTP_403_FORBIDDEN
