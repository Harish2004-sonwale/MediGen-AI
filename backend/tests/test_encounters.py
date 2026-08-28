from datetime import datetime, timezone
from fastapi import status
from fastapi.testclient import TestClient

from app.schemas.encounter import EncounterStatus, EncounterType
from app.schemas.user import UserRole


def get_auth_headers(client: TestClient, role: UserRole = UserRole.DOCTOR, email: str = "enc_doc@hospital.org") -> dict[str, str]:
    """Helper to register and authenticate a user with the specified role."""
    client.post(
        "/api/v1/auth/register",
        json={
            "name": f"Dr. {role.value.capitalize()}",
            "email": email,
            "password": "SecurePassword123!",
            "role": role.value,
        },
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_test_patient(client: TestClient, headers: dict[str, str], patient_id: str = "PAT-ENC-001") -> str:
    """Helper to create a test patient."""
    res = client.post(
        "/api/v1/patients",
        json={
            "patient_id": patient_id,
            "first_name": "Clara",
            "last_name": "Oswald",
            "date_of_birth": "1986-11-23",
            "gender": "female",
        },
        headers=headers,
    )
    return res.json()["patient_id"]


def test_create_encounter_success(client: TestClient):
    """Verify recording a clinical encounter for an existing patient."""
    headers = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_enc1@hospital.org")
    patient_id = create_test_patient(client, headers, patient_id="PAT-TEST-001")

    payload = {
        "encounter_type": "initial_consultation",
        "chief_complaint": "Persistent cough and mild fever for 4 days",
        "clinical_notes": "Chest auscultation reveals clear breath sounds bilaterally. No wheezing.",
        "assessment": "Acute viral upper respiratory tract infection.",
        "plan": "Rest, oral hydration, paracetamol 500mg as needed for fever. Follow up in 5 days if unresolved.",
        "status": "completed",
    }
    response = client.post(f"/api/v1/patients/{patient_id}/encounters", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["encounter_id"].startswith("ENC-")
    assert data["patient_id"] == patient_id
    assert data["encounter_type"] == "initial_consultation"
    assert data["chief_complaint"] == "Persistent cough and mild fever for 4 days"
    assert data["status"] == "completed"
    assert data["attending_user_name"] is not None
    assert "id" in data
    assert "created_at" in data


def test_create_encounter_nonexistent_patient_fails(client: TestClient):
    """Verify that creating an encounter for a non-existent patient returns 404."""
    headers = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_enc2@hospital.org")
    payload = {
        "chief_complaint": "Headache",
        "encounter_type": "routine_checkup",
    }
    response = client.post("/api/v1/patients/PAT-NONEXISTENT/encounters", json=payload, headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "was not found" in response.json()["detail"]


def test_unauthenticated_encounter_access_rejected(client: TestClient):
    """Verify unauthenticated requests to encounter endpoints are rejected with 401."""
    assert client.post("/api/v1/patients/PAT-001/encounters", json={}).status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/patients/PAT-001/encounters").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/encounters/ENC-001").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.patch("/api/v1/encounters/ENC-001", json={}).status_code == status.HTTP_401_UNAUTHORIZED


def test_clinical_roles_encounter_access(client: TestClient):
    """Verify doctor, healthcare_staff, and admin can all create and access encounters."""
    # Healthcare staff creating encounter
    staff_headers = get_auth_headers(client, role=UserRole.HEALTHCARE_STAFF, email="staff_enc@hospital.org")
    patient_id = create_test_patient(client, staff_headers, patient_id="PAT-ROLES-01")

    res_staff = client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        json={"chief_complaint": "Triage vitals check", "encounter_type": "routine_checkup"},
        headers=staff_headers,
    )
    assert res_staff.status_code == status.HTTP_201_CREATED
    encounter_id = res_staff.json()["encounter_id"]

    # Doctor retrieving encounter
    doc_headers = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_roles@hospital.org")
    res_doc = client.get(f"/api/v1/encounters/{encounter_id}", headers=doc_headers)
    assert res_doc.status_code == status.HTTP_200_OK

    # Admin retrieving and updating encounter
    admin_headers = get_auth_headers(client, role=UserRole.ADMIN, email="admin_roles@hospital.org")
    res_admin = client.patch(
        f"/api/v1/encounters/{encounter_id}",
        json={"status": "amended", "clinical_notes": "Reviewed and verified by clinical director."},
        headers=admin_headers,
    )
    assert res_admin.status_code == status.HTTP_200_OK
    assert res_admin.json()["status"] == "amended"


def test_multiple_encounters_chronological_listing(client: TestClient):
    """Verify multiple encounters for a single patient are listed with pagination."""
    headers = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_multi@hospital.org")
    patient_id = create_test_patient(client, headers, patient_id="PAT-MULTI-01")

    # Record 3 distinct encounters
    client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        json={"chief_complaint": "Initial sprained ankle", "encounter_type": "emergency"},
        headers=headers,
    )
    client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        json={"chief_complaint": "2-week follow up on ankle", "encounter_type": "follow_up"},
        headers=headers,
    )
    client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        json={"chief_complaint": "Annual routine wellness check", "encounter_type": "routine_checkup"},
        headers=headers,
    )

    # List encounters
    list_res = client.get(f"/api/v1/patients/{patient_id}/encounters?page=1&size=10", headers=headers)
    assert list_res.status_code == status.HTTP_200_OK
    data = list_res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["page"] == 1
    assert data["total_pages"] == 1


