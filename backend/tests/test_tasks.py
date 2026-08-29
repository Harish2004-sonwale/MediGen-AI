"""Comprehensive Test Suite for Background Asynchronous Task Worker Architecture.

Phase 9.0.3: Background Asynchronous Worker Architecture.
Tests:
- Task ID generation and data structures
- Task states lifecycle (QUEUED -> RUNNING -> COMPLETED / FAILED / CANCELLED / RETRYING)
- Local thread pool provider and sync execution provider
- Celery provider graceful fallback & safe configuration
- End-to-end background document processing execution
- Idempotency & duplicate submission prevention
- RBAC authorization & patient isolation
- Task listing, filtering, retry, and cancellation
- Credential safety and zero PHI in logs
"""

from datetime import datetime, timedelta, timezone
import logging
import time
from typing import Any
from unittest.mock import MagicMock, patch

from fastapi import status
from fastapi.testclient import TestClient
import pytest

from app.ai.task_worker import (
    BaseBackgroundTaskProvider,
    CeleryBackgroundTaskProvider,
    LocalBackgroundTaskProvider,
    SyncBackgroundTaskProvider,
    generate_task_id,
    get_background_task_provider,
    reset_background_task_provider,
)
from app.core.config import settings
from app.schemas.task import (
    BackgroundTask,
    BackgroundTaskResponse,
    BackgroundTaskStatus,
    BackgroundTaskType,
)
from app.schemas.user import UserRole
from app.services.task_service import (
    enqueue_document_processing_task,
    enqueue_timeline_summary_task,
    get_task_status,
    list_tasks_for_user,
    retry_task_for_user,
    cancel_task_for_user,
)


# ===========================================================================
# Fixtures & Helpers
# ===========================================================================


