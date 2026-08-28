from datetime import date
from fastapi import status
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.patient import Patient
from app.schemas.patient import Gender, PatientStatus
from app.schemas.user import UserRole


def get_auth_headers(client: TestClient, role: UserRole = UserRole.DOCTOR, email: str = "doc@test.org") -> dict[str, str]:
    """Helper to create and authenticate a user with the specified role."""
    client.post(
        "/api/v1/auth/register",
        json={
            "name": f"Test {role.value.capitalize()}",
            "email": email,
            "password": "ValidPassword123!",
            "role": role.value,
        },
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "ValidPassword123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_patient_success(client: TestClient):
    """Verify patient creation with auto-generated patient_id and standard fields."""
    headers = get_auth_headers(client, role=UserRole.DOCTOR, email="doc1@hospital.org")
    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1985-05-15",
        "gender": "male",
        "phone": "+1-555-0199",
        "email": "john.doe@example.com",
        "address": "123 Healthcare Ave, Cityville",
        "emergency_contact_name": "Jane Doe",
        "emergency_contact_phone": "+1-555-0198",
    }
    response = client.post("/api/v1/patients", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["date_of_birth"] == "1985-05-15"
    assert data["gender"] == "male"
    assert data["status"] == "active"
    assert data["patient_id"].startswith("PAT-")
    assert "id" in data
    assert "created_at" in data


def test_create_patient_custom_id(client: TestClient):
    """Verify patient creation with explicit unique patient_id."""
    headers = get_auth_headers(client, role=UserRole.HEALTHCARE_STAFF, email="staff1@hospital.org")
    payload = {
        "patient_id": "PAT-CUSTOM-001",
        "first_name": "Emily",
        "last_name": "Clark",
        "date_of_birth": "1992-10-20",
        "gender": "female",
    }
    response = client.post("/api/v1/patients", json=payload, headers=headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["patient_id"] == "PAT-CUSTOM-001"


def test_create_patient_duplicate_id_fails(client: TestClient):
    """Verify that creating a patient with a duplicate patient_id returns 400 Bad Request."""
    headers = get_auth_headers(client, role=UserRole.ADMIN, email="admin1@hospital.org")
    payload = {
        "patient_id": "PAT-DUPLICATE-01",
        "first_name": "Mark",
        "last_name": "Twain",
        "date_of_birth": "1970-01-01",
        "gender": "male",
    }
    res1 = client.post("/api/v1/patients", json=payload, headers=headers)
    assert res1.status_code == status.HTTP_201_CREATED

    res2 = client.post("/api/v1/patients", json=payload, headers=headers)
    assert res2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in res2.json()["detail"]


def test_unauthenticated_patient_access_rejected(client: TestClient):
    """Verify that unauthenticated requests to patient endpoints return 401."""
    # POST
    assert client.post("/api/v1/patients", json={}).status_code == status.HTTP_401_UNAUTHORIZED
    # GET list
    assert client.get("/api/v1/patients").status_code == status.HTTP_401_UNAUTHORIZED
    # GET single
    assert client.get("/api/v1/patients/PAT-001").status_code == status.HTTP_401_UNAUTHORIZED
    # PATCH
    assert client.patch("/api/v1/patients/PAT-001", json={}).status_code == status.HTTP_401_UNAUTHORIZED
    # DELETE
    assert client.delete("/api/v1/patients/PAT-001").status_code == status.HTTP_401_UNAUTHORIZED


def test_invalid_patient_data_validation(client: TestClient):
    """Verify that invalid inputs (missing required fields, bad email, bad date) return 422."""
    headers = get_auth_headers(client, role=UserRole.DOCTOR, email="doc2@hospital.org")

    # Missing date_of_birth
    res_missing = client.post(
        "/api/v1/patients",
        json={"first_name": "A", "last_name": "B", "gender": "male"},
        headers=headers,
    )
    assert res_missing.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Invalid email
    res_bad_email = client.post(
        "/api/v1/patients",
        json={
            "first_name": "A",
            "last_name": "B",
            "date_of_birth": "1990-01-01",
            "gender": "female",
            "email": "not-valid-email",
        },
        headers=headers,
    )
    assert res_bad_email.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_patient_by_id(client: TestClient):
    """Verify retrieving a patient by patient_id returns 200 and 404 for non-existent."""
    headers = get_auth_headers(client, role=UserRole.HEALTHCARE_STAFF, email="staff2@hospital.org")
    create_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Robert",
            "last_name": "Pattinson",
            "date_of_birth": "1986-05-13",
            "gender": "male",
            "phone": "+1-555-4321",
        },
        headers=headers,
    )
    patient_id = create_res.json()["patient_id"]

    # Retrieve existing
    get_res = client.get(f"/api/v1/patients/{patient_id}", headers=headers)
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["first_name"] == "Robert"

    # Retrieve non-existent
    not_found_res = client.get("/api/v1/patients/PAT-NONEXISTENT", headers=headers)
    assert not_found_res.status_code == status.HTTP_404_NOT_FOUND


