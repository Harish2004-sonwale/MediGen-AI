"""Comprehensive Test Suite for Clinical Decision Support (CDS) Safety Layer.

Phase 8.9: Longitudinal Clinical Intelligence & Safety Layer.
Tests medication duplication detection, allergy warning checks, drug-drug interaction providers,
contraindication checking, patient isolation, and RBAC authorization.
"""

from datetime import datetime, timedelta, timezone
from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.core.config import settings
from app.schemas.user import UserRole


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.PATIENT,
    email: str = "patient_safety@hospital.org",
    name: str = "Safety User",
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


@pytest.fixture
def safety_env(client: TestClient) -> dict[str, any]:
    """Setup Admin, Doctor, and Patients for clinical safety tests."""
    admin_headers, _ = get_auth_headers(
        client, role=UserRole.ADMIN, email="admin_safety@hospital.org", name="Admin Safety"
    )
    doc_headers, doc_uid = get_auth_headers(
        client, role=UserRole.DOCTOR, email="dr_safety@hospital.org", name="Dr. Gregory Safety"
    )
    unrelated_doc_headers, _ = get_auth_headers(
        client, role=UserRole.DOCTOR, email="unrelated_safety_doc@hospital.org", name="Dr. Unrelated Safety"
    )

    # Patient A
    pat_a_headers, _ = get_auth_headers(
        client, role=UserRole.PATIENT, email="alice_safety@patient.org", name="Alice Safety"
    )
    pat_a_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Alice",
            "last_name": "Safety",
            "date_of_birth": "1990-05-15",
            "gender": "female",
            "email": "alice_safety@patient.org",
        },
        headers=admin_headers,
    )
    pat_a_id = pat_a_res.json()["patient_id"]

    # Patient B
    pat_b_headers, _ = get_auth_headers(
        client, role=UserRole.PATIENT, email="bob_safety@patient.org", name="Bob Safety"
    )
    pat_b_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Bob",
            "last_name": "Safety",
            "date_of_birth": "1985-08-20",
            "gender": "male",
            "email": "bob_safety@patient.org",
        },
        headers=admin_headers,
    )
    pat_b_id = pat_b_res.json()["patient_id"]

    # Create & verify Doctor Profile
    doc_res = client.post(
        "/api/v1/doctors",
        json={
            "user_id": doc_uid,
            "full_name": "Gregory Safety",
            "department": "Internal Medicine",
            "specialization": "Clinical Pharmacology",
            "medical_registration_number": "MED-SAFETY-001",
        },
        headers=admin_headers,
    )
    doc_id = doc_res.json()["doctor_id"]
    client.post(f"/api/v1/doctors/{doc_id}/verify", headers=admin_headers)

    # Link Doctor to Patient A via appointment
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    client.post(
        "/api/v1/appointments",
        json={
            "patient_id": pat_a_id,
            "doctor_id": doc_id,
            "appointment_date": future_time,
            "duration_minutes": 30,
            "consultation_mode": "in_person",
            "reason_for_visit": "Safety Baseline Review",
        },
        headers=admin_headers,
    )

    return {
        "admin_headers": admin_headers,
        "doc_headers": doc_headers,
        "unrelated_doc_headers": unrelated_doc_headers,
        "pat_a_headers": pat_a_headers,
        "pat_a_id": pat_a_id,
        "pat_b_headers": pat_b_headers,
        "pat_b_id": pat_b_id,
        "doc_id": doc_id,
    }


def _upload_safety_doc(client: TestClient, patient_id: str, title: str, content: str, headers: dict):
    """Helper to upload a test clinical document with medication and allergy information."""
    files = {
        "file": (f"{title.lower().replace(' ', '_')}.txt", content.encode("utf-8"), "text/plain"),
    }
    data = {
        "patient_id": patient_id,
        "title": title,
        "document_type": "clinical_note",
    }
    res = client.post("/api/v1/documents/upload", data=data, files=files, headers=headers)
    assert res.status_code == status.HTTP_201_CREATED
    return res.json()


