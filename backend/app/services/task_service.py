"""Background Task Orchestration and Authorization Service.

Phase 9.0.3: Background Asynchronous Worker Architecture.

Provides:
- Task submission wrappers for heavy clinical workloads (document processing, timeline compilation)
- Strict RBAC and patient data isolation for task status queries
- Idempotency guards preventing duplicate active jobs for the same clinical resource
- Worker job execution functions that safely handle independent database sessions
"""

from datetime import datetime, timezone
import logging
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.task_worker import (
    BaseBackgroundTaskProvider,
    get_background_task_provider,
)
from app.database.session import SessionLocal
from app.models.document import MedicalDocument
from app.models.patient import Patient
from app.models.user import User
from app.schemas.document import DocumentProcessingStatus
from app.schemas.task import (
    BackgroundTask,
    BackgroundTaskResponse,
    BackgroundTaskStatus,
    BackgroundTaskType,
)
from app.schemas.user import UserRole
from app.services.appointment_service import resolve_patient
from app.services.document_processing_service import process_medical_document
from app.services.document_service import (
    get_document_by_id,
    has_patient_clinical_access,
)

logger = logging.getLogger("medigen.tasks.service")


# ---------------------------------------------------------------------------
# Background Worker Execution Handlers (run inside worker threads)
# ---------------------------------------------------------------------------


