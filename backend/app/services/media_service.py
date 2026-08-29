"""Business logic service for Multi-Modal Medical Diagnostics and Clinical Imaging.

Phase 9.0.7: Advanced Multi-Modal Medical Diagnostics & Imaging Support.
Provides:
- Secure upload & validation of clinical media files
- Patient isolation & RBAC enforcement
- Background AI imaging analysis invocation
- Clinician review and diagnostic signoff
- Authoritative metadata management in PostgreSQL
"""

from datetime import datetime, timezone
import logging
import os
import shutil
import uuid
from typing import Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.imaging_provider import BaseMedicalImagingProvider, get_imaging_provider
from app.core.config import settings
from app.database.session import SessionLocal
from app.models.media import DiagnosticMedia
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.media import (
    ClinicianReviewRequest,
    DiagnosticMediaListResponse,
    DiagnosticMediaResponse,
    MediaBodySite,
    MediaModality,
    MediaStatus,
)

logger = logging.getLogger("medigen.media_service")

ALLOWED_MEDIA_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
    "tiff",
    "tif",
    "dcm",
    "dicom",
    "pdf",
}

ALLOWED_MEDIA_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/tiff",
    "application/dicom",
    "application/pdf",
    "application/octet-stream",
}


def _validate_patient_media_access(db: Session, current_user: User, patient: Patient) -> None:
    """Enforce strict RBAC and patient isolation for medical media."""
    if current_user.role == UserRole.ADMIN:
        return
    if current_user.role in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF):
        return
    if current_user.role == UserRole.PATIENT:
        if current_user.email.lower() != patient.email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot access clinical media belonging to another patient.",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient clinical privileges to access patient media.",
    )


