from fastapi import status
from fastapi.testclient import TestClient

from app.schemas.doctor import (
    ConsultationMode,
    DoctorAvailabilityStatus,
    DoctorVerificationStatus,
)
from app.schemas.user import UserRole


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "doc1@hospital.org",
    name: str = "Dr. Standard",
) -> tuple[dict[str, str], int]:
    """Register and authenticate user, returning headers and user ID."""
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
            "email": email,
            "password": "SecurePassword123!",
            "role": role.value,
        },
    )
    user_id = reg_res.json()["id"]

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user_id


def test_admin_create_doctor_success(client: TestClient):
    """Verify admin can create a doctor profile for an existing doctor user."""
    admin_headers, _ = get_auth_headers(client, role=UserRole.ADMIN, email="admin_doc_create@hospital.org", name="Admin User")
    _, doctor_user_id = get_auth_headers(client, role=UserRole.DOCTOR, email="cardiologist@hospital.org", name="Dr. Gregory House")

    payload = {
        "user_id": doctor_user_id,
        "full_name": "Gregory House",
        "professional_title": "Dr.",
        "department": "Cardiology",
        "specialization": "Interventional Cardiology",
        "qualifications": "MBBS, MD (Cardiology)",
        "medical_degree": "MD",
        "medical_registration_number": "MED-REG-10001",
        "years_of_experience": 15,
        "phone": "+1-555-0101",
        "clinic_hospital_name": "Princeton Plainsboro Hospital",
        "consultation_location": "Diagnostics Wing, Room 402",
        "consultation_mode": "both",
        "professional_bio": "Specialist in diagnostic cardiology and internal medicine.",
    }

    response = client.post("/api/v1/doctors", json=payload, headers=admin_headers)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["doctor_id"].startswith("DOC-")
    assert data["full_name"] == "Gregory House"
    assert data["department"] == "Cardiology"
    assert data["specialization"] == "Interventional Cardiology"
    assert data["medical_registration_number"] == "MED-REG-10001"
    assert data["verification_status"] == "pending"
    assert data["availability_status"] == "available"
    assert data["user_id"] == doctor_user_id
    assert data["email"] == "cardiologist@hospital.org"


def test_doctor_self_registration(client: TestClient):
    """Verify doctor can create their own doctor profile."""
    doc_headers, user_id = get_auth_headers(client, role=UserRole.DOCTOR, email="dermatologist@hospital.org", name="Dr. Allison Cameron")

    payload = {
        "full_name": "Allison Cameron",
        "professional_title": "Dr.",
        "department": "Dermatology",
        "specialization": "Cosmetic Dermatology",
        "medical_registration_number": "MED-REG-10002",
        "years_of_experience": 8,
        "clinic_hospital_name": "City Skin Clinic",
    }

    response = client.post("/api/v1/doctors", json=payload, headers=doc_headers)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["user_id"] == user_id
    assert response.json()["department"] == "Dermatology"
    assert response.json()["specialization"] == "Cosmetic Dermatology"


def test_duplicate_doctor_user_rejected(client: TestClient):
    """Verify a user cannot have more than one doctor profile."""
    doc_headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="duplicate_doc@hospital.org", name="Dr. Eric Foreman")

    payload1 = {
        "full_name": "Eric Foreman",
        "department": "Neurology",
        "specialization": "Neurology",
        "medical_registration_number": "MED-REG-10003",
    }
    res1 = client.post("/api/v1/doctors", json=payload1, headers=doc_headers)
    assert res1.status_code == status.HTTP_201_CREATED

    payload2 = {
        "full_name": "Eric Foreman",
        "department": "Neurology",
        "specialization": "Neurology",
        "medical_registration_number": "MED-REG-10004",
    }
    res2 = client.post("/api/v1/doctors", json=payload2, headers=doc_headers)
    assert res2.status_code == status.HTTP_400_BAD_REQUEST
    assert "already has an associated doctor profile" in res2.json()["detail"]


