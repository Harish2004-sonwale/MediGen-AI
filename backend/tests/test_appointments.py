from datetime import datetime, timedelta, timezone
from fastapi import status
from fastapi.testclient import TestClient

from app.schemas.user import UserRole


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "doc_apt@hospital.org",
    name: str = "Dr. Apt User",
) -> tuple[dict[str, str], int]:
    """Register and login helper returning authorization headers and user ID."""
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


def setup_doctor_and_patient(client: TestClient) -> tuple[dict[str, str], str, dict[str, str], str, dict[str, str]]:
    """Helper to set up an admin, a verified doctor, and an active patient."""
    admin_headers, _ = get_auth_headers(client, role=UserRole.ADMIN, email="admin_apt_mgr@hospital.org", name="Admin Manager")
    doc_headers, doc_uid = get_auth_headers(client, role=UserRole.DOCTOR, email="cardiologist_apt@hospital.org", name="Dr. Marcus Welby")
    patient_headers, _ = get_auth_headers(client, role=UserRole.PATIENT, email="john.doe.apt@patient.org", name="John Doe")

    # Create doctor profile
    doc_res = client.post(
        "/api/v1/doctors",
        json={
            "user_id": doc_uid,
            "full_name": "Marcus Welby",
            "department": "Cardiology",
            "specialization": "General Cardiology",
            "medical_registration_number": "MED-APT-001",
            "years_of_experience": 12,
        },
        headers=admin_headers,
    )
    doctor_id = doc_res.json()["doctor_id"]

    # Verify doctor
    client.post(f"/api/v1/doctors/{doctor_id}/verify", headers=admin_headers)

    # Create patient
    pat_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "John",
            "last_name": "Doe",
            "date_of_birth": "1985-05-15",
            "gender": "male",
            "email": "john.doe.apt@patient.org",
            "phone": "+1-555-0199",
        },
        headers=admin_headers,
    )
    patient_id = pat_res.json()["patient_id"]

    return admin_headers, doctor_id, doc_headers, patient_id, patient_headers


def test_create_appointment_success(client: TestClient):
    """Verify successful appointment booking with future datetime and valid doctor/patient."""
    admin_headers, doctor_id, _, patient_id, _ = setup_doctor_and_patient(client)

    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    payload = {
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "appointment_date": future_time,
        "duration_minutes": 30,
        "consultation_mode": "in_person",
        "reason_for_visit": "Routine cardiac checkup and palpitations follow-up",
        "notes": "Patient advised to bring recent ECG printouts.",
    }

    res = client.post("/api/v1/appointments", json=payload, headers=admin_headers)
    assert res.status_code == status.HTTP_201_CREATED

    data = res.json()
    assert data["appointment_id"].startswith("APT-")
    assert data["patient_public_id"] == patient_id
    assert data["doctor_public_id"] == doctor_id
    assert data["status"] == "scheduled"
    assert data["duration_minutes"] == 30
    assert data["doctor_department"] == "Cardiology"
    assert data["doctor_name"] == "Dr. Marcus Welby"


def test_appointment_rejections_for_invalid_prerequisites(client: TestClient):
    """Verify validation errors for nonexistent, unverified, inactive entities, and past dates."""
    admin_headers, doctor_id, _, patient_id, _ = setup_doctor_and_patient(client)

    # 1. Past date rejection
    past_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    res_past = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": past_time,
            "reason_for_visit": "Past checkup",
        },
        headers=admin_headers,
    )
    assert res_past.status_code == status.HTTP_400_BAD_REQUEST
    assert "future" in res_past.json()["detail"]

    # 2. Nonexistent patient rejection
    future_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    res_nopatient = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": "PAT-99999999-XXXX",
            "doctor_id": doctor_id,
            "appointment_date": future_time,
            "reason_for_visit": "Checkup",
        },
        headers=admin_headers,
    )
    assert res_nopatient.status_code == status.HTTP_400_BAD_REQUEST
    assert "Patient reference" in res_nopatient.json()["detail"]

    # 3. Nonexistent doctor rejection
    res_nodoctor = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": "DOC-99999999-XXXX",
            "appointment_date": future_time,
            "reason_for_visit": "Checkup",
        },
        headers=admin_headers,
    )
    assert res_nodoctor.status_code == status.HTTP_400_BAD_REQUEST
    assert "Doctor reference" in res_nodoctor.json()["detail"]

    # 4. Unverified doctor rejection
    _, unverified_uid = get_auth_headers(client, role=UserRole.DOCTOR, email="unverified_doc@hospital.org", name="Dr. Unverified")
    unverified_res = client.post(
        "/api/v1/doctors",
        json={
            "user_id": unverified_uid,
            "full_name": "Unverified Doctor",
            "department": "Neurology",
            "specialization": "Neurology",
            "medical_registration_number": "MED-APT-UNVERIFIED",
        },
        headers=admin_headers,
    )
    unverified_doc_id = unverified_res.json()["doctor_id"]

    res_unver = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": unverified_doc_id,
            "appointment_date": future_time,
            "reason_for_visit": "Consultation",
        },
        headers=admin_headers,
    )
    assert res_unver.status_code == status.HTTP_400_BAD_REQUEST
    assert "not verified" in res_unver.json()["detail"]


