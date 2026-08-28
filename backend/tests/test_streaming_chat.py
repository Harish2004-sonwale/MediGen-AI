"""Tests for Server-Sent Events (SSE) Streaming Clinical Chat.

Phase 8.8: SSE Streaming Clinical Chat, Session Persistence & Grounded Retrieval.
"""

from datetime import datetime, timezone
import io
import json
from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.ai.context_builder import INSUFFICIENT_INFORMATION_MESSAGE
from app.schemas.user import UserRole


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.PATIENT,
    email: str = "patient_stream@hospital.org",
    name: str = "Stream User",
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


def parse_sse_events(raw_body: str) -> list[tuple[str, dict]]:
    """Parse raw SSE text output into a list of (event_type, parsed_data_dict) pairs."""
    events = []
    current_event = "message"
    for line in raw_body.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("event:"):
            current_event = line[6:].strip()
        elif line.startswith("data:"):
            raw_data = line[5:].strip()
            try:
                parsed_data = json.loads(raw_data)
            except Exception:
                parsed_data = {"raw": raw_data}
            events.append((current_event, parsed_data))
            current_event = "message"
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_authenticated_sse_streaming_success(client: TestClient):
    """Test full SSE streaming message generation with tokens, citations, and persistence."""
    admin_headers, _ = get_auth_headers(
        client, role=UserRole.ADMIN, email="admin_stream1@hospital.org", name="Admin Stream"
    )
    pat_headers, _ = get_auth_headers(
        client, role=UserRole.PATIENT, email="anna_stream@patient.org", name="Anna Stream"
    )

    # 1. Create Patient
    pat_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Anna",
            "last_name": "Stream",
            "date_of_birth": "1991-03-15",
            "gender": "female",
            "email": "anna_stream@patient.org",
        },
        headers=admin_headers,
    )
    patient_id = pat_res.json()["patient_id"]

    # 2. Upload Document
    doc_text = (
        "CLINICAL NOTE\n"
        "Patient Anna Stream presented with persistent migraines.\n"
        "Diagnosis: Chronic migraine without aura.\n"
        "Prescribed: Sumatriptan 50mg as needed at headache onset.\n"
        "Plan: Maintain headache diary."
    )
    client.post(
        "/api/v1/documents/upload",
        files={"file": ("migraine.txt", io.BytesIO(doc_text.encode("utf-8")), "text/plain")},
        data={
            "patient_id": patient_id,
            "title": "Migraine Evaluation",
            "document_type": "clinical_note",
        },
        headers=admin_headers,
    )

    # 3. Create Session
    session_res = client.post(
        "/api/v1/chat/sessions",
        json={"patient_id": patient_id, "title": "Migraine Treatment Chat"},
        headers=pat_headers,
    )
    session_id = session_res.json()["session_id"]

    # 4. Stream Message via SSE
    stream_res = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages/stream",
        json={"message": "What medication was prescribed for my migraines?"},
        headers=pat_headers,
    )
    assert stream_res.status_code == status.HTTP_200_OK
    assert "text/event-stream" in stream_res.headers["content-type"]

    events = parse_sse_events(stream_res.text)
    event_types = [e[0] for e in events]

    assert "start" in event_types
    assert "delta" in event_types
    assert "done" in event_types

    # Collect full text from deltas
    deltas = [e[1]["text"] for e in events if e[0] == "delta"]
    full_text = "".join(deltas)
    assert "sumatriptan" in full_text.lower()

    # 5. Verify PostgreSQL Persistence
    detail_res = client.get(f"/api/v1/chat/sessions/{session_id}", headers=pat_headers)
    assert detail_res.status_code == status.HTTP_200_OK
    messages = detail_res.json()["messages"]
    assert len(messages) == 2  # 1 user + 1 assistant
    assert messages[0]["sender_role"] == "user"
    assert messages[1]["sender_role"] == "assistant"
    assert "sumatriptan" in messages[1]["content"].lower()


def test_sse_streaming_insufficient_information(client: TestClient):
    """Test that unrelated questions stream the exact insufficient information message."""
    admin_headers, _ = get_auth_headers(
        client, role=UserRole.ADMIN, email="admin_stream2@hospital.org", name="Admin Stream2"
    )
    pat_headers, _ = get_auth_headers(
        client, role=UserRole.PATIENT, email="bob_stream@patient.org", name="Bob Stream"
    )

    # Create Patient with no uploaded documents
    pat_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Bob",
            "last_name": "Stream",
            "date_of_birth": "1975-08-20",
            "gender": "male",
            "email": "bob_stream@patient.org",
        },
        headers=admin_headers,
    )
    patient_id = pat_res.json()["patient_id"]

    session_res = client.post(
        "/api/v1/chat/sessions",
        json={"patient_id": patient_id, "title": "Empty Session"},
        headers=pat_headers,
    )
    session_id = session_res.json()["session_id"]

    stream_res = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages/stream",
        json={"message": "What surgery did I have?"},
        headers=pat_headers,
    )
    assert stream_res.status_code == status.HTTP_200_OK
    events = parse_sse_events(stream_res.text)

    deltas = [e[1]["text"] for e in events if e[0] == "delta"]
    full_text = "".join(deltas)
    assert INSUFFICIENT_INFORMATION_MESSAGE.lower() in full_text.lower()

    done_event = [e[1] for e in events if e[0] == "done"][0]
    assert done_event["insufficient_information"] is True