def test_duplicate_medical_registration_rejected(client: TestClient):
    """Verify medical registration number must be unique across all doctors."""
    admin_headers, _ = get_auth_headers(client, role=UserRole.ADMIN, email="admin_dup_reg@hospital.org", name="Admin Dup")
    _, doc_user_1 = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_reg1@hospital.org", name="Dr. Reg One")
    _, doc_user_2 = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_reg2@hospital.org", name="Dr. Reg Two")

    client.post(
        "/api/v1/doctors",
        json={
            "user_id": doc_user_1,
            "full_name": "Reg One",
            "department": "Pediatrics",
            "specialization": "Pediatric Surgery",
            "medical_registration_number": "UNIQUE-REG-9999",
        },
        headers=admin_headers,
    )

    res_dup = client.post(
        "/api/v1/doctors",
        json={
            "user_id": doc_user_2,
            "full_name": "Reg Two",
            "department": "Pediatrics",
            "specialization": "Pediatric Cardiology",
            "medical_registration_number": "UNIQUE-REG-9999",
        },
        headers=admin_headers,
    )
    assert res_dup.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in res_dup.json()["detail"]


def test_doctor_view_and_update_own_profile(client: TestClient):
    """Verify doctor can view and update their own profile via /me."""
    doc_headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_me@hospital.org", name="Dr. Robert Chase")

    # Create profile
    client.post(
        "/api/v1/doctors",
        json={
            "full_name": "Robert Chase",
            "department": "General Surgery",
            "specialization": "Intensive Care Surgeon",
            "medical_registration_number": "MED-REG-10005",
            "years_of_experience": 10,
        },
        headers=doc_headers,
    )

    # Get /me
    get_me = client.get("/api/v1/doctors/me", headers=doc_headers)
    assert get_me.status_code == status.HTTP_200_OK
    assert get_me.json()["full_name"] == "Robert Chase"
    assert get_me.json()["department"] == "General Surgery"

    # Patch /me including department
    patch_me = client.patch(
        "/api/v1/doctors/me",
        json={"department": "Critical Care", "years_of_experience": 11, "consultation_location": "Surgical Wing, 3rd Floor"},
        headers=doc_headers,
    )
    assert patch_me.status_code == status.HTTP_200_OK
    assert patch_me.json()["department"] == "Critical Care"
    assert patch_me.json()["years_of_experience"] == 11
    assert patch_me.json()["consultation_location"] == "Surgical Wing, 3rd Floor"


def test_doctor_cannot_modify_another_doctor(client: TestClient):
    """Verify a doctor cannot modify another doctor's profile."""
    doc1_headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_a@hospital.org", name="Dr. Doc A")
    doc2_headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_b@hospital.org", name="Dr. Doc B")

    # Create profile for Doctor A
    res_a = client.post(
        "/api/v1/doctors",
        json={
            "full_name": "Doc A",
            "department": "Oncology",
            "specialization": "Radiation Oncology",
            "medical_registration_number": "MED-REG-10006",
        },
        headers=doc1_headers,
    )
    doctor_a_id = res_a.json()["doctor_id"]

    # Doctor B tries to update Doctor A's profile
    res_unauth = client.patch(
        f"/api/v1/doctors/{doctor_a_id}",
        json={"specialization": "Hacked"},
        headers=doc2_headers,
    )
    assert res_unauth.status_code == status.HTTP_403_FORBIDDEN
    assert "permission" in res_unauth.json()["detail"]