def test_medication_duplication_detection(client: TestClient, safety_env, tmp_path):
    """Detects duplicate or overlapping active medication entries."""
    settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
    env = safety_env
    pat_id = env["pat_a_id"]
    pat_headers = env["pat_a_headers"]
    doc_headers = env["doc_headers"]

    # Upload document with Metformin
    doc_content = (
        "INTERNAL MEDICINE NOTE\n"
        "Diagnosis: Type 2 Diabetes Mellitus.\n"
        "Prescribed: Metformin 500mg BID oral."
    )
    _upload_safety_doc(client, pat_id, "Diabetes Note", doc_content, doc_headers)

    # Run safety check with candidate Metformin 1000mg
    res = client.post(
        f"/api/v1/patients/{pat_id}/safety/check",
        json={
            "candidate_medications": ["Metformin 1000mg daily"],
        },
        headers=pat_headers,
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["patient_id"] == pat_id
    dup_alerts = [a for a in data["alerts"] if a["alert_type"] == "medication_duplicate"]
    assert len(dup_alerts) >= 1
    assert dup_alerts[0]["severity"] == "MODERATE"
    assert dup_alerts[0]["requires_clinician_review"] is True
    assert "disclaimer" in data


def test_allergy_warning_conflict_detection(client: TestClient, safety_env, tmp_path):
    """Detects severe conflict when prescribed medication matches documented allergy."""
    settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
    env = safety_env
    pat_id = env["pat_a_id"]
    pat_headers = env["pat_a_headers"]
    doc_headers = env["doc_headers"]

    # Upload document with Penicillin allergy
    doc_content = (
        "ADMISSION INTAKE\n"
        "Allergies: Penicillin (anaphylaxis), Sulfa drugs.\n"
        "Diagnosis: Acute bacterial sinusitis."
    )
    _upload_safety_doc(client, pat_id, "Allergy Record", doc_content, doc_headers)

    # Candidate medication: Penicillin VK 500mg
    res = client.post(
        f"/api/v1/patients/{pat_id}/safety/check",
        json={
            "candidate_medications": ["Penicillin VK 500mg QID"],
        },
        headers=pat_headers,
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    allergy_alerts = [a for a in data["alerts"] if a["alert_type"] == "allergy_warning"]
    assert len(allergy_alerts) >= 1
    assert allergy_alerts[0]["severity"] == "CRITICAL"
    assert data["safe_to_proceed"] is False


def test_drug_drug_interaction_provider_evaluation(client: TestClient, safety_env, tmp_path):
    """Detects drug-drug interaction via pluggable interaction provider."""
    settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
    env = safety_env
    pat_id = env["pat_a_id"]
    pat_headers = env["pat_a_headers"]
    doc_headers = env["doc_headers"]

    # Document contains Warfarin
    doc_content = (
        "CARDIOLOGY DISCHARGE NOTE\n"
        "Diagnosis: Chronic atrial fibrillation.\n"
        "Prescribed: Warfarin 5mg daily."
    )
    _upload_safety_doc(client, pat_id, "Warfarin Note", doc_content, doc_headers)

    # Check candidate Aspirin
    res = client.post(
        f"/api/v1/patients/{pat_id}/safety/check",
        json={
            "candidate_medications": ["Aspirin 81mg daily"],
        },
        headers=pat_headers,
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    ddi_alerts = [a for a in data["alerts"] if a["alert_type"] == "drug_interaction"]
    assert len(ddi_alerts) >= 1
    assert ddi_alerts[0]["severity"] in ("HIGH", "CRITICAL")
    assert data["safe_to_proceed"] is False


def test_contraindication_provider_evaluation(client: TestClient, safety_env, tmp_path):
    """Detects disease-drug contraindication (e.g. NSAID in Peptic Ulcer Disease)."""
    settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
    env = safety_env
    pat_id = env["pat_a_id"]
    pat_headers = env["pat_a_headers"]
    doc_headers = env["doc_headers"]

    # Document has Peptic Ulcer Disease
    doc_content = (
        "GASTROENTEROLOGY CONSULT\n"
        "Diagnosis: Active peptic ulcer disease with gastric erosion.\n"
        "Prescribed: Omeprazole 40mg daily."
    )
    _upload_safety_doc(client, pat_id, "GI Note", doc_content, doc_headers)

    # Candidate medication: Ibuprofen
    res = client.post(
        f"/api/v1/patients/{pat_id}/safety/check",
        json={
            "candidate_medications": ["Ibuprofen 400mg TID"],
        },
        headers=pat_headers,
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    contra_alerts = [a for a in data["alerts"] if a["alert_type"] == "contraindication"]
    assert len(contra_alerts) >= 1
    assert contra_alerts[0]["severity"] == "HIGH"
    assert data["safe_to_proceed"] is False


def test_clean_safety_check_returns_safe_to_proceed(client: TestClient, safety_env, tmp_path):
    """Safe clinical regimen without conflicts returns safe_to_proceed=True and empty alerts."""
    settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
    env = safety_env
    pat_id = env["pat_a_id"]
    pat_headers = env["pat_a_headers"]
    doc_headers = env["doc_headers"]

    doc_content = (
        "ROUTINE WELLNESS NOTE\n"
        "Diagnosis: General checkup normal.\n"
        "Allergies: NKDA.\n"
        "Prescribed: Multivitamin daily."
    )
    _upload_safety_doc(client, pat_id, "Wellness Note", doc_content, doc_headers)

    res = client.post(
        f"/api/v1/patients/{pat_id}/safety/check",
        json={"candidate_medications": ["Acetaminophen 500mg PRN"]},
        headers=pat_headers,
    )
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["safe_to_proceed"] is True
    assert len(data["alerts"]) == 0
    assert "No adverse medication duplicates" in data["summary"]


def test_safety_check_patient_isolation_and_rbac(client: TestClient, safety_env, tmp_path):
    """Patient A cannot run safety checks on Patient B; unrelated doctor is forbidden."""
    settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
    env = safety_env
    pat_a_id = env["pat_a_id"]
    pat_b_headers = env["pat_b_headers"]
    unrelated_doc_headers = env["unrelated_doc_headers"]

    # Patient B attempts to run safety check on Patient A -> 403
    res_cross = client.post(
        f"/api/v1/patients/{pat_a_id}/safety/check",
        json={"candidate_medications": ["Lisinopril 10mg"]},
        headers=pat_b_headers,
    )
    assert res_cross.status_code == status.HTTP_403_FORBIDDEN

    # Unrelated Doctor attempts to run safety check on Patient A -> 403
    res_unauth_doc = client.post(
        f"/api/v1/patients/{pat_a_id}/safety/check",
        json={"candidate_medications": ["Lisinopril 10mg"]},
        headers=unrelated_doc_headers,
    )
    assert res_unauth_doc.status_code == status.HTTP_403_FORBIDDEN