def test_sse_streaming_unauthorized_patient_rejected(client: TestClient):
    """Patient B must be rejected when attempting to stream to Patient A's session."""
    admin_headers, _ = get_auth_headers(
        client, role=UserRole.ADMIN, email="admin_stream3@hospital.org", name="Admin Stream3"
    )
    pat_a_headers, _ = get_auth_headers(
        client, role=UserRole.PATIENT, email="patient_a_stream@patient.org", name="Patient A"
    )
    pat_b_headers, _ = get_auth_headers(
        client, role=UserRole.PATIENT, email="patient_b_stream@patient.org", name="Patient B"
    )

    pat_a_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Patient",
            "last_name": "A",
            "date_of_birth": "1990-01-01",
            "gender": "female",
            "email": "patient_a_stream@patient.org",
        },
        headers=admin_headers,
    )
    patient_a_id = pat_a_res.json()["patient_id"]

    session_res = client.post(
        "/api/v1/chat/sessions",
        json={"patient_id": patient_a_id, "title": "Patient A Session"},
        headers=pat_a_headers,
    )
    session_id = session_res.json()["session_id"]

    # Patient B attempts to stream message to Patient A session
    res = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages/stream",
        json={"message": "What is Patient A's diagnosis?"},
        headers=pat_b_headers,
    )
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_sse_streaming_closed_session_rejected(client: TestClient):
    """Attempting to stream to a closed session must be rejected with 400 Bad Request."""
    admin_headers, _ = get_auth_headers(
        client, role=UserRole.ADMIN, email="admin_stream4@hospital.org", name="Admin Stream4"
    )
    pat_headers, _ = get_auth_headers(
        client, role=UserRole.PATIENT, email="closed_stream@patient.org", name="Closed Stream"
    )

    pat_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Closed",
            "last_name": "Patient",
            "date_of_birth": "1985-05-05",
            "gender": "male",
            "email": "closed_stream@patient.org",
        },
        headers=admin_headers,
    )
    patient_id = pat_res.json()["patient_id"]

    session_res = client.post(
        "/api/v1/chat/sessions",
        json={"patient_id": patient_id, "title": "To Close"},
        headers=pat_headers,
    )
    session_id = session_res.json()["session_id"]

    # Close session
    client.delete(f"/api/v1/chat/sessions/{session_id}", headers=pat_headers)

    # Attempt to stream
    res = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages/stream",
        json={"message": "Hello?"},
        headers=pat_headers,
    )
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_non_streaming_endpoint_remains_functional(client: TestClient):
    """Ensure existing POST /api/v1/chat/sessions/{session_id}/messages works identically."""
    admin_headers, _ = get_auth_headers(
        client, role=UserRole.ADMIN, email="admin_stream5@hospital.org", name="Admin Stream5"
    )
    pat_headers, _ = get_auth_headers(
        client, role=UserRole.PATIENT, email="nonstream@patient.org", name="Non Stream"
    )

    pat_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Non",
            "last_name": "Stream",
            "date_of_birth": "1992-02-02",
            "gender": "female",
            "email": "nonstream@patient.org",
        },
        headers=admin_headers,
    )
    patient_id = pat_res.json()["patient_id"]

    doc_text = "CLINICAL NOTE\nDiagnosis: Hypertension.\nPrescribed: Lisinopril 10mg daily."
    client.post(
        "/api/v1/documents/upload",
        files={"file": ("htn.txt", io.BytesIO(doc_text.encode("utf-8")), "text/plain")},
        data={"patient_id": patient_id, "title": "HTN Note", "document_type": "clinical_note"},
        headers=admin_headers,
    )

    session_res = client.post(
        "/api/v1/chat/sessions",
        json={"patient_id": patient_id, "title": "HTN Consult"},
        headers=pat_headers,
    )
    session_id = session_res.json()["session_id"]

    msg_res = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"message": "What is my blood pressure medication?"},
        headers=pat_headers,
    )
    assert msg_res.status_code == status.HTTP_200_OK
    assert "lisinopril" in msg_res.json()["content"].lower()