def _generate_media_id() -> str:
    """Generate unique public diagnostic media identifier."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"MED-{date_str}-{unique_suffix}"


def upload_clinical_media(
    db: Session,
    patient_id: str,
    file: UploadFile,
    title: str,
    modality: MediaModality,
    body_site: Optional[MediaBodySite],
    encounter_id: Optional[int],
    current_user: User,
) -> DiagnosticMediaResponse:
    """Upload and record a new clinical media file for a patient."""
    # 1. Resolve target patient
    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' not found.",
        )

    # 2. Verify authorization
    _validate_patient_media_access(db, current_user, patient)

    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may upload diagnostic media.",
        )

    # 3. Validate file extension & mime
    raw_filename = file.filename or "media_file"
    file_ext = raw_filename.split(".")[-1].lower() if "." in raw_filename else ""

    if file_ext not in ALLOWED_MEDIA_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '.{file_ext}'. Allowed formats: {', '.join(sorted(ALLOWED_MEDIA_EXTENSIONS))}",
        )

    mime_type = file.content_type or "application/octet-stream"

    # 4. Enforce size limits and write to safe storage path
    storage_dir = os.path.abspath(settings.MEDIA_STORAGE_DIR)
    os.makedirs(storage_dir, exist_ok=True)

    safe_filename = f"{uuid.uuid4().hex}.{file_ext}"
    destination_path = os.path.join(storage_dir, safe_filename)

    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > settings.MEDIA_MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum permissible size of {settings.MEDIA_MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )

    with open(destination_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    media_id = _generate_media_id()

    # 5. Persist record in PostgreSQL
    media = DiagnosticMedia(
        media_id=media_id,
        patient_id=patient.id,
        uploader_user_id=current_user.id,
        encounter_id=encounter_id,
        title=title.strip(),
        modality=modality,
        body_site=body_site,
        original_filename=os.path.basename(raw_filename),
        file_extension=file_ext,
        file_size_bytes=file_size,
        storage_path=destination_path,
        mime_type=mime_type,
        status=MediaStatus.UPLOADED,
        requires_clinician_review=True,
        clinician_confirmed=False,
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    logger.info("Uploaded diagnostic media %s for patient_id=%s", media_id, patient.patient_id)
    return DiagnosticMediaResponse.model_validate(media)


def get_diagnostic_media(
    db: Session,
    media_id: str,
    current_user: User,
) -> DiagnosticMediaResponse:
    """Retrieve diagnostic media metadata and AI findings."""
    stmt = select(DiagnosticMedia).where(DiagnosticMedia.media_id == media_id)
    media = db.execute(stmt).scalar_one_or_none()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic media '{media_id}' not found.",
        )

    _validate_patient_media_access(db, current_user, media.patient)
    return DiagnosticMediaResponse.model_validate(media)


def list_patient_diagnostic_media(
    db: Session,
    patient_id: str,
    current_user: User,
    skip: int = 0,
    limit: int = 50,
) -> DiagnosticMediaListResponse:
    """List all clinical diagnostic media records for a patient."""
    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' not found.",
        )

    _validate_patient_media_access(db, current_user, patient)

    media_stmt = (
        select(DiagnosticMedia)
        .where(DiagnosticMedia.patient_id == patient.id)
        .order_by(DiagnosticMedia.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = db.execute(media_stmt).scalars().all()

    return DiagnosticMediaListResponse(
        items=[DiagnosticMediaResponse.model_validate(m) for m in items],
        total=len(items),
    )


def get_diagnostic_media_file(
    db: Session,
    media_id: str,
    current_user: User,
) -> Tuple[str, str, str]:
    """Retrieve physical file path, MIME type, and original filename."""
    stmt = select(DiagnosticMedia).where(DiagnosticMedia.media_id == media_id)
    media = db.execute(stmt).scalar_one_or_none()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic media '{media_id}' not found.",
        )

    _validate_patient_media_access(db, current_user, media.patient)

    if not os.path.exists(media.storage_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media binary file could not be located on storage volume.",
        )

    return media.storage_path, media.mime_type, media.original_filename


def analyze_diagnostic_media(
    db: Session,
    media_id: str,
    current_user: User,
    imaging_provider: Optional[BaseMedicalImagingProvider] = None,
) -> DiagnosticMediaResponse:
    """Execute AI multi-modal imaging analysis against media record."""
    stmt = select(DiagnosticMedia).where(DiagnosticMedia.media_id == media_id)
    media = db.execute(stmt).scalar_one_or_none()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic media '{media_id}' not found.",
        )

    _validate_patient_media_access(db, current_user, media.patient)

    provider = imaging_provider or get_imaging_provider()

    try:
        media.status = MediaStatus.ANALYZING
        db.commit()

        finding = provider.analyze_image(
            file_path=media.storage_path,
            modality=media.modality,
        )

        media.confidence_score = finding.confidence_score
        media.findings_summary = finding.primary_observation
        media.structured_findings = finding.model_dump()
        media.anomalies_detected = [f.model_dump() for f in finding.findings if f.is_abnormal]
        media.analyzed_at = datetime.now(timezone.utc)
        media.status = MediaStatus.ANALYZED
        media.requires_clinician_review = True
        media.clinician_confirmed = False

        db.commit()
        db.refresh(media)

        logger.info("Completed imaging analysis for media_id=%s", media.media_id)
        return DiagnosticMediaResponse.model_validate(media)

    except Exception as exc:
        db.rollback()
        media.status = MediaStatus.FAILED
        media.error_message = str(exc)
        db.commit()
        logger.error("Failed imaging analysis for media_id=%s: %s", media.media_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Imaging analysis failed: {str(exc)}",
        ) from exc


def review_diagnostic_media(
    db: Session,
    media_id: str,
    review_request: ClinicianReviewRequest,
    current_user: User,
) -> DiagnosticMediaResponse:
    """Record physician review, notes, and verification signoff."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only licensed physicians or administrators may sign off on diagnostic media findings.",
        )

    stmt = select(DiagnosticMedia).where(DiagnosticMedia.media_id == media_id)
    media = db.execute(stmt).scalar_one_or_none()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic media '{media_id}' not found.",
        )

    _validate_patient_media_access(db, current_user, media.patient)

    media.clinician_confirmed = review_request.clinician_confirmed
    media.clinician_notes = review_request.clinician_notes
    media.reviewed_at = datetime.now(timezone.utc)
    media.status = MediaStatus.REVIEWED

    db.commit()
    db.refresh(media)

    logger.info("Physician user_id=%s signed off on media_id=%s", current_user.id, media.media_id)
    return DiagnosticMediaResponse.model_validate(media)


def execute_media_analysis_job(
    media_id: str,
    user_id: Optional[int] = None,
) -> dict:
    """Background worker job execution entrypoint for asynchronous media analysis."""
    db = SessionLocal()
    try:
        stmt = select(DiagnosticMedia).where(DiagnosticMedia.media_id == media_id)
        media = db.execute(stmt).scalar_one_or_none()
        if not media:
            raise KeyError(f"Diagnostic media '{media_id}' not found.")

        user = None
        if user_id:
            user = db.get(User, user_id)
        if not user:
            user = media.uploader or User(id=1, email="system@medigen.internal", role=UserRole.ADMIN, name="System Worker")

        res = analyze_diagnostic_media(db=db, media_id=media_id, current_user=user)
        return {
            "media_id": media.media_id,
            "patient_id": str(media.patient_id),
            "modality": media.modality.value if hasattr(media.modality, "value") else str(media.modality),
            "confidence_score": media.confidence_score,
            "status": media.status.value if hasattr(media.status, "value") else str(media.status),
            "findings_summary": media.findings_summary,
        }
    finally:
        db.close()