def test_admin_verification_workflow(client: TestClient):
    """Verify admin can verify, reject, and deactivate doctor profiles."""
    admin_headers, _ = get_auth_headers(client, role=UserRole.ADMIN, email="admin_wf@hospital.org", name="Admin Workflow")
    doc_headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_wf@hospital.org", name="Dr. Chris Taub")

    create_res = client.post(
        "/api/v1/doctors",
        json={
            "full_name": "Chris Taub",
            "department": "Surgery",
            "specialization": "Plastic Surgery",
            "medical_registration_number": "MED-REG-10007",
        },
        headers=doc_headers,
    )
    doctor_id = create_res.json()["doctor_id"]
    assert create_res.json()["verification_status"] == "pending"

    # Non-admin cannot verify
    unauth_verify = client.post(f"/api/v1/doctors/{doctor_id}/verify", headers=doc_headers)
    assert unauth_verify.status_code == status.HTTP_403_FORBIDDEN

    # Admin verifies doctor
    verify_res = client.post(f"/api/v1/doctors/{doctor_id}/verify", headers=admin_headers)
    assert verify_res.status_code == status.HTTP_200_OK
    assert verify_res.json()["verification_status"] == "verified"

    # Admin rejects doctor
    reject_res = client.post(
        f"/api/v1/doctors/{doctor_id}/reject",
        json={"rejection_reason": "Incomplete license documentation."},
        headers=admin_headers,
    )
    assert reject_res.status_code == status.HTTP_200_OK
    assert reject_res.json()["verification_status"] == "rejected"
    assert reject_res.json()["rejection_reason"] == "Incomplete license documentation."

    # Admin soft deactivates doctor
    deact_res = client.delete(f"/api/v1/doctors/{doctor_id}", headers=admin_headers)
    assert deact_res.status_code == status.HTTP_200_OK
    assert deact_res.json()["verification_status"] == "inactive"
    assert deact_res.json()["availability_status"] == "unavailable"


def test_public_doctor_discovery_and_filtering(client: TestClient):
    """Verify patients can only browse verified doctors with public fields, and search by specialization."""
    admin_headers, _ = get_auth_headers(client, role=UserRole.ADMIN, email="admin_disc@hospital.org", name="Admin Discovery")
    patient_headers, _ = get_auth_headers(client, role=UserRole.HEALTHCARE_STAFF, email="patient_disc@hospital.org", name="Patient User")

    # Create 2 doctors
    _, doc1_uid = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_verified@hospital.org", name="Dr. Lisa Cuddy")
    _, doc2_uid = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_pending@hospital.org", name="Dr. James Wilson")

    res1 = client.post(
        "/api/v1/doctors",
        json={
            "user_id": doc1_uid,
            "full_name": "Lisa Cuddy",
            "department": "Endocrinology",
            "specialization": "Reproductive Endocrinology",
            "medical_registration_number": "MED-REG-10008",
            "years_of_experience": 18,
            "clinic_hospital_name": "Metro Endocrinology Clinic",
        },
        headers=admin_headers,
    )
    doc1_id = res1.json()["doctor_id"]

    res2 = client.post(
        "/api/v1/doctors",
        json={
            "user_id": doc2_uid,
            "full_name": "James Wilson",
            "department": "Oncology",
            "specialization": "Clinical Oncology",
            "medical_registration_number": "MED-REG-10009",
            "years_of_experience": 14,
        },
        headers=admin_headers,
    )
    doc2_id = res2.json()["doctor_id"]

    # Verify doctor 1 only
    client.post(f"/api/v1/doctors/{doc1_id}/verify", headers=admin_headers)

    # Patient lists doctors -> only Doctor 1 should appear
    patient_list = client.get("/api/v1/doctors", headers=patient_headers)
    assert patient_list.status_code == status.HTTP_200_OK
    items = patient_list.json()["items"]
    assert any(d["doctor_id"] == doc1_id for d in items)
    assert not any(d["doctor_id"] == doc2_id for d in items)

    # Verify no private admin fields in patient view
    verified_doc_item = next(d for d in items if d["doctor_id"] == doc1_id)
    assert "medical_registration_number" not in verified_doc_item
    assert "email" not in verified_doc_item
    assert verified_doc_item["department"] == "Endocrinology"

    # Patient tries to view unverified doctor directly -> 404
    unverified_get = client.get(f"/api/v1/doctors/{doc2_id}", headers=patient_headers)
    assert unverified_get.status_code == status.HTTP_404_NOT_FOUND

    # Patient filters by specialization
    filter_res = client.get("/api/v1/doctors?specialization=Endocrinology", headers=patient_headers)
    assert filter_res.status_code == status.HTTP_200_OK
    assert all("Endocrinology" in d["specialization"] for d in filter_res.json()["items"])


