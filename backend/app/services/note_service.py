"""Business logic service for Clinical Notes, AI Scribe Synthesis & Signoff.

Phase 9.0.8: Automated Clinical Documentation, AI Scribe Synthesis & Structured Note Generation.
Provides:
- Manual note drafting & editing
- Multi-source contextual AI scribe note synthesis
- Strict RBAC & patient data isolation
- Attending physician verification and immutable signoff enforcement
- Background worker execution entrypoint
"""

from datetime import datetime, timezone
import logging
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.scribe_provider import BaseClinicalScribeProvider, get_scribe_provider
from app.database.session import SessionLocal
from app.models.encounter import Encounter
from app.models.media import DiagnosticMedia
from app.models.note import ClinicalNote
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.note import (
    ClinicalNoteCreate,
    ClinicalNoteListResponse,
    ClinicalNoteResponse,
    ClinicalNoteSignoff,
    ClinicalNoteSynthesizeRequest,
    ClinicalNoteUpdate,
    NoteStatus,
    NoteType,
)

logger = logging.getLogger("medigen.services.note_service")


def _validate_patient_note_access(db: Session, current_user: User, patient: Patient) -> None:
    """Enforce RBAC and strict patient data isolation for clinical notes."""
    if current_user.role == UserRole.ADMIN:
        return
    if current_user.role in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF):
        return
    if current_user.role == UserRole.PATIENT:
        if current_user.email.lower() != patient.email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot access clinical notes belonging to another patient.",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient privileges to access patient clinical notes.",
    )


def _generate_note_id() -> str:
    """Generate unique public clinical note identifier (NOT-YYYYMMDD-XXXXXX)."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"NOT-{date_str}-{unique_suffix}"


def create_manual_note(
    db: Session,
    patient_id: str,
    note_in: ClinicalNoteCreate,
    current_user: User,
) -> ClinicalNoteResponse:
    """Create a manual clinician-drafted clinical note."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may create clinical notes.",
        )

    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' not found.",
        )

    _validate_patient_note_access(db, current_user, patient)

    note = ClinicalNote(
        note_id=_generate_note_id(),
        patient_id=patient.id,
        author_user_id=current_user.id,
        encounter_id=note_in.encounter_id,
        title=note_in.title.strip(),
        note_type=note_in.note_type,
        status=NoteStatus.DRAFT,
        content_json=note_in.content_json,
        raw_text=note_in.raw_text.strip(),
        is_ai_generated=False,
        requires_clinician_review=True,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    logger.info("Created manual clinical note %s for patient_id=%s", note.note_id, patient.patient_id)
    return ClinicalNoteResponse.model_validate(note)


def get_clinical_note(
    db: Session,
    note_id: str,
    current_user: User,
) -> ClinicalNoteResponse:
    """Retrieve details of a specific clinical note."""
    stmt = select(ClinicalNote).where(ClinicalNote.note_id == note_id)
    note = db.execute(stmt).scalar_one_or_none()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical note '{note_id}' not found.",
        )

    _validate_patient_note_access(db, current_user, note.patient)
    return ClinicalNoteResponse.model_validate(note)


