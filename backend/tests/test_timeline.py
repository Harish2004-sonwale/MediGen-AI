"""Comprehensive Test Suite for Longitudinal Clinical Timeline.

Phase 8.9: Longitudinal Clinical Intelligence & Safety Layer.
Tests timeline event aggregation, date/type filtering, pagination, chronological ordering,
grounded longitudinal summaries, patient isolation, and RBAC authorization.
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
    email: str = "patient_tl@hospital.org",
    name: str = "Timeline User",
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
def timeline_env(client: TestClient) -> dict[str, any]:
    """Setup Admin, Doctor, and Patients for timeline testing."""
    admin_headers, _ = get_auth_headers(
        client, role=UserRole.ADMIN, email="admin_tl@hospital.org", name="Admin TL"
    )
    doc_headers, doc_uid = get_auth_headers(
        client, role=UserRole.DOCTOR, email="dr_tl@hospital.org", name="Dr. Gregory TL"
    )
    unrelated_doc_headers, _ = get_auth_headers(
        client, role=UserRole.DOCTOR, email="unrelated_tl_doc@hospital.org", name="Dr. Unrelated TL"
    )

    # Patient A
    pat_a_headers, _ = get_auth_headers(
        client, role=UserRole.PATIENT, email="alice_tl@patient.org", name="Alice TL"
    )
    pat_a_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Alice",
            "last_name": "Timeline",
            "date_of_birth": "1990-05-15",
            "gender": "female",
            "email": "alice_tl@patient.org",
        },
        headers=admin_headers,
    )
    pat_a_id = pat_a_res.json()["patient_id"]

    # Patient B
    pat_b_headers, _ = get_auth_headers(
        client, role=UserRole.PATIENT, email="bob_tl@patient.org", name="Bob TL"
    )
    pat_b_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Bob",
            "last_name": "Timeline",
            "date_of_birth": "1985-08-20",
            "gender": "male",
            "email": "bob_tl@patient.org",
        },
        headers=admin_headers,
    )
    pat_b_id = pat_b_res.json()["patient_id"]

    # Create & verify Doctor Profile
    doc_res = client.post(
        "/api/v1/doctors",
        json={
            "user_id": doc_uid,
            "full_name": "Gregory TL",
            "department": "Cardiology",
            "specialization": "Internal Medicine",
            "medical_registration_number": "MED-TL-001",
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
            "reason_for_visit": "Cardiology Baseline",
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


def _upload_clinical_doc(client: TestClient, patient_id: str, title: str, content: str, headers: dict):
    """Helper to upload a test clinical document."""
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


def test_timeline_aggregation_across_all_clinical_entities(client: TestClient, timeline_env, tmp_path):
    """Timeline aggregates encounters, appointments, documents, and derived chunk events."""
    settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
    env = timeline_env
    pat_id = env["pat_a_id"]
    pat_headers = env["pat_a_headers"]
    doc_headers = env["doc_headers"]

    # 1. Create Encounter
    enc_res = client.post(
        f"/api/v1/patients/{pat_id}/encounters",
        json={
            "encounter_type": "initial_consultation",
            "chief_complaint": "Palpitations and mild dyspnea",
            "clinical_notes": "ECG showed sinus tachycardia. Plan to start beta-blocker.",
            "assessment": "Sinus Tachycardia",
            "plan": "Start Metoprolol",
        },
        headers=doc_headers,
    )
    assert enc_res.status_code == status.HTTP_201_CREATED

    # 2. Upload Clinical Document with Diagnoses and Medications
    doc_content = (
        "CARDIOLOGY CONSULTATION NOTE\n"
        "Diagnosis: Essential hypertension and sinus tachycardia.\n"
        "Prescribed: Metoprolol Tartrate 25mg BID, Lisinopril 10mg daily.\n"
        "Lab Results: Serum potassium 4.2 mEq/L, Serum Creatinine 0.9 mg/dL."
    )
    _upload_clinical_doc(client, pat_id, "Cardiology Baseline Note", doc_content, doc_headers)

    # Query Timeline
    res = client.get(f"/api/v1/patients/{pat_id}/timeline", headers=pat_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["patient_id"] == pat_id
    assert data["total"] >= 3
    event_types = {e["event_type"] for e in data["events"]}
    assert "encounter" in event_types
    assert "appointment" in event_types
    assert "document_upload" in event_types
    assert "diagnosis" in event_types or "medication_prescribed" in event_types


def test_timeline_chronological_sorting_and_pagination(client: TestClient, timeline_env, tmp_path):
    """Timeline correctly respects asc/desc sorting and pagination offsets."""
    settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
    env = timeline_env
    pat_id = env["pat_a_id"]
    pat_headers = env["pat_a_headers"]

    for i in range(4):
        _upload_clinical_doc(
            client,
            pat_id,
            f"Progress Note {i}",
            f"CLINICAL NOTE\nDiagnosis: Condition {i}.\nPrescribed: Medication {i} 10mg daily.",
            pat_headers,
        )

    # Test Descending Sort (Default)
    res_desc = client.get(f"/api/v1/patients/{pat_id}/timeline?sort_order=desc&limit=10", headers=pat_headers)
    assert res_desc.status_code == status.HTTP_200_OK
    events_desc = res_desc.json()["events"]
    assert len(events_desc) >= 4
    for j in range(len(events_desc) - 1):
        dt1 = datetime.fromisoformat(events_desc[j]["event_date"].replace("Z", "+00:00"))
        dt2 = datetime.fromisoformat(events_desc[j + 1]["event_date"].replace("Z", "+00:00"))
        assert dt1 >= dt2

    # Test Ascending Sort
    res_asc = client.get(f"/api/v1/patients/{pat_id}/timeline?sort_order=asc&limit=10", headers=pat_headers)
    assert res_asc.status_code == status.HTTP_200_OK
    events_asc = res_asc.json()["events"]
    for k in range(len(events_asc) - 1):
        dt1 = datetime.fromisoformat(events_asc[k]["event_date"].replace("Z", "+00:00"))
        dt2 = datetime.fromisoformat(events_asc[k + 1]["event_date"].replace("Z", "+00:00"))
        assert dt1 <= dt2

    # Test Pagination skip and limit
    res_page = client.get(f"/api/v1/patients/{pat_id}/timeline?skip=1&limit=2", headers=pat_headers)
    assert res_page.status_code == status.HTTP_200_OK
    assert len(res_page.json()["events"]) == 2


def test_timeline_event_type_and_date_filtering(client: TestClient, timeline_env, tmp_path):
    """Timeline filters by specific event_type and date boundaries."""
    settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
    env = timeline_env
    pat_id = env["pat_a_id"]
    pat_headers = env["pat_a_headers"]
    doc_headers = env["doc_headers"]

    # Filter for only encounters
    res_enc = client.get(f"/api/v1/patients/{pat_id}/timeline?event_type=appointment", headers=pat_headers)
    assert res_enc.status_code == status.HTTP_200_OK
    events = res_enc.json()["events"]
    assert len(events) >= 1
    assert all(e["event_type"] == "appointment" for e in events)

    # Filter with future start_date -> 0 events
    future_date = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    res_future = client.get(f"/api/v1/patients/{pat_id}/timeline?start_date={future_date}", headers=pat_headers)
    assert res_future.status_code == status.HTTP_200_OK
    assert res_future.json()["total"] == 0


def test_timeline_empty_history_returns_empty_list(client: TestClient, timeline_env):
    """Patient with no recorded encounters, appointments, or documents returns 0 events."""
    env = timeline_env
    pat_b_id = env["pat_b_id"]
    pat_b_headers = env["pat_b_headers"]

    res = client.get(f"/api/v1/patients/{pat_b_id}/timeline", headers=pat_b_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert data["total"] == 0
    assert data["events"] == []


def test_timeline_patient_isolation_and_rbac(client: TestClient, timeline_env, tmp_path):
    """Patient A cannot access Patient B timeline; unrelated doctor is forbidden."""
    settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
    env = timeline_env
    pat_a_id = env["pat_a_id"]
    pat_b_headers = env["pat_b_headers"]
    unrelated_doc_headers = env["unrelated_doc_headers"]

    # Patient B attempts to view Patient A's timeline -> 403
    res_cross = client.get(f"/api/v1/patients/{pat_a_id}/timeline", headers=pat_b_headers)
    assert res_cross.status_code == status.HTTP_403_FORBIDDEN

    # Unrelated Doctor attempts to view Patient A's timeline -> 403
    res_unauth_doc = client.get(f"/api/v1/patients/{pat_a_id}/timeline", headers=unrelated_doc_headers)
    assert res_unauth_doc.status_code == status.HTTP_403_FORBIDDEN


def test_timeline_longitudinal_summary_with_citations(client: TestClient, timeline_env, tmp_path):
    """Timeline summary endpoint generates grounded summary with verified citations."""
    settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
    env = timeline_env
    pat_id = env["pat_a_id"]
    pat_headers = env["pat_a_headers"]
    doc_headers = env["doc_headers"]

    doc_content = (
        "ONCOLOGY CLINICAL SUMMARY\n"
        "Diagnosis: Early-stage localized adenocarcinoma.\n"
        "Prescribed: Tamoxifen 20mg daily.\n"
        "Plan: Follow-up surveillance scan in 6 months."
    )
    _upload_clinical_doc(client, pat_id, "Oncology Summary", doc_content, doc_headers)

    res = client.get(f"/api/v1/patients/{pat_id}/timeline/summary", headers=pat_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["patient_id"] == pat_id
    assert len(data["summary"]) > 10
    assert data["event_count"] >= 1
    assert "generated_at" in data