def test_invalid_encounter_validation(client: TestClient):
    """Verify that missing required fields or bad encounter types fail with 422."""
    headers = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_invalid@hospital.org")
    patient_id = create_test_patient(client, headers, patient_id="PAT-INV-01")

    # Missing chief_complaint
    res_missing = client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        json={"encounter_type": "follow_up"},
        headers=headers,
    )
    assert res_missing.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Invalid encounter_type
    res_bad_type = client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        json={"chief_complaint": "Checkup", "encounter_type": "invalid_type"},
        headers=headers,
    )
    assert res_bad_type.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_and_patch_encounter(client: TestClient):
    """Verify retrieving and updating encounter details."""
    headers = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_patch@hospital.org")
    patient_id = create_test_patient(client, headers, patient_id="PAT-PATCH-01")

    create_res = client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        json={
            "chief_complaint": "Earache and dizziness",
            "clinical_notes": "Erythema of the right tympanic membrane.",
            "assessment": "Otitis media",
            "plan": "Amoxicillin 500mg TID for 7 days",
        },
        headers=headers,
    )
    encounter_id = create_res.json()["encounter_id"]
    original_id = create_res.json()["id"]

    # Get single encounter
    get_res = client.get(f"/api/v1/encounters/{encounter_id}", headers=headers)
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["assessment"] == "Otitis media"

    # Patch encounter
    patch_res = client.patch(
        f"/api/v1/encounters/{encounter_id}",
        json={
            "plan": "Amoxicillin 500mg TID for 7 days + decongestant",
            "status": "amended",
        },
        headers=headers,
    )
    assert patch_res.status_code == status.HTTP_200_OK
    data = patch_res.json()
    assert data["plan"] == "Amoxicillin 500mg TID for 7 days + decongestant"
    assert data["status"] == "amended"
    assert data["id"] == original_id
    assert data["encounter_id"] == encounter_id


def test_patient_deactivation_preserves_clinical_encounters(client: TestClient):
    """Verify that deactivating a patient keeps clinical encounters intact and retrievable."""
    admin_headers = get_auth_headers(client, role=UserRole.ADMIN, email="admin_preserve@hospital.org")
    patient_id = create_test_patient(client, admin_headers, patient_id="PAT-PRESERVE-01")

    # Create encounter for patient
    enc_res = client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        json={
            "chief_complaint": "Severe acute migraine with visual aura",
            "clinical_notes": "Patient reports photophobia and nausea.",
            "assessment": "Acute migraine without complications.",
            "plan": "Sumatriptan 50mg, dark quiet room, follow-up if persisting.",
            "status": "completed",
        },
        headers=admin_headers,
    )
    assert enc_res.status_code == status.HTTP_201_CREATED
    encounter_id = enc_res.json()["encounter_id"]

    # Deactivate the patient (soft-delete)
    deact_res = client.delete(f"/api/v1/patients/{patient_id}", headers=admin_headers)
    assert deact_res.status_code == status.HTTP_200_OK
    assert deact_res.json()["status"] == "inactive"

    # Verify encounter is still fully retrievable
    get_enc_res = client.get(f"/api/v1/encounters/{encounter_id}", headers=admin_headers)
    assert get_enc_res.status_code == status.HTTP_200_OK
    assert get_enc_res.json()["encounter_id"] == encounter_id
    assert get_enc_res.json()["patient_id"] == patient_id
    assert get_enc_res.json()["assessment"] == "Acute migraine without complications."

    # Verify encounter still shows in patient's chronological history
    list_enc_res = client.get(f"/api/v1/patients/{patient_id}/encounters", headers=admin_headers)
    assert list_enc_res.status_code == status.HTTP_200_OK
    assert list_enc_res.json()["total"] == 1
    assert list_enc_res.json()["items"][0]["encounter_id"] == encounter_id