def list_patient_clinical_notes(
    db: Session,
    patient_id: str,
    current_user: User,
    skip: int = 0,
    limit: int = 50,
) -> ClinicalNoteListResponse:
    """List clinical notes associated with a patient."""
    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' not found.",
        )

    _validate_patient_note_access(db, current_user, patient)

    note_stmt = (
        select(ClinicalNote)
        .where(ClinicalNote.patient_id == patient.id)
        .order_by(ClinicalNote.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    notes = db.execute(note_stmt).scalars().all()

    return ClinicalNoteListResponse(
        items=[ClinicalNoteResponse.model_validate(n) for n in notes],
        total=len(notes),
    )


def update_draft_note(
    db: Session,
    note_id: str,
    note_in: ClinicalNoteUpdate,
    current_user: User,
) -> ClinicalNoteResponse:
    """Update a draft clinical note. Finalized notes are immutable."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may edit clinical notes.",
        )

    stmt = select(ClinicalNote).where(ClinicalNote.note_id == note_id)
    note = db.execute(stmt).scalar_one_or_none()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical note '{note_id}' not found.",
        )

    _validate_patient_note_access(db, current_user, note.patient)

    # Immutability check
    if note.status == NoteStatus.FINALIZED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify a finalized clinical note. Signed notes are legally immutable.",
        )

    if note_in.title is not None:
        note.title = note_in.title.strip()
    if note_in.content_json is not None:
        note.content_json = note_in.content_json
    if note_in.raw_text is not None:
        note.raw_text = note_in.raw_text.strip()

    db.commit()
    db.refresh(note)

    logger.info("Updated draft clinical note %s", note.note_id)
    return ClinicalNoteResponse.model_validate(note)


def synthesize_clinical_note(
    db: Session,
    request: ClinicalNoteSynthesizeRequest,
    current_user: User,
    scribe_provider: Optional[BaseClinicalScribeProvider] = None,
) -> ClinicalNoteResponse:
    """Synthesize multi-modal context into a structured clinical note draft."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may trigger AI clinical note synthesis.",
        )

    stmt = select(Patient).where(
        (Patient.patient_id == request.patient_id)
        | (Patient.id == (int(request.patient_id) if request.patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{request.patient_id}' not found.",
        )

    _validate_patient_note_access(db, current_user, patient)

    # Gather encounter context if specified
    encounter = None
    if request.encounter_id:
        encounter = db.get(Encounter, request.encounter_id)

    # Gather recent diagnostic imaging findings
    media_stmt = (
        select(DiagnosticMedia)
        .where(DiagnosticMedia.patient_id == patient.id)
        .order_by(DiagnosticMedia.created_at.desc())
        .limit(3)
    )
    media_items = db.execute(media_stmt).scalars().all()
    imaging_summaries = [f"[{m.modality.value.upper()}] {m.findings_summary}" for m in media_items if m.findings_summary]

    provider = scribe_provider or get_scribe_provider()
    patient_full_name = f"{patient.first_name} {patient.last_name}"

    content_json, raw_text = provider.synthesize_note(
        patient_name=patient_full_name,
        patient_age=35,
        patient_gender=patient.gender.value if hasattr(patient.gender, "value") else str(patient.gender),
        note_type=request.note_type,
        encounter_title=encounter.notes if encounter else None,
        encounter_assessment=encounter.assessment if encounter else None,
        encounter_plan=encounter.plan if encounter else None,
        imaging_findings=imaging_summaries,
        custom_instructions=request.custom_instructions,
    )

    title_map = {
        NoteType.SOAP: f"SOAP Note — {patient_full_name}",
        NoteType.CONSULTATION: f"Consultation Summary — {patient_full_name}",
        NoteType.DISCHARGE_SUMMARY: f"Discharge Summary — {patient_full_name}",
        NoteType.PROCEDURE_NOTE: f"Procedure Note — {patient_full_name}",
        NoteType.REFERRAL_LETTER: f"Referral Letter — {patient_full_name}",
    }
    title = title_map.get(request.note_type, f"Clinical Note — {patient_full_name}")

    note = ClinicalNote(
        note_id=_generate_note_id(),
        patient_id=patient.id,
        author_user_id=current_user.id,
        encounter_id=request.encounter_id,
        title=title,
        note_type=request.note_type,
        status=NoteStatus.DRAFT,
        content_json=content_json,
        raw_text=raw_text,
        is_ai_generated=True,
        requires_clinician_review=True,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    logger.info("Synthesized AI clinical note %s for patient_id=%s", note.note_id, patient.patient_id)
    return ClinicalNoteResponse.model_validate(note)


def signoff_clinical_note(
    db: Session,
    note_id: str,
    signoff_in: ClinicalNoteSignoff,
    current_user: User,
) -> ClinicalNoteResponse:
    """Attending physician verification and legal signoff of clinical note."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only licensed physicians or administrators may sign off and finalize clinical notes.",
        )

    stmt = select(ClinicalNote).where(ClinicalNote.note_id == note_id)
    note = db.execute(stmt).scalar_one_or_none()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical note '{note_id}' not found.",
        )

    _validate_patient_note_access(db, current_user, note.patient)

    if not signoff_in.confirm_accuracy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must confirm clinical review and accuracy before finalizing the note.",
        )

    note.status = NoteStatus.FINALIZED
    note.signed_by_user_id = current_user.id
    note.signed_at = datetime.now(timezone.utc)
    note.requires_clinician_review = False

    if signoff_in.clinician_notes:
        note.raw_text += f"\n\n[PHYSICIAN SIGNOFF REMARKS - Dr. {current_user.name}]:\n{signoff_in.clinician_notes.strip()}"

    db.commit()
    db.refresh(note)

    logger.info("Physician user_id=%s signed off and finalized clinical note %s", current_user.id, note.note_id)
    return ClinicalNoteResponse.model_validate(note)


def execute_note_synthesis_job(
    patient_id: str,
    note_type: str,
    encounter_id: Optional[int] = None,
    chat_session_id: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    """Background worker job execution entrypoint for asynchronous note synthesis."""
    db = SessionLocal()
    try:
        user = None
        if user_id:
            user = db.get(User, user_id)
        if not user:
            user = User(id=1, email="system@medigen.internal", role=UserRole.ADMIN, name="System Worker")

        req = ClinicalNoteSynthesizeRequest(
            patient_id=patient_id,
            note_type=NoteType(note_type),
            encounter_id=encounter_id,
            chat_session_id=chat_session_id,
            custom_instructions=custom_instructions,
        )
        res = synthesize_clinical_note(db=db, request=req, current_user=user)
        return {
            "note_id": res.note_id,
            "patient_id": str(res.patient_id),
            "note_type": res.note_type.value if hasattr(res.note_type, "value") else str(res.note_type),
            "status": res.status.value if hasattr(res.status, "value") else str(res.status),
            "title": res.title,
        }
    finally:
        db.close()
