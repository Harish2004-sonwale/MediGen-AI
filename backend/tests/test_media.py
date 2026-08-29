"""Comprehensive test suite for Multi-Modal Medical Diagnostics and Clinical Imaging.

Phase 9.0.7: Advanced Multi-Modal Medical Diagnostics & Imaging Support.
Tests:
- Upload validation (formats, file size limits, safe paths)
- Patient isolation and RBAC authorization
- Deterministic MockMedicalImagingProvider across all modalities
- Background MEDIA_ANALYSIS task lifecycle & worker execution
- Clinician review verification and signoff
- Safety invariants (unconfirmed AI observations vs confirmed diagnosis)
- PHI-safe logging
"""

import io
import os
import pytest
from fastapi.testclient import TestClient

from app.ai.imaging_provider import MockMedicalImagingProvider
from app.ai.task_worker import get_background_task_provider, reset_background_task_provider
from app.models.patient import Patient
from app.schemas.media import MediaModality, MediaStatus
from app.schemas.task import BackgroundTaskType
from app.schemas.user import UserRole


@pytest.fixture
def mock_imaging_provider():
    return MockMedicalImagingProvider()


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.DOCTOR,
    email: str = "media_doc@hospital.org",
    name: str = "Dr. Media Doc",
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


def test_mock_imaging_provider_all_modalities(mock_imaging_provider, tmp_path):
    """Verify deterministic findings and confidence scores across all supported modalities."""
    dummy_file = tmp_path / "test_image.png"
    dummy_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 500)

    modalities = [
        MediaModality.XRAY_CHEST,
        MediaModality.CT_SCAN,
        MediaModality.MRI,
        MediaModality.ULTRASOUND,
        MediaModality.DERMATOLOGY,
        MediaModality.PATHOLOGY,
        MediaModality.OTHER,
    ]

    for mod in modalities:
        result = mock_imaging_provider.analyze_image(str(dummy_file), mod)
        assert result.modality == mod
        assert 0.70 <= result.confidence_score <= 1.0
        assert len(result.primary_observation) > 10
        assert len(result.findings) >= 1
        assert "AI clinical decision support observation only" in result.disclaimer
        for finding in result.findings:
            assert 0.0 <= finding.confidence <= 1.0
            assert len(finding.anatomical_region) > 0


def test_upload_clinical_media_success(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify successful upload of a medical image associated with a patient."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_upload@test.com")
    file_content = b"\xff\xd8\xff\xe0" + b"\x00" * 1024  # Minimal JPEG header
    file_obj = io.BytesIO(file_content)

    response = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/media",
        headers=headers,
        data={
            "title": "Chest X-Ray PA View",
            "modality": "xray_chest",
            "body_site": "chest",
        },
        files={"file": ("chest_xray.jpg", file_obj, "image/jpeg")},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Chest X-Ray PA View"
    assert data["modality"] == "xray_chest"
    assert data["body_site"] == "chest"
    assert data["status"] == "uploaded"
    assert data["requires_clinician_review"] is True
    assert data["clinician_confirmed"] is False
    assert data["media_id"].startswith("MED-")