def run_document_processing_job(document_internal_id: int) -> dict[str, Any]:
    """Worker job function: executes full document extraction, chunking, and vector indexing.

    Opens an isolated database session, commits changes, and returns execution metrics.
    """
    db: Session = SessionLocal()
    try:
        doc = db.scalars(
            select(MedicalDocument).where(MedicalDocument.id == document_internal_id)
        ).first()

        if not doc:
            raise ValueError(f"Medical document id={document_internal_id} not found on worker execution.")

        logger.info(
            "Worker executing document processing job for document_id=%s (id=%d)",
            doc.document_id,
            doc.id,
        )

        processed_doc = process_medical_document(db=db, document=doc)

        if processed_doc.processing_status == DocumentProcessingStatus.FAILED:
            raise RuntimeError(processed_doc.error_message or "Document processing failed in worker pipeline.")

        return {
            "document_id": processed_doc.document_id,
            "processing_status": processed_doc.processing_status.value,
            "total_chunks": processed_doc.total_chunks,
            "page_count": processed_doc.page_count,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        db.close()


def run_timeline_summary_job(patient_id_str: str, focus: Optional[str] = None) -> dict[str, Any]:
    """Worker job function: compiles longitudinal clinical timeline summary in background."""
    db: Session = SessionLocal()
    try:
        patient = resolve_patient(db, patient_id_str)
        if not patient:
            raise ValueError(f"Patient '{patient_id_str}' not found on timeline worker execution.")

        from app.services.timeline_service import get_patient_timeline

        # Use system/admin role context for internal summary generation
        admin_user = db.scalars(select(User).where(User.role == UserRole.ADMIN)).first()
        if not admin_user:
            # Fallback to creating a transient system user object
            admin_user = User(id=0, email="system@medigen.internal", role=UserRole.ADMIN)

        timeline_data = get_patient_timeline(
            db=db,
            patient_id_str=patient_id_str,
            current_user=admin_user,
            event_type=None,
            page=1,
            size=100,
        )

        return {
            "patient_id": patient_id_str,
            "total_events_analyzed": timeline_data.total_events,
            "focus_area": focus or "comprehensive",
            "compiled_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        db.close()


def run_imaging_analysis_job(study_id_str: str, user_id: int) -> dict[str, Any]:
    """Worker job function: executes multimodal imaging AI interpretation in background."""
    db: Session = SessionLocal()
    try:
        from app.services.imaging_service import imaging_service
        user = db.get(User, user_id) or User(id=user_id, email="system@medigen.internal", role=UserRole.ADMIN)
        result = imaging_service.run_ai_analysis(db=db, study_id=study_id_str, current_user=user)
        return {
            "study_id": result["study_id"],
            "status": result["status"],
            "findings_count": result["findings_count"],
            "critical_findings_count": result["critical_findings_count"],
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task Service Business Logic & RBAC Enforcement
# ---------------------------------------------------------------------------



def build_task_response(task: BackgroundTask) -> BackgroundTaskResponse:
    """Convert BackgroundTask domain model to public BackgroundTaskResponse schema."""
    return BackgroundTaskResponse(
        task_id=task.task_id,
        task_type=task.task_type,
        status=task.status,
        patient_id=task.patient_id,
        progress=task.progress,
        result_metadata=task.result_metadata,
        error_message=task.error_message,
        retry_count=task.retry_count,
        max_retries=task.max_retries,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


def validate_task_access(
    db: Session,
    current_user: User,
    task: BackgroundTask,
) -> None:
    """Enforce strict RBAC and patient isolation on background task access.

    Raises:
        PermissionError: If user lacks authorization to inspect or manage the task.
    """
    if current_user.role in (UserRole.ADMIN, UserRole.HEALTHCARE_STAFF):
        return

    # User created the task
    if task.created_by_user_id == current_user.id:
        return

    # Check patient isolation
    if current_user.role == UserRole.PATIENT:
        patient = db.scalars(select(Patient).where(Patient.email == current_user.email)).first()
        if not patient:
            raise PermissionError("Patient record not found for authenticated user.")
        if task.patient_id and task.patient_id not in (patient.patient_id, str(patient.id)):
            raise PermissionError("You are not authorized to access tasks for other patients.")
        return

    # Check doctor access to patient
    if current_user.role == UserRole.DOCTOR:
        if not task.patient_id:
            return
        patient = resolve_patient(db, task.patient_id)
        if not patient or not has_patient_clinical_access(db, current_user, patient):
            raise PermissionError("You do not have clinical access to the patient associated with this task.")
        return

    raise PermissionError("Unauthorized to access background task.")


def enqueue_document_processing_task(
    db: Session,
    document_ref: str,
    current_user: User,
    provider: Optional[BaseBackgroundTaskProvider] = None,
) -> BackgroundTask:
    """Enqueue asynchronous document extraction and indexing with idempotency check."""
    doc = get_document_by_id(db, document_ref)
    if not doc:
        raise KeyError(f"Medical document '{document_ref}' was not found.")

    if current_user.role == UserRole.PATIENT:
        raise PermissionError("Patients cannot trigger background document processing.")

    if not has_patient_clinical_access(db, current_user, doc.patient):
        raise PermissionError("You do not have authorization to process documents for this patient.")

    task_provider = provider or get_background_task_provider()
    patient_pub_id = doc.patient.patient_id if doc.patient else str(doc.patient_id)

    # Idempotency check: see if there's already an active processing task for this document
    active_tasks = task_provider.list_tasks(
        patient_id=patient_pub_id,
        task_type=BackgroundTaskType.DOCUMENT_PROCESSING,
    )
    for existing in active_tasks:
        if (
            existing.status in (BackgroundTaskStatus.QUEUED, BackgroundTaskStatus.RUNNING)
            and existing.payload.get("document_id") == doc.document_id
        ):
            logger.info(
                "Returning existing active task task_id=%s for document_id=%s",
                existing.task_id,
                doc.document_id,
            )
            return existing

    # Enqueue new background processing task
    task = task_provider.submit_task(
        task_type=BackgroundTaskType.DOCUMENT_PROCESSING,
        fn=run_document_processing_job,
        fn_args=(doc.id,),
        patient_id=patient_pub_id,
        created_by_user_id=current_user.id,
        payload={"document_id": doc.document_id, "document_internal_id": doc.id},
    )

    return task


def enqueue_timeline_summary_task(
    db: Session,
    patient_id_str: str,
    current_user: User,
    focus: Optional[str] = None,
    provider: Optional[BaseBackgroundTaskProvider] = None,
) -> BackgroundTask:
    """Enqueue asynchronous clinical timeline compilation task."""
    patient = resolve_patient(db, patient_id_str)
    if not patient:
        raise KeyError(f"Patient '{patient_id_str}' was not found.")

    if not has_patient_clinical_access(db, current_user, patient):
        raise PermissionError("You do not have authorization to access timeline for this patient.")

    task_provider = provider or get_background_task_provider()
    patient_pub_id = patient.patient_id

    task = task_provider.submit_task(
        task_type=BackgroundTaskType.TIMELINE_SUMMARY,
        fn=run_timeline_summary_job,
        fn_args=(patient_pub_id, focus),
        patient_id=patient_pub_id,
        created_by_user_id=current_user.id,
        payload={"patient_id": patient_pub_id, "focus": focus},
    )

    return task


def enqueue_imaging_analysis_task(
    db: Session,
    study_id_str: str,
    current_user: User,
    provider: Optional[BaseBackgroundTaskProvider] = None,
) -> BackgroundTask:
    """Enqueue asynchronous medical imaging AI analysis with clinician access checks."""
    from app.services.imaging_service import imaging_service
    study = imaging_service.get_study(db, study_id_str)
    if not study:
        raise KeyError(f"Imaging study '{study_id_str}' was not found.")

    if current_user.role == UserRole.PATIENT and study.patient and study.patient.email != current_user.email:
        raise PermissionError("Patients cannot trigger imaging analysis for other patients.")

    task_provider = provider or get_background_task_provider()
    patient_pub_id = study.patient.patient_id if study.patient else str(study.patient_id)

    task = task_provider.submit_task(
        task_type=BackgroundTaskType.IMAGING_ANALYSIS,
        fn=run_imaging_analysis_job,
        fn_args=(study.study_id, current_user.id),
        patient_id=patient_pub_id,
        created_by_user_id=current_user.id,
        payload={"study_id": study.study_id, "patient_id": patient_pub_id},
    )

    return task


def get_task_status(

    db: Session,
    task_id: str,
    current_user: User,
    provider: Optional[BaseBackgroundTaskProvider] = None,
) -> BackgroundTask:
    """Retrieve task details with RBAC and patient isolation enforcement."""
    task_provider = provider or get_background_task_provider()
    task = task_provider.get_task(task_id)

    if not task:
        raise KeyError(f"Background task '{task_id}' was not found.")

    validate_task_access(db, current_user, task)
    return task


def list_tasks_for_user(
    db: Session,
    current_user: User,
    patient_id: Optional[str] = None,
    status: Optional[BackgroundTaskStatus] = None,
    task_type: Optional[BackgroundTaskType] = None,
    page: int = 1,
    size: int = 20,
    provider: Optional[BaseBackgroundTaskProvider] = None,
) -> tuple[list[BackgroundTask], int]:
    """Retrieve filtered and paginated list of authorized background tasks."""
    task_provider = provider or get_background_task_provider()

    target_patient_id = patient_id
    if current_user.role == UserRole.PATIENT:
        patient = db.scalars(select(Patient).where(Patient.email == current_user.email)).first()
        if not patient:
            return [], 0
        target_patient_id = patient.patient_id
    elif patient_id is not None:
        patient = resolve_patient(db, patient_id)
        if not patient:
            raise KeyError(f"Patient '{patient_id}' was not found.")
        if not has_patient_clinical_access(db, current_user, patient):
            raise PermissionError("You do not have permission to access tasks for this patient.")
        target_patient_id = patient.patient_id

    all_tasks = task_provider.list_tasks(
        patient_id=target_patient_id,
        status=status,
        task_type=task_type,
    )

    # Filter by user authorization
    authorized_tasks: list[BackgroundTask] = []
    for t in all_tasks:
        try:
            validate_task_access(db, current_user, t)
            authorized_tasks.append(t)
        except PermissionError:
            continue

    total = len(authorized_tasks)
    offset = (page - 1) * size
    paginated = authorized_tasks[offset : offset + size]
    return paginated, total


def cancel_task_for_user(
    db: Session,
    task_id: str,
    current_user: User,
    provider: Optional[BaseBackgroundTaskProvider] = None,
) -> bool:
    """Cancel a queued background task after validating authorization."""
    task_provider = provider or get_background_task_provider()
    task = task_provider.get_task(task_id)
    if not task:
        raise KeyError(f"Background task '{task_id}' was not found.")

    validate_task_access(db, current_user, task)
    return task_provider.cancel_task(task_id)


def retry_task_for_user(
    db: Session,
    task_id: str,
    current_user: User,
    provider: Optional[BaseBackgroundTaskProvider] = None,
) -> BackgroundTask:
    """Retry a failed or cancelled background task after validating authorization."""
    task_provider = provider or get_background_task_provider()
    task = task_provider.get_task(task_id)
    if not task:
        raise KeyError(f"Background task '{task_id}' was not found.")

    validate_task_access(db, current_user, task)
    retried_task = task_provider.retry_task(task_id)
    if not retried_task:
        raise ValueError(f"Task '{task_id}' cannot be retried (current status: {task.status.value}).")
    return retried_task