def test_list_and_search_patients(client: TestClient):
    """Verify listing patients, search filtering, and status filtering."""
    headers = get_auth_headers(client, role=UserRole.DOCTOR, email="doc3@hospital.org")

    # Create 3 patients
    client.post(
        "/api/v1/patients",
        json={"patient_id": "PAT-SRCH-01", "first_name": "Alexander", "last_name": "Fleming", "date_of_birth": "1881-08-06", "gender": "male", "phone": "+44-1234"},
        headers=headers,
    )
    client.post(
        "/api/v1/patients",
        json={"patient_id": "PAT-SRCH-02", "first_name": "Marie", "last_name": "Curie", "date_of_birth": "1867-11-07", "gender": "female", "phone": "+33-5678"},
        headers=headers,
    )
    client.post(
        "/api/v1/patients",
        json={"patient_id": "PAT-SRCH-03", "first_name": "Louis", "last_name": "Pasteur", "date_of_birth": "1822-12-27", "gender": "male", "phone": "+33-9999", "status": "inactive"},
        headers=headers,
    )

    # List all
    list_res = client.get("/api/v1/patients?page=1&size=10", headers=headers)
    assert list_res.status_code == status.HTTP_200_OK
    data = list_res.json()
    assert data["total"] >= 3
    assert len(data["items"]) >= 3
    assert data["page"] == 1
    assert data["size"] == 10
    assert data["total_pages"] >= 1

    # Search by first name
    search_res = client.get("/api/v1/patients?search=Marie", headers=headers)
    assert search_res.status_code == status.HTTP_200_OK
    search_data = search_res.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["first_name"] == "Marie"

    # Search by patient_id
    search_id_res = client.get("/api/v1/patients?search=PAT-SRCH-01", headers=headers)
    assert search_id_res.status_code == status.HTTP_200_OK
    assert search_id_res.json()["items"][0]["last_name"] == "Fleming"

    # Filter by status
    filter_status = client.get("/api/v1/patients?status=inactive", headers=headers)
    assert filter_status.status_code == status.HTTP_200_OK
    assert any(p["patient_id"] == "PAT-SRCH-03" for p in filter_status.json()["items"])


def test_update_patient(client: TestClient):
    """Verify PATCH updates mutable fields while preserving immutable fields."""
    headers = get_auth_headers(client, role=UserRole.DOCTOR, email="doc4@hospital.org")
    create_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Bruce",
            "last_name": "Wayne",
            "date_of_birth": "1980-02-19",
            "gender": "male",
            "phone": "+1-555-BAT1",
            "address": "Wayne Manor",
        },
        headers=headers,
    )
    patient_id = create_res.json()["patient_id"]
    original_id = create_res.json()["id"]
    original_created_at = create_res.json()["created_at"]

    # Update address and phone
    update_res = client.patch(
        f"/api/v1/patients/{patient_id}",
        json={"phone": "+1-555-BAT2", "address": "Batcave, Gotham"},
        headers=headers,
    )
    assert update_res.status_code == status.HTTP_200_OK
    updated_data = update_res.json()
    assert updated_data["phone"] == "+1-555-BAT2"
    assert updated_data["address"] == "Batcave, Gotham"
    assert updated_data["first_name"] == "Bruce"
    assert updated_data["id"] == original_id
    assert updated_data["patient_id"] == patient_id
    assert updated_data["created_at"] == original_created_at


def test_deactivate_patient(client: TestClient):
    """Verify soft delete / deactivation sets status to inactive and keeps database record."""
    admin_headers = get_auth_headers(client, role=UserRole.ADMIN, email="admin_deact@hospital.org")
    create_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Tony",
            "last_name": "Stark",
            "date_of_birth": "1970-05-29",
            "gender": "male",
        },
        headers=admin_headers,
    )
    patient_id = create_res.json()["patient_id"]
    assert create_res.json()["status"] == "active"

    # Soft delete / deactivate
    deact_res = client.delete(f"/api/v1/patients/{patient_id}", headers=admin_headers)
    assert deact_res.status_code == status.HTTP_200_OK
    assert deact_res.json()["status"] == "inactive"

    # Verify patient still exists and is accessible
    get_res = client.get(f"/api/v1/patients/{patient_id}", headers=admin_headers)
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["status"] == "inactive"