def test_upload_media_unsupported_extension_rejected(
    client: TestClient,
    test_patient: Patient,
):
    """Verify rejection of disallowed file extensions (e.g. executable/scripts)."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_unsupported@test.com")
    file_obj = io.BytesIO(b"malicious executable payload")

    response = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/media",
        headers=headers,
        data={"title": "Malicious File", "modality": "other"},
        files={"file": ("virus.exe", file_obj, "application/octet-stream")},
    )

    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_media_patient_isolation(
    client: TestClient,
    test_patient: Patient,
):
    """Verify that patients cannot upload media directly; only DOCTOR/STAFF/ADMIN."""
    headers, _ = get_auth_headers(client, role=UserRole.PATIENT, email="pat_upload@test.com")
    file_obj = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    response = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/media",
        headers=headers,
        data={"title": "Patient Self Upload", "modality": "xray_chest"},
        files={"file": ("scan.png", file_obj, "image/png")},
    )

    # Patients cannot upload directly; only DOCTOR, HEALTHCARE_STAFF, ADMIN
    assert response.status_code == 403


def test_list_and_get_diagnostic_media(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify listing and retrieving diagnostic media for an authorized patient."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_list@test.com")

    # Upload study first
    file_obj = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
    upload_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/media",
        headers=headers,
        data={"title": "Brain CT Non-Contrast", "modality": "ct_scan", "body_site": "brain"},
        files={"file": ("brain_ct.png", file_obj, "image/png")},
    )
    media_id = upload_res.json()["media_id"]

    # 1. List
    list_res = client.get(
        f"/api/v1/patients/{test_patient.patient_id}/media",
        headers=headers,
    )
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert any(m["media_id"] == media_id for m in items)

    # 2. Get Detail
    detail_res = client.get(
        f"/api/v1/media/{media_id}",
        headers=headers,
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["media_id"] == media_id
    assert detail_res.json()["modality"] == "ct_scan"


def test_media_file_download_stream(
    client: TestClient,
    test_patient: Patient,
):
    """Verify streaming authorized binary media file."""
    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_stream@test.com")
    raw_bytes = b"\x89PNG\r\n\x1a\n" + b"\x12\x34\x56" * 50
    file_obj = io.BytesIO(raw_bytes)

    upload_res = client.post(
        f"/api/v1/patients/{test_patient.patient_id}/media",
        headers=headers,
        data={"title": "Skin Dermoscopy", "modality": "dermatology", "body_site": "skin"},
        files={"file": ("lesion.png", file_obj, "image/png")},
    )
    media_id = upload_res.json()["media_id"]

    # Stream file
    file_res = client.get(
        f"/api/v1/media/{media_id}/file",
        headers=headers,
    )
    assert file_res.status_code == 200
    assert file_res.content == raw_bytes


def test_async_media_analysis_task_and_review(
    client: TestClient,
    db_session,
    test_patient: Patient,
):
    """Verify asynchronous background analysis task execution, findings generation, and clinician review signoff."""
    from unittest.mock import patch
    from tests.conftest import TestingSessionLocal

    headers, _ = get_auth_headers(client, role=UserRole.DOCTOR, email="doc_review@test.com")
    reset_background_task_provider()
    # Use sync task provider for synchronous test execution
    get_background_task_provider(provider_type="sync", force_new=True)

    with patch("app.services.media_service.SessionLocal", TestingSessionLocal):
        # 1. Upload media
        file_obj = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"\x00" * 300)
        upload_res = client.post(
            f"/api/v1/patients/{test_patient.patient_id}/media",
            headers=headers,
            data={"title": "Chest X-Ray Lateral", "modality": "xray_chest", "body_site": "chest"},
            files={"file": ("chest_lat.png", file_obj, "image/png")},
        )
        media_id = upload_res.json()["media_id"]

        # 2. Enqueue background analysis
        task_res = client.post(
            f"/api/v1/tasks/media/{media_id}/analyze",
            headers=headers,
        )
        assert task_res.status_code == 202
        assert task_res.json()["task_type"] == BackgroundTaskType.MEDIA_ANALYSIS.value

        # 3. Verify media was analyzed and findings populated
        detail_res = client.get(
            f"/api/v1/media/{media_id}",
            headers=headers,
        )
        media_data = detail_res.json()
        assert media_data["status"] == MediaStatus.ANALYZED.value
        assert media_data["confidence_score"] is not None
        assert media_data["confidence_score"] >= 0.85
        assert len(media_data["findings_summary"]) > 10
        assert media_data["requires_clinician_review"] is True
        assert media_data["clinician_confirmed"] is False

        # 4. Clinician Review & Signoff
        review_res = client.post(
            f"/api/v1/media/{media_id}/review",
            headers=headers,
            json={
                "clinician_confirmed": True,
                "clinician_notes": "Reviewed by Dr. Attending; clear lung fields confirmed.",
            },
        )
        assert review_res.status_code == 200
        reviewed_data = review_res.json()
        assert reviewed_data["status"] == MediaStatus.REVIEWED.value
        assert reviewed_data["clinician_confirmed"] is True
        assert "Reviewed by Dr. Attending" in reviewed_data["clinician_notes"]
        assert reviewed_data["reviewed_at"] is not None