def test_doctor_department_and_multi_filter_search(client: TestClient):
    """Verify comprehensive department, specialization, experience, availability and multi-filter discovery."""
    admin_headers, _ = get_auth_headers(client, role=UserRole.ADMIN, email="admin_multi_flt@hospital.org", name="Admin Multi")
    patient_headers, _ = get_auth_headers(client, role=UserRole.HEALTHCARE_STAFF, email="patient_multi_flt@hospital.org", name="Patient Multi")

    # Register multiple doctors across departments
    _, doc_dentist_1 = get_auth_headers(client, role=UserRole.DOCTOR, email="dentist1@hospital.org", name="Dr. Rahul Sharma")
    _, doc_dentist_2 = get_auth_headers(client, role=UserRole.DOCTOR, email="dentist2@hospital.org", name="Dr. Priya Patel")
    _, doc_cardio = get_auth_headers(client, role=UserRole.DOCTOR, email="cardio_flt@hospital.org", name="Dr. Vikram Rao")

    # Doctor 1: Dentistry / Orthodontist (7 yrs, available)
    r1 = client.post(
        "/api/v1/doctors",
        json={
            "user_id": doc_dentist_1,
            "full_name": "Rahul Sharma",
            "department": "Dentistry",
            "specialization": "Orthodontist",
            "medical_registration_number": "DENT-REG-001",
            "years_of_experience": 7,
            "clinic_hospital_name": "Smile Dental Center",
            "consultation_mode": "in_person",
        },
        headers=admin_headers,
    )
    doc1_id = r1.json()["doctor_id"]

    # Doctor 2: Dentistry / Periodontist (3 yrs, available)
    r2 = client.post(
        "/api/v1/doctors",
        json={
            "user_id": doc_dentist_2,
            "full_name": "Priya Patel",
            "department": "Dentistry",
            "specialization": "Periodontist",
            "medical_registration_number": "DENT-REG-002",
            "years_of_experience": 3,
            "clinic_hospital_name": "City Dental Clinic",
            "consultation_mode": "both",
        },
        headers=admin_headers,
    )
    doc2_id = r2.json()["doctor_id"]

    # Doctor 3: Cardiology / Cardiologist (12 yrs, available)
    r3 = client.post(
        "/api/v1/doctors",
        json={
            "user_id": doc_cardio,
            "full_name": "Vikram Rao",
            "department": "Cardiology",
            "specialization": "Cardiologist",
            "medical_registration_number": "CARD-REG-001",
            "years_of_experience": 12,
            "clinic_hospital_name": "Apex Heart Hospital",
            "consultation_mode": "telehealth",
        },
        headers=admin_headers,
    )
    doc3_id = r3.json()["doctor_id"]

    # Verify all 3 doctors
    client.post(f"/api/v1/doctors/{doc1_id}/verify", headers=admin_headers)
    client.post(f"/api/v1/doctors/{doc2_id}/verify", headers=admin_headers)
    client.post(f"/api/v1/doctors/{doc3_id}/verify", headers=admin_headers)

    # 1. Department search: GET /api/v1/doctors?department=Dentistry
    dent_res = client.get("/api/v1/doctors?department=Dentistry", headers=patient_headers)
    assert dent_res.status_code == status.HTTP_200_OK
    assert dent_res.json()["total"] == 2
    assert all(d["department"] == "Dentistry" for d in dent_res.json()["items"])

    # 2. Combined department + specialization search: GET /api/v1/doctors?department=Dentistry&specialization=Orthodontist
    ortho_res = client.get("/api/v1/doctors?department=Dentistry&specialization=Orthodontist", headers=patient_headers)
    assert ortho_res.status_code == status.HTTP_200_OK
    assert ortho_res.json()["total"] == 1
    assert ortho_res.json()["items"][0]["specialization"] == "Orthodontist"
    assert ortho_res.json()["items"][0]["full_name"] == "Rahul Sharma"

    # 3. Combined department + availability search: GET /api/v1/doctors?department=Dentistry&availability=available
    avail_res = client.get("/api/v1/doctors?department=Dentistry&availability=available", headers=patient_headers)
    assert avail_res.status_code == status.HTTP_200_OK
    assert avail_res.json()["total"] == 2

    # 4. Name search: GET /api/v1/doctors?search=Rahul
    name_search = client.get("/api/v1/doctors?search=Rahul", headers=patient_headers)
    assert name_search.status_code == status.HTTP_200_OK
    assert name_search.json()["total"] == 1
    assert name_search.json()["items"][0]["doctor_id"] == doc1_id

    # 5. Department + experience filter: GET /api/v1/doctors?department=Dentistry&min_experience=5
    exp_res = client.get("/api/v1/doctors?department=Dentistry&min_experience=5", headers=patient_headers)
    assert exp_res.status_code == status.HTTP_200_OK
    assert exp_res.json()["total"] == 1
    assert exp_res.json()["items"][0]["doctor_id"] == doc1_id

    # 6. Combined multi-filter: department + specialization + availability + min_experience
    multi_res = client.get(
        "/api/v1/doctors?department=Dentistry&specialization=Orthodontist&availability=available&min_experience=5",
        headers=patient_headers,
    )
    assert multi_res.status_code == status.HTTP_200_OK
    assert multi_res.json()["total"] == 1
    assert multi_res.json()["items"][0]["doctor_id"] == doc1_id

    # 7. Case-insensitive search
    case_res = client.get("/api/v1/doctors?department=dentistry&specialization=orthodontist", headers=patient_headers)
    assert case_res.status_code == status.HTTP_200_OK
    assert case_res.json()["total"] == 1

    # 8. Pagination with page_size parameter
    page_res = client.get("/api/v1/doctors?page=1&page_size=1", headers=patient_headers)
    assert page_res.status_code == status.HTTP_200_OK
    assert page_res.json()["size"] == 1
    assert len(page_res.json()["items"]) == 1
    assert page_res.json()["total_pages"] >= 3