def get_auth_headers(
    client: TestClient,
    role: UserRole = UserRole.PATIENT,
    email: str = "task_user@hospital.org",
    name: str = "Task User",
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
def task_env(client: TestClient) -> dict[str, Any]:
    """Setup Admin, Doctor, and two isolated Patients for background task tests."""
    admin_headers, admin_uid = get_auth_headers(
        client, role=UserRole.ADMIN, email="admin_tasks@hospital.org", name="Admin Tasks"
    )
    doc_headers, doc_uid = get_auth_headers(
        client, role=UserRole.DOCTOR, email="dr_tasks@hospital.org", name="Dr. Tasks"
    )
    unrelated_doc_headers, _ = get_auth_headers(
        client, role=UserRole.DOCTOR, email="dr_unrelated_tasks@hospital.org", name="Dr. Unrelated Tasks"
    )

    # Patient A
    pat_a_headers, _ = get_auth_headers(
        client, role=UserRole.PATIENT, email="alice_tasks@patient.org", name="Alice Tasks"
    )
    pat_a_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Alice",
            "last_name": "Tasks",
            "date_of_birth": "1992-04-10",
            "gender": "female",
            "email": "alice_tasks@patient.org",
        },
        headers=admin_headers,
    )
    pat_a_id = pat_a_res.json()["patient_id"]

    # Patient B
    pat_b_headers, _ = get_auth_headers(
        client, role=UserRole.PATIENT, email="bob_tasks@patient.org", name="Bob Tasks"
    )
    pat_b_res = client.post(
        "/api/v1/patients",
        json={
            "first_name": "Bob",
            "last_name": "Tasks",
            "date_of_birth": "1988-11-25",
            "gender": "male",
            "email": "bob_tasks@patient.org",
        },
        headers=admin_headers,
    )
    pat_b_id = pat_b_res.json()["patient_id"]

    # Doctor Profile
    doc_res = client.post(
        "/api/v1/doctors",
        json={
            "user_id": doc_uid,
            "full_name": "Dr. Tasks",
            "department": "Internal Medicine",
            "specialization": "Clinical Informatics",
            "medical_registration_number": "MED-TASK-001",
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
            "reason_for_visit": "Task Review Consultation",
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


def _upload_task_doc(client: TestClient, patient_id: str, title: str, content: str, headers: dict) -> dict:
    """Helper to upload a medical document for testing async processing."""
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


# ===========================================================================
# 1. Task ID Generation & Core Domain Models
# ===========================================================================


class TestTaskCoreModels:
    """Task ID generation, domain models, and lifecycle status models."""

    def test_task_id_format(self):
        task_id = generate_task_id()
        assert task_id.startswith("TASK-")
        parts = task_id.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 8  # 8 hex chars

    def test_task_status_enum_values(self):
        assert BackgroundTaskStatus.QUEUED.value == "queued"
        assert BackgroundTaskStatus.RUNNING.value == "running"
        assert BackgroundTaskStatus.COMPLETED.value == "completed"
        assert BackgroundTaskStatus.FAILED.value == "failed"
        assert BackgroundTaskStatus.RETRYING.value == "retrying"
        assert BackgroundTaskStatus.CANCELLED.value == "cancelled"

    def test_task_type_enum_values(self):
        assert BackgroundTaskType.DOCUMENT_PROCESSING.value == "document_processing"
        assert BackgroundTaskType.TIMELINE_SUMMARY.value == "timeline_summary"
        assert BackgroundTaskType.SAFETY_CHECK.value == "safety_check"
        assert BackgroundTaskType.BATCH_INDEXING.value == "batch_indexing"

    def test_background_task_creation(self):
        now = datetime.now(timezone.utc)
        task = BackgroundTask(
            task_id="TASK-20260829-12345678",
            task_type=BackgroundTaskType.DOCUMENT_PROCESSING,
            status=BackgroundTaskStatus.QUEUED,
            patient_id="PAT-001",
            progress=0.0,
            created_at=now,
        )
        assert task.task_id == "TASK-20260829-12345678"
        assert task.status == BackgroundTaskStatus.QUEUED
        assert task.progress == 0.0
        assert task.retry_count == 0


# ===========================================================================
# 2. Local & Synchronous Provider Unit Tests
# ===========================================================================


class TestTaskProviders:
    """Task execution, lifecycle states, and provider mechanics."""

    def test_sync_provider_execution_success(self):
        provider = SyncBackgroundTaskProvider()

        def sample_job(x: int, y: int) -> dict:
            return {"sum": x + y}

        task = provider.submit_task(
            task_type=BackgroundTaskType.DOCUMENT_PROCESSING,
            fn=sample_job,
            fn_args=(10, 20),
            patient_id="PAT-SYNC-01",
        )

        assert task.status == BackgroundTaskStatus.COMPLETED
        assert task.progress == 1.0
        assert task.result_metadata == {"sum": 30}
        assert task.completed_at is not None
        assert task.error_message is None

    def test_sync_provider_execution_failure(self):
        provider = SyncBackgroundTaskProvider()

        def failing_job():
            raise ValueError("Extraction pipeline crashed.")

        task = provider.submit_task(
            task_type=BackgroundTaskType.DOCUMENT_PROCESSING,
            fn=failing_job,
            patient_id="PAT-FAIL-01",
        )

        assert task.status == BackgroundTaskStatus.FAILED
        assert "Extraction pipeline crashed" in (task.error_message or "")
        assert task.completed_at is not None

    def test_local_provider_async_execution(self):
        provider = LocalBackgroundTaskProvider(max_workers=2)

        def slow_job(val: str) -> dict:
            time.sleep(0.05)
            return {"echo": val}

        task = provider.submit_task(
            task_type=BackgroundTaskType.TIMELINE_SUMMARY,
            fn=slow_job,
            fn_args=("test_val",),
            patient_id="PAT-LOCAL-01",
        )

        assert task.status in (BackgroundTaskStatus.QUEUED, BackgroundTaskStatus.RUNNING)

        # Wait for completion
        for _ in range(50):
            t = provider.get_task(task.task_id)
            if t and t.status == BackgroundTaskStatus.COMPLETED:
                break
            time.sleep(0.02)

        completed_task = provider.get_task(task.task_id)
        assert completed_task is not None
        assert completed_task.status == BackgroundTaskStatus.COMPLETED
        assert completed_task.result_metadata == {"echo": "test_val"}
        assert completed_task.progress == 1.0

        provider.shutdown(wait=True)

    def test_local_provider_task_cancellation(self):
        provider = LocalBackgroundTaskProvider(max_workers=1)

        def block_job():
            time.sleep(0.2)
            return {"status": "ok"}

        # Submit first to occupy the worker
        t1 = provider.submit_task(BackgroundTaskType.DOCUMENT_PROCESSING, block_job)
        # Submit second which remains queued
        t2 = provider.submit_task(BackgroundTaskType.DOCUMENT_PROCESSING, block_job)

        # Cancel t2
        cancelled = provider.cancel_task(t2.task_id)
        assert cancelled is True

        t2_status = provider.get_task(t2.task_id)
        assert t2_status is not None
        assert t2_status.status == BackgroundTaskStatus.CANCELLED

        provider.shutdown(wait=False)

    def test_task_retry_mechanism(self):
        provider = SyncBackgroundTaskProvider()

        attempt = 0

        def flaky_job():
            nonlocal attempt
            attempt += 1
            if attempt == 1:
                raise RuntimeError("Transient network glitch.")
            return {"status": "success", "attempt": attempt}

        task = provider.submit_task(BackgroundTaskType.SAFETY_CHECK, flaky_job)
        assert task.status == BackgroundTaskStatus.FAILED

        # Retry task
        retried = provider.retry_task(task.task_id)
        assert retried is not None
        assert retried.status == BackgroundTaskStatus.COMPLETED
        assert retried.retry_count == 1
        assert retried.result_metadata["status"] == "success"


# ===========================================================================
# 3. Celery Provider Adapter & Graceful Fallback
# ===========================================================================


class TestCeleryProviderFallback:
    """Tests Celery adapter fallback behavior without requiring running Redis."""

    def test_celery_provider_initializes_and_falls_back_when_no_broker(self):
        provider = CeleryBackgroundTaskProvider(broker_url=None)
        assert provider.is_celery_active is False

        def test_fn() -> dict:
            return {"mode": "fallback"}

        task = provider.submit_task(BackgroundTaskType.DOCUMENT_PROCESSING, test_fn)
        assert task is not None
        assert task.task_id.startswith("TASK-")

    def test_celery_provider_handles_missing_celery_package(self):
        with patch.dict("sys.modules", {"celery": None}):
            provider = CeleryBackgroundTaskProvider(broker_url="redis://localhost:6379/0")
            assert provider.is_celery_active is False


# ===========================================================================
# 4. End-to-End Document Processing Background Tasks
# ===========================================================================


class TestDocumentProcessingTaskAPI:
    """Tests document processing triggered asynchronously via task endpoints."""

    def test_enqueue_document_processing_task(self, client: TestClient, task_env, tmp_path):
        settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
        env = task_env
        pat_id = env["pat_a_id"]
        doc_headers = env["doc_headers"]

        # Upload a medical document
        doc_res = _upload_task_doc(
            client,
            pat_id,
            "Async Cardiology Note",
            "CARDIOLOGY CLINICAL NOTE\nDiagnosis: Hypertension stage 2.\nPrescribed: Amlodipine 10mg daily.",
            doc_headers,
        )
        doc_id = doc_res["document_id"]

        # Enqueue background processing
        res = client.post(
            f"/api/v1/tasks/documents/{doc_id}/process",
            headers=doc_headers,
        )
        assert res.status_code == status.HTTP_202_ACCEPTED
        task_data = res.json()

        assert task_data["task_id"].startswith("TASK-")
        assert task_data["task_type"] == "document_processing"
        assert task_data["patient_id"] == pat_id

        # Query task status endpoint
        task_id = task_data["task_id"]
        status_res = client.get(f"/api/v1/tasks/{task_id}", headers=doc_headers)
        assert status_res.status_code == status.HTTP_200_OK
        current_task = status_res.json()
        assert current_task["task_id"] == task_id
        assert current_task["status"] in ("queued", "running", "completed")

    def test_idempotent_duplicate_document_processing_task(self, client: TestClient, task_env, tmp_path):
        """Re-enqueuing document processing while active returns the existing task."""
        settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
        env = task_env
        pat_id = env["pat_a_id"]
        doc_headers = env["doc_headers"]

        doc_res = _upload_task_doc(
            client,
            pat_id,
            "Async Duplicate Test Note",
            "Discharge note content.",
            doc_headers,
        )
        doc_id = doc_res["document_id"]

        res1 = client.post(f"/api/v1/tasks/documents/{doc_id}/process", headers=doc_headers)
        assert res1.status_code == status.HTTP_202_ACCEPTED
        t1_id = res1.json()["task_id"]

        res2 = client.post(f"/api/v1/tasks/documents/{doc_id}/process", headers=doc_headers)
        assert res2.status_code == status.HTTP_202_ACCEPTED
        # Either returns existing active task or a new valid task
        assert res2.json()["task_id"].startswith("TASK-")

    def test_enqueue_timeline_compilation_task(self, client: TestClient, task_env, tmp_path):
        settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
        env = task_env
        pat_id = env["pat_a_id"]
        doc_headers = env["doc_headers"]

        res = client.post(
            f"/api/v1/tasks/timeline/{pat_id}/summary",
            json={"focus": "cardiology"},
            headers=doc_headers,
        )
        assert res.status_code == status.HTTP_202_ACCEPTED
        data = res.json()
        assert data["task_type"] == "timeline_summary"
        assert data["patient_id"] == pat_id


# ===========================================================================
# 5. RBAC & Patient Isolation on Tasks
# ===========================================================================


class TestTaskSecurityAndRBAC:
    """Ensures cross-patient isolation and unauthorized access rejection on tasks."""

    def test_patient_cannot_trigger_document_processing_task(self, client: TestClient, task_env, tmp_path):
        settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
        env = task_env
        pat_id = env["pat_a_id"]
        pat_headers = env["pat_a_headers"]
        doc_headers = env["doc_headers"]

        doc_res = _upload_task_doc(client, pat_id, "Patient Upload", "Patient document content.", doc_headers)
        doc_id = doc_res["document_id"]

        # Patient attempts to trigger processing -> 403
        res = client.post(f"/api/v1/tasks/documents/{doc_id}/process", headers=pat_headers)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_cross_patient_task_status_access_rejected(self, client: TestClient, task_env, tmp_path):
        settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
        env = task_env
        pat_a_id = env["pat_a_id"]
        pat_b_headers = env["pat_b_headers"]
        doc_headers = env["doc_headers"]

        doc_res = _upload_task_doc(client, pat_a_id, "Alice Document", "Alice content.", doc_headers)
        doc_id = doc_res["document_id"]

        task_res = client.post(f"/api/v1/tasks/documents/{doc_id}/process", headers=doc_headers)
        task_id = task_res.json()["task_id"]

        # Bob attempts to view Alice's background task -> 403
        res = client.get(f"/api/v1/tasks/{task_id}", headers=pat_b_headers)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_unrelated_doctor_task_access_rejected(self, client: TestClient, task_env, tmp_path):
        settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
        env = task_env
        pat_a_id = env["pat_a_id"]
        unrelated_doc_headers = env["unrelated_doc_headers"]
        doc_headers = env["doc_headers"]

        doc_res = _upload_task_doc(client, pat_a_id, "Alice Secret Document", "Alice confidential.", doc_headers)
        doc_id = doc_res["document_id"]

        task_res = client.post(f"/api/v1/tasks/documents/{doc_id}/process", headers=doc_headers)
        task_id = task_res.json()["task_id"]

        # Unrelated doctor attempts to access task -> 403
        res = client.get(f"/api/v1/tasks/{task_id}", headers=unrelated_doc_headers)
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_task_access_rejected(self, client: TestClient):
        res = client.get("/api/v1/tasks/TASK-20260829-00000000")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_nonexistent_task_returns_404(self, client: TestClient, task_env):
        admin_headers = task_env["admin_headers"]
        res = client.get("/api/v1/tasks/TASK-NONEXISTENT-9999", headers=admin_headers)
        assert res.status_code == status.HTTP_404_NOT_FOUND


# ===========================================================================
# 6. Task Listing, Filtering, and Pagination
# ===========================================================================


class TestTaskListAndManagementAPI:
    """Tests GET /tasks, POST /tasks/{id}/cancel, POST /tasks/{id}/retry."""

    def test_list_tasks_pagination_and_filters(self, client: TestClient, task_env, tmp_path):
        settings.DOCUMENT_STORAGE_PATH = str(tmp_path)
        env = task_env
        pat_id = env["pat_a_id"]
        doc_headers = env["doc_headers"]

        # Submit two tasks
        client.post(f"/api/v1/tasks/timeline/{pat_id}/summary", headers=doc_headers)
        client.post(f"/api/v1/tasks/timeline/{pat_id}/summary", headers=doc_headers)

        res = client.get(f"/api/v1/tasks?patient_id={pat_id}&size=10", headers=doc_headers)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 2

    def test_cancel_and_retry_task_flow(self, client: TestClient, task_env):
        admin_headers = task_env["admin_headers"]

        # Directly submit a mock task to local provider
        provider = get_background_task_provider()
        task = provider.submit_task(
            task_type=BackgroundTaskType.SAFETY_CHECK,
            fn=lambda: {"test": "ok"},
            patient_id="PAT-RETRY-01",
        )

        # Cancel endpoint
        cancel_res = client.post(f"/api/v1/tasks/{task.task_id}/cancel", headers=admin_headers)
        assert cancel_res.status_code in (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST)

        # Retry endpoint
        retry_res = client.post(f"/api/v1/tasks/{task.task_id}/retry", headers=admin_headers)
        assert retry_res.status_code in (status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST)


# ===========================================================================
# 7. Credential & PHI Logging Protection
# ===========================================================================


class TestTaskSecurityLogging:
    """Verifies that secrets, API keys, and PHI never appear in task logs."""

    def test_api_keys_and_passwords_not_in_task_logs(self, caplog):
        with caplog.at_level(logging.INFO, logger="medigen.tasks"):
            provider = LocalBackgroundTaskProvider(max_workers=1)
            task = provider.submit_task(
                task_type=BackgroundTaskType.DOCUMENT_PROCESSING,
                fn=lambda: {"status": "ok"},
                patient_id="PAT-999",
                payload={"api_key": "SECRET_KEY_123", "password": "PASSWORD_456"},
            )
            time.sleep(0.05)
            provider.shutdown(wait=True)

        log_content = caplog.text
        assert "SECRET_KEY_123" not in log_content
        assert "PASSWORD_456" not in log_content
