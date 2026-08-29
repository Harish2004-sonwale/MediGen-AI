"""API endpoints for Multi-Modal Medical Diagnostics and Clinical Imaging.

Phase 9.0.7: Advanced Multi-Modal Medical Diagnostics & Imaging Support.
Provides:
- POST /api/v1/patients/{patient_id}/media (Upload media)
- GET /api/v1/patients/{patient_id}/media (List media)
- GET /api/v1/media/{media_id} (Retrieve metadata & findings)
- GET /api/v1/media/{media_id}/file (Stream raw binary file)
- POST /api/v1/tasks/media/{media_id}/analyze (Enqueue async AI imaging analysis)
- POST /api/v1/media/{media_id}/review (Clinician verification & signoff)
"""

import os
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.ai.task_worker import get_background_task_provider
from app.api.deps import get_current_active_user, get_db, require_role
from app.models.media import DiagnosticMedia
from app.models.user import User, UserRole
from app.schemas.media import (
    ClinicianReviewRequest,
    DiagnosticMediaListResponse,
    DiagnosticMediaResponse,
    MediaBodySite,
    MediaModality,
)
from app.schemas.task import BackgroundTaskResponse, BackgroundTaskType
from app.services.media_service import (
    execute_media_analysis_job,
    get_diagnostic_media,
    get_diagnostic_media_file,
    list_patient_diagnostic_media,
    review_diagnostic_media,
    upload_clinical_media,
)

router = APIRouter(tags=["Multi-Modal Medical Diagnostics"])


@router.post(
    "/patients/{patient_id}/media",
    response_model=DiagnosticMediaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and register a clinical diagnostic media file for a patient",
)
def upload_media_endpoint(
    patient_id: str,
    file: UploadFile = File(..., description="Clinical imaging file (JPEG, PNG, DICOM, TIFF, WebP, PDF)"),
    title: str = Form(..., description="Descriptive title of the imaging study"),
    modality: MediaModality = Form(MediaModality.OTHER, description="Clinical imaging modality"),
    body_site: Optional[MediaBodySite] = Form(None, description="Target anatomical body site"),
    encounter_id: Optional[int] = Form(None, description="Optional associated clinical encounter ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> DiagnosticMediaResponse:
    """Upload a medical image or diagnostic file associated with a patient."""
    return upload_clinical_media(
        db=db,
        patient_id=patient_id,
        file=file,
        title=title,
        modality=modality,
        body_site=body_site,
        encounter_id=encounter_id,
        current_user=current_user,
    )


@router.get(
    "/patients/{patient_id}/media",
    response_model=DiagnosticMediaListResponse,
    status_code=status.HTTP_200_OK,
    summary="List diagnostic media records for a patient",
)
def list_patient_media_endpoint(
    patient_id: str,
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DiagnosticMediaListResponse:
    """Retrieve all diagnostic media records associated with the patient."""
    return list_patient_diagnostic_media(
        db=db,
        patient_id=patient_id,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/media/{media_id}",
    response_model=DiagnosticMediaResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve diagnostic media metadata and AI analysis findings",
)
def get_media_endpoint(
    media_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DiagnosticMediaResponse:
    """Retrieve full details of a specific diagnostic media record."""
    return get_diagnostic_media(
        db=db,
        media_id=media_id,
        current_user=current_user,
    )


@router.get(
    "/media/{media_id}/file",
    status_code=status.HTTP_200_OK,
    summary="Download or stream the raw diagnostic media file",
)
def get_media_file_endpoint(
    media_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """Stream authorized medical media binary file."""
    file_path, mime_type, original_filename = get_diagnostic_media_file(
        db=db,
        media_id=media_id,
        current_user=current_user,
    )
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=original_filename,
    )


@router.post(
    "/tasks/media/{media_id}/analyze",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue asynchronous AI imaging analysis background task",
)
def enqueue_media_analysis_task_endpoint(
    media_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)),
) -> BackgroundTaskResponse:
    """Trigger asynchronous background AI imaging analysis."""
    media = db.query(DiagnosticMedia).filter(DiagnosticMedia.media_id == media_id).first()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic media '{media_id}' not found.",
        )

    task_provider = get_background_task_provider()
    task = task_provider.submit_task(
        task_type=BackgroundTaskType.MEDIA_ANALYSIS,
        fn=execute_media_analysis_job,
        fn_kwargs={"media_id": media.media_id, "user_id": current_user.id},
        patient_id=str(media.patient_id),
        created_by_user_id=current_user.id,
        payload={"media_id": media.media_id, "modality": media.modality.value if hasattr(media.modality, "value") else str(media.modality)},
    )
    return BackgroundTaskResponse.model_validate(task)


@router.post(
    "/media/{media_id}/review",
    response_model=DiagnosticMediaResponse,
    status_code=status.HTTP_200_OK,
    summary="Clinician review, verification, and signoff of AI findings",
)
def review_media_endpoint(
    media_id: str,
    review_request: ClinicianReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> DiagnosticMediaResponse:
    """Record licensed physician confirmation or correction of AI findings."""
    return review_diagnostic_media(
        db=db,
        media_id=media_id,
        review_request=review_request,
        current_user=current_user,
    )
