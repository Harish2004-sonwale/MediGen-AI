"""Comprehensive test suite for Clinical Notes, AI Scribe Synthesis & Signoff.

Phase 9.0.8: Automated Clinical Documentation, AI Scribe Synthesis & Structured Note Generation.
Tests:
- Deterministic mock scribe synthesis across all 5 note types (SOAP, Consultation, Discharge, Procedure, Referral)
- Manual draft creation and field validation
- Clinical note listing and detail retrieval
- Draft editing and legal immutability enforcement for finalized notes
- Background task worker NOTE_SYNTHESIS lifecycle and execution
- Attending physician verification and signoff
- RBAC and patient data isolation
- Assistive clinical decision support disclaimer invariants
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.ai.scribe_provider import MockClinicalScribeProvider, get_scribe_provider
from app.ai.task_worker import get_background_task_provider, reset_background_task_provider
from app.models.patient import Patient
from app.models.user import UserRole
from app.schemas.note import NoteStatus, NoteType
from app.schemas.task import BackgroundTaskType
from tests.conftest import TestingSessionLocal


@pytest.fixture
def mock_scribe_provider():
    return MockClinicalScribeProvider()


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "notes_doc@hospital.org",
    name: str = "Dr. Notes Scribe",
) -> tuple[dict[str, str], int]:
    """Register and login helper returning authorization headers and user ID."""
    client.post(
        "/api/v1/auth/register",
        json={
            "name": name,
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
    user_id = login_res.json()["user"]["id"]
    return {"Authorization": f"Bearer {token}"}, user_id


def test_mock_scribe_provider_all_note_types(mock_scribe_provider):
    """Verify deterministic synthesis and structure across all 5 note types."""
    note_types = [
        NoteType.SOAP,
        NoteType.CONSULTATION,
        NoteType.DISCHARGE_SUMMARY,
        NoteType.PROCEDURE_NOTE,
        NoteType.REFERRAL_LETTER,
    ]

    for nt in note_types:
        content_json, raw_text = mock_scribe_provider.synthesize_note(
            patient_name="Eleanor Vance",
            patient_age=42,
            patient_gender="female",
            note_type=nt,
            encounter_assessment="Hypertension with mild headache.",
            encounter_plan="Initiate ACE inhibitor and low sodium diet.",
            medications=["Lisinopril 10mg daily"],
            allergies=["Penicillin"],
            imaging_findings=["Clear chest x-ray"],
            custom_instructions="Focus on cardiovascular risk.",
        )

        assert isinstance(content_json, dict)
        assert len(content_json) >= 3
        assert len(raw_text) > 100
        assert "AI CLINICAL SCRIBE DRAFT" in raw_text
        assert "Eleanor Vance" in raw_text or "Eleanor Vance" in str(content_json)


def test_create_and_get_manual_clinical_note(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify creating a manual clinical note draft and retrieving it."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_manual_note@test.com")

    # 1. Create Manual Draft
    create_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/notes",
        headers=headers,
        json={
            "title": "Initial Cardiology Consult",
            "note_type": "soap",
            "raw_text": "SUBJECTIVE: Patient reports exertional dyspnea.\nOBJECTIVE: Vitals normal.\nASSESSMENT: Class I Angina.\nPLAN: Beta blocker.",
        },
    )
    assert create_res.status_code == 201
    data = create_res.json()
    assert data["title"] == "Initial Cardiology Consult"
    assert data["note_type"] == "soap"
    assert data["status"] == "draft"
    assert data["is_ai_generated"] is False
    assert data["requires_clinician_review"] is True
    note_id = data["note_id"]

    # 2. Get Note
    get_res = client.get(
        f"/api/v1/notes/{note_id}",
        headers=headers,
    )
    assert get_res.status_code == 200
    assert get_res.json()["note_id"] == note_id

    # 3. List Notes for Patient
    list_res = client.get(
        f"/api/v1/patients/{test_patient.patient_id}/notes",
        headers=headers,
    )
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(n["note_id"] == note_id for n in items)


def test_update_draft_note_and_immutability_after_signoff(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify editing a draft note and immutability once finalized."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_immutability@test.com")

    # 1. Create Draft
    create_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/notes",
        headers=headers,
        json={
            "title": "Draft SOAP Note",
            "note_type": "soap",
            "raw_text": "Original text before editing.",
        },
    )
    note_id = create_res.json()["note_id"]

    # 2. Update Draft (Should Succeed)
    update_res = client.patch(
        f"/api/v1/notes/{note_id}",
        headers=headers,
        json={
            "title": "Updated Draft SOAP Note",
            "raw_text": "Amended text in draft mode.",
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Updated Draft SOAP Note"
    assert update_res.json()["raw_text"] == "Amended text in draft mode."

    # 3. Physician Signoff
    signoff_res = client.post(
        f"/api/v1/notes/{note_id}/signoff",
        headers=headers,
        json={
            "confirm_accuracy": True,
            "clinician_notes": "Reviewed and approved by attending physician.",
        },
    )
    assert signoff_res.status_code == 200
    assert signoff_res.json()["status"] == "finalized"
    assert signoff_res.json()["requires_clinician_review"] is False
    assert signoff_res.json()["signed_at"] is not None

    # 4. Attempt Update on Finalized Note (MUST FAIL with 400)
    failed_update = client.patch(
        f"/api/v1/notes/{note_id}",
        headers=headers,
        json={"raw_text": "Illegal mutation of finalized note."},
    )
    assert failed_update.status_code == 400
    assert "Cannot modify a finalized clinical note" in failed_update.json()["detail"]


def test_async_ai_scribe_synthesis_and_signoff(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify background task execution for AI Scribe note synthesis and physician finalization."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_scribe_task@test.com")
    reset_background_task_provider()
    get_background_task_provider(provider_type="sync", force_new=False)


    with patch("app.services.note_service.SessionLocal", TestingSessionLocal):
        # 1. Enqueue Synthesis
        task_res = client.post(
            "/api/v1/tasks/notes/synthesize",
            headers=headers,
            json={
                "patient_id": test_patient.patient_id,
                "note_type": "soap",
                "custom_instructions": "Focus on recent blood pressure readings.",
            },
        )
        assert task_res.status_code == 202
        assert task_res.json()["task_type"] == BackgroundTaskType.NOTE_SYNTHESIS.value

        # 2. Check Patient Notes to retrieve the AI-synthesized note
        list_res = client.get(
            f"/api/v1/patients/{test_patient.patient_id}/notes",
            headers=headers,
        )
        assert list_res.status_code == 200
        items = list_res.json()["items"]
        assert len(items) >= 1
        synth_note = items[0]

        assert synth_note["is_ai_generated"] is True
        assert synth_note["status"] == NoteStatus.DRAFT.value
        assert synth_note["requires_clinician_review"] is True
        assert "SOAP Note" in synth_note["title"]

        # 3. Physician Signoff
        signoff_res = client.post(
            f"/api/v1/notes/{synth_note['note_id']}/signoff",
            headers=headers,
            json={
                "confirm_accuracy": True,
                "clinician_notes": "AI draft verified and confirmed.",
            },
        )
        assert signoff_res.status_code == 200
        assert signoff_res.json()["status"] == NoteStatus.FINALIZED.value


def test_patient_role_cannot_create_or_signoff_notes(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify that patient users cannot draft notes or perform physician signoff."""
    headers, _ = get_auth_headers(client, role=UserRole.PATIENT, email="patient_unauth_note@test.com")

    # 1. Patient attempts note creation -> 403 Forbidden
    create_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/notes",
        headers=headers,
        json={
            "title": "Patient Self Note",
            "note_type": "soap",
            "raw_text": "Unauthorized text.",
        },
    )
    assert create_res.status_code == 403

    # 2. Patient attempts synthesis task -> 403 Forbidden
    synth_res = client.post(
        "/api/v1/tasks/notes/synthesize",
        headers=headers,
        json={
            "patient_id": test_patient.patient_id,
            "note_type": "soap",
        },
    )
    assert synth_res.status_code == 403