def test_overlapping_appointment_conflict_rejected(client: TestClient):
    """Verify overlapping booking slots for the same doctor are rejected."""
    admin_headers, doctor_id, _, patient_id, _ = setup_doctor_and_patient(client)

    # Book slot at +5 days 10:00 UTC with duration 30 min
    slot_time = (datetime.now(timezone.utc) + timedelta(days=5)).replace(minute=0, second=0, microsecond=0)
    slot_iso = slot_time.isoformat()

    res1 = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": slot_iso,
            "duration_minutes": 30,
            "reason_for_visit": "Initial consultation",
        },
        headers=admin_headers,
    )
    assert res1.status_code == status.HTTP_201_CREATED

    # Book overlapping slot at 10:15 UTC (15 mins into 30 min slot)
    overlapping_iso = (slot_time + timedelta(minutes=15)).isoformat()
    res_overlap = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": overlapping_iso,
            "duration_minutes": 30,
            "reason_for_visit": "Conflicting consultation",
        },
        headers=admin_headers,
    )
    assert res_overlap.status_code == status.HTTP_400_BAD_REQUEST
    assert "already booked" in res_overlap.json()["detail"]


def test_appointment_lifecycle_transitions(client: TestClient):
    """Verify confirm, complete, and cancel appointment lifecycle transitions."""
    admin_headers, doctor_id, doc_headers, patient_id, _ = setup_doctor_and_patient(client)

    future_time = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    create_res = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": future_time,
            "duration_minutes": 45,
            "reason_for_visit": "Hypertension assessment",
        },
        headers=admin_headers,
    )
    apt_id = create_res.json()["appointment_id"]
    assert create_res.json()["status"] == "scheduled"

    # Doctor confirms appointment
    confirm_res = client.post(f"/api/v1/appointments/{apt_id}/confirm", headers=doc_headers)
    assert confirm_res.status_code == status.HTTP_200_OK
    assert confirm_res.json()["status"] == "confirmed"

    # Doctor completes appointment
    complete_res = client.post(f"/api/v1/appointments/{apt_id}/complete", headers=doc_headers)
    assert complete_res.status_code == status.HTTP_200_OK
    assert complete_res.json()["status"] == "completed"

    # Completed appointment cannot be cancelled
    cancel_fail = client.post(f"/api/v1/appointments/{apt_id}/cancel", headers=admin_headers)
    assert cancel_fail.status_code == status.HTTP_400_BAD_REQUEST

    # Create new appointment to test cancellation
    future_time_2 = (datetime.now(timezone.utc) + timedelta(days=8)).isoformat()
    create_res_2 = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": future_time_2,
            "reason_for_visit": "Cancellation test",
        },
        headers=admin_headers,
    )
    apt_id_2 = create_res_2.json()["appointment_id"]

    cancel_res = client.post(
        f"/api/v1/appointments/{apt_id_2}/cancel",
        json={"cancellation_reason": "Patient requested rescheduling due to travel."},
        headers=admin_headers,
    )
    assert cancel_res.status_code == status.HTTP_200_OK
    assert cancel_res.json()["status"] == "cancelled"
    assert cancel_res.json()["cancellation_reason"] == "Patient requested rescheduling due to travel."


def test_appointment_authorization_and_filtering(client: TestClient):
    """Verify patients only see their appointments, doctors see assigned appointments, and unauthenticated requests fail."""
    admin_headers, doctor_id, doc_headers, patient_id, patient_headers = setup_doctor_and_patient(client)

    future_time = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    create_res = client.post(
        "/api/v1/appointments",
        json={
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": future_time,
            "reason_for_visit": "Cardiac review",
        },
        headers=admin_headers,
    )
    apt_id = create_res.json()["appointment_id"]

    # 1. Patient can view their appointment
    pat_view = client.get(f"/api/v1/appointments/{apt_id}", headers=patient_headers)
    assert pat_view.status_code == status.HTTP_200_OK
    assert pat_view.json()["appointment_id"] == apt_id

    # 2. Doctor can view their assigned appointment
    doc_view = client.get(f"/api/v1/appointments/{apt_id}", headers=doc_headers)
    assert doc_view.status_code == status.HTTP_200_OK

    # 3. Another doctor cannot view it
    other_doc_headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="other_doc@hospital.org", name="Dr. Other")
    other_view = client.get(f"/api/v1/appointments/{apt_id}", headers=other_doc_headers)
    assert other_view.status_code == status.HTTP_403_FORBIDDEN

    # 4. Patient cannot confirm own appointment
    unauth_confirm = client.post(f"/api/v1/appointments/{apt_id}/confirm", headers=patient_headers)
    assert unauth_confirm.status_code == status.HTTP_403_FORBIDDEN

    # 5. Unauthenticated rejection
    assert client.get("/api/v1/appointments").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.post("/api/v1/appointments", json={}).status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get(f"/api/v1/appointments/{apt_id}").status_code == status.HTTP_401_UNAUTHORIZED