def test_doctor_availability_toggle(client: TestClient):
    """Verify activating and deactivating doctor availability."""
    doc_headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_avail@hospital.org", name="Dr. Avail")

    create_res = client.post(
        "/api/v1/doctors",
        json={
            "full_name": "Avail Doctor",
            "department": "General Medicine",
            "specialization": "General Medicine",
            "medical_registration_number": "MED-REG-10010",
        },
        headers=doc_headers,
    )
    doctor_id = create_res.json()["doctor_id"]

    # Set unavailable / deactivate
    deact_res = client.post(f"/api/v1/doctors/{doctor_id}/deactivate", headers=doc_headers)
    assert deact_res.status_code == status.HTTP_200_OK
    assert deact_res.json()["availability_status"] == "unavailable"

    # Set available / activate
    act_res = client.post(f"/api/v1/doctors/{doctor_id}/activate", headers=doc_headers)
    assert act_res.status_code == status.HTTP_200_OK
    assert act_res.json()["availability_status"] == "available"


def test_unauthenticated_doctor_access_rejected(client: TestClient):
    """Verify unauthenticated requests are rejected with 401."""
    assert client.post("/api/v1/doctors", json={}).status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/doctors").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/doctors/me").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.patch("/api/v1/doctors/me", json={}).status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/api/v1/doctors/DOC-001").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.patch("/api/v1/doctors/DOC-001", json={}).status_code == status.HTTP_401_UNAUTHORIZED
    assert client.delete("/api/v1/doctors/DOC-001").status_code == status.HTTP_401_UNAUTHORIZED
