"""API endpoints for Clinical Notes & AI Scribe Synthesis.

Phase 9.0.8: Automated Clinical Documentation, AI Scribe Synthesis & Structured Note Generation.
Provides:
- POST  /api/v1/patients/{patient_id}/notes (Create manual draft)
- GET   /api/v1/patients/{patient_id}/notes (List notes)
- GET   /api/v1/notes/{note_id}             (Get note details)
- PATCH /api/v1/notes/{note_id}             (Update draft note)
- POST  /api/v1/tasks/notes/synthesize      (Enqueue async AI note synthesis)
- POST  /api/v1/notes/{note_id}/signoff     (Physician legal signoff)
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.ai.task_worker import get_background_task_provider
from app.api.deps import get_current_active_user, get_db, require_role
from app.models.user import User, UserRole
from app.schemas.note import (
    ClinicalNoteCreate,
    ClinicalNoteListResponse,
    ClinicalNoteResponse,
    ClinicalNoteSignoff,
    ClinicalNoteSynthesizeRequest,
    ClinicalNoteUpdate,
)
from app.schemas.task import BackgroundTaskResponse, BackgroundTaskType
from app.services.note_service import (
    create_manual_note,
    execute_note_synthesis_job,
    get_clinical_note,
    list_patient_clinical_notes,
    signoff_clinical_note,
    synthesize_clinical_note,
    update_draft_note,
)

router = APIRouter(tags=["Clinical Notes & AI Scribe"])


@router.post(
    "/patients/{patient_id}/notes",
    response_model=ClinicalNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual clinical note draft for a patient",
)
def create_note_endpoint(
    patient_id: str,
    note_in: ClinicalNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> ClinicalNoteResponse:
    """Manually draft a clinical note associated with a patient."""
    return create_manual_note(
        db=db,
        patient_id=patient_id,
        note_in=note_in,
        current_user=current_user,
    )


@router.get(
    "/patients/{patient_id}/notes",
    response_model=ClinicalNoteListResponse,
    status_code=status.HTTP_200_OK,
    summary="List clinical notes for a patient",
)
def list_patient_notes_endpoint(
    patient_id: str,
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalNoteListResponse:
    """List clinical notes associated with the patient."""
    return list_patient_clinical_notes(
        db=db,
        patient_id=patient_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/notes/{note_id}",
    response_model=ClinicalNoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve details of a specific clinical note",
)
def get_note_endpoint(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalNoteResponse:
    """Retrieve full details of a clinical note."""
    return get_clinical_note(
        db=db,
        note_id=note_id,
        current_user=current_user,
    )


@router.patch(
    "/notes/{note_id}",
    response_model=ClinicalNoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a draft clinical note",
)
def update_note_endpoint(
    note_id: str,
    note_in: ClinicalNoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> ClinicalNoteResponse:
    """Update sections or raw text of a draft clinical note. Finalized notes are immutable."""
    return update_draft_note(
        db=db,
        note_id=note_id,
        note_in=note_in,
        current_user=current_user,
    )


@router.post(
    "/tasks/notes/synthesize",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue asynchronous AI Scribe note synthesis background task",
)
def enqueue_note_synthesis_task_endpoint(
    request: ClinicalNoteSynthesizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> BackgroundTaskResponse:
    """Trigger background AI Scribe note synthesis."""
    task_provider = get_background_task_provider()
    task = task_provider.submit_task(
        task_type=BackgroundTaskType.NOTE_SYNTHESIS,
        fn=execute_note_synthesis_job,
        fn_kwargs={
            "patient_id": request.patient_id,
            "note_type": request.note_type.value,
            "encounter_id": request.encounter_id,
            "chat_session_id": request.chat_session_id,
            "custom_instructions": request.custom_instructions,
            "user_id": current_user.id,
        },
        patient_id=request.patient_id,
        created_by_user_id=current_user.id,
        payload={"note_type": request.note_type.value, "patient_id": request.patient_id},
    )
    return BackgroundTaskResponse.model_validate(task)


@router.post(
    "/notes/{note_id}/signoff",
    response_model=ClinicalNoteResponse,
    status_code=status.HTTP_200_OK,
    summary="Attending physician review, verification, and legal signoff",
)
def signoff_note_endpoint(
    note_id: str,
    signoff_in: ClinicalNoteSignoff,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> ClinicalNoteResponse:
    """Sign off and finalize a clinical note, making it authoritative and legally immutable."""
    return signoff_clinical_note(
        db=db,
        note_id=note_id,
        signoff_in=signoff_in,
        current_user=current_user,
    )
