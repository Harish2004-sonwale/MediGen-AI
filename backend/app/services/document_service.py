from datetime import datetime, timezone
import os
from pathlib import Path
import secrets
from typing import BinaryIO, Union
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.document import DocumentChunk, MedicalDocument
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.user import User
from app.schemas.document import (
    DocumentChunkResponse,
    DocumentProcessingStatus,
    DocumentResponse,
    DocumentType,
)
from app.schemas.patient import PatientStatus
from app.schemas.user import UserRole
from app.services.appointment_service import resolve_patient
from app.services.document_processing_service import process_medical_document
from app.services.encounter_service import get_encounter_by_encounter_id, get_encounter_by_id

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".jpg", ".jpeg", ".png"}

ALLOWED_MIME_TYPES = {
    ".pdf": {"application/pdf"},
    ".txt": {"text/plain", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "application/octet-stream",
        "application/zip",
    },
    ".jpg": {"image/jpeg", "image/jpg", "application/octet-stream"},
    ".jpeg": {"image/jpeg", "application/octet-stream"},
    ".png": {"image/png", "application/octet-stream"},
}


def generate_unique_document_id(db: Session) -> str:
    """Generate unique public document identifier (e.g. DOCU-20260828-A1B2)."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    for _ in range(10):
        random_suffix = secrets.token_hex(2).upper()
        candidate = f"DOCU-{date_part}-{random_suffix}"
        exists = db.scalar(select(MedicalDocument.id).where(MedicalDocument.document_id == candidate))
        if not exists:
            return candidate
    return f"DOCU-{date_part}-{secrets.token_hex(4).upper()}"


def has_patient_clinical_access(db: Session, current_user: User, patient: Patient) -> bool:
    """Check if the user is authorized to access the patient's clinical documents."""
    if current_user.role in (UserRole.ADMIN, UserRole.HEALTHCARE_STAFF):
        return True

    if current_user.role == UserRole.PATIENT:
        if patient.user_id == current_user.id:
            return True
        return bool(patient.email and patient.email.strip().lower() == current_user.email.strip().lower())

    if current_user.role == UserRole.DOCTOR:
        doctor = db.scalars(select(Doctor).where(Doctor.user_id == current_user.id)).first()
        if not doctor:
            return False

        if patient.assigned_doctor_id == doctor.id:
            return True

        has_appointment = db.scalar(
            select(Appointment.id).where(
                Appointment.doctor_id == doctor.id,
                Appointment.patient_id == patient.id,
            )
        )
        if has_appointment:
            return True

        has_encounter = db.scalar(
            select(Encounter.id).where(
                Encounter.attending_user_id == current_user.id,
                Encounter.patient_id == patient.id,
            )
        )
        if has_encounter:
            return True

    return False


def validate_file_metadata(filename: str, content_type: str | None, file_size: int) -> tuple[str, str]:
    """Validate file extension, size, and MIME type."""
    if file_size <= 0:
        raise ValueError("Uploaded file is empty (0 bytes).")

    max_bytes = settings.MAX_DOCUMENT_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise ValueError(
            f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds maximum allowed size of {settings.MAX_DOCUMENT_SIZE_MB} MB."
        )

    # Sanitize and get extension
    safe_filename = Path(filename).name
    ext = Path(safe_filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    normalized_mime = content_type.lower() if content_type else "application/octet-stream"
    allowed_mimes = ALLOWED_MIME_TYPES.get(ext, set())

    # If MIME type is provided and not generic, verify compatibility
    if normalized_mime not in allowed_mimes and "octet-stream" not in normalized_mime:
        raise ValueError(
            f"MIME type '{content_type}' is incompatible with file extension '{ext}'."
        )

    return ext, normalized_mime


def save_document_file(document_id: str, file_ext: str, file_stream: BinaryIO) -> tuple[str, int]:
    """Save upload stream to secure storage directory outside web root."""
    storage_dir = os.path.abspath(settings.DOCUMENT_STORAGE_PATH)
    os.makedirs(storage_dir, exist_ok=True)

    safe_filename = f"{document_id}{file_ext}"
    target_path = os.path.normpath(os.path.join(storage_dir, safe_filename))

    # Path traversal protection
    if not target_path.startswith(storage_dir):
        raise ValueError("Invalid storage path destination (path traversal detected).")

    file_size = 0
    with open(target_path, "wb") as dest:
        while chunk := file_stream.read(1024 * 1024):  # 1MB chunks
            dest.write(chunk)
            file_size += len(chunk)

    return target_path, file_size


def delete_document_file(storage_path: str) -> None:
    """Delete physical file from disk safely."""
    try:
        if storage_path and os.path.exists(storage_path):
            os.remove(storage_path)
    except OSError:
        pass


def build_document_response(doc: MedicalDocument) -> DocumentResponse:
    """Convert MedicalDocument ORM model to public DocumentResponse schema."""
    patient = doc.patient
    patient_public_id = patient.patient_id if patient else ""

    return DocumentResponse(
        id=doc.id,
        document_id=doc.document_id,
        patient_id=doc.patient_id,
        patient_public_id=patient_public_id,
        uploader_user_id=doc.uploader_user_id,
        encounter_id=doc.encounter_id,
        title=doc.title,
        document_type=doc.document_type,
        original_filename=doc.original_filename,
        file_extension=doc.file_extension,
        file_size_bytes=doc.file_size_bytes,
        mime_type=doc.mime_type,
        processing_status=doc.processing_status,
        error_message=doc.error_message,
        page_count=doc.page_count,
        total_chunks=doc.total_chunks,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def build_chunk_response(chunk: DocumentChunk) -> DocumentChunkResponse:
    """Convert DocumentChunk ORM model to public DocumentChunkResponse schema."""
    doc = chunk.document
    doc_public_id = doc.document_id if doc else ""

    return DocumentChunkResponse(
        id=chunk.id,
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        document_public_id=doc_public_id,
        patient_id=chunk.patient_id,
        chunk_index=chunk.chunk_index,
        page_number=chunk.page_number,
        content=chunk.content,
        token_count=chunk.token_count,
        vector_id=chunk.vector_id,
        created_at=chunk.created_at,
    )


def create_medical_document(
    db: Session,
    patient_ref: Union[int, str],
    title: str,
    document_type: DocumentType,
    upload_file: UploadFile,
    current_user: User,
    encounter_ref: Union[int, str, None] = None,
    process_immediately: bool = True,
) -> MedicalDocument:
    """Validate, store, and create a new medical document record with automatic processing."""
    patient = resolve_patient(db, patient_ref)
    if not patient:
        raise ValueError(f"Patient reference '{patient_ref}' was not found.")

    if patient.status != PatientStatus.ACTIVE:
        raise ValueError("Cannot upload medical documents for an inactive patient.")

    if not has_patient_clinical_access(db, current_user, patient):
        raise PermissionError("You do not have authorization to upload documents for this patient.")

    # Validate Encounter linking if provided
    encounter_id: int | None = None
    if encounter_ref:
        encounter = None
        if isinstance(encounter_ref, int) or (isinstance(encounter_ref, str) and encounter_ref.isdigit()):
            encounter = get_encounter_by_id(db, int(encounter_ref))
        if not encounter and isinstance(encounter_ref, str):
            encounter = get_encounter_by_encounter_id(db, encounter_ref)

        if not encounter:
            raise ValueError(f"Clinical encounter reference '{encounter_ref}' was not found.")
        if encounter.patient_id != patient.id:
            raise ValueError("Clinical encounter does not belong to the specified patient.")
        encounter_id = encounter.id

    # Read and validate file metadata
    upload_file.file.seek(0, os.SEEK_END)
    file_size = upload_file.file.tell()
    upload_file.file.seek(0)

    original_filename = Path(upload_file.filename or "document.bin").name
    file_ext, mime_type = validate_file_metadata(
        filename=original_filename,
        content_type=upload_file.content_type,
        file_size=file_size,
    )

    document_id = generate_unique_document_id(db)

    # Save to storage
    storage_path, saved_size = save_document_file(
        document_id=document_id,
        file_ext=file_ext,
        file_stream=upload_file.file,
    )

    db_document = MedicalDocument(
        document_id=document_id,
        patient_id=patient.id,
        uploader_user_id=current_user.id,
        encounter_id=encounter_id,
        title=title.strip(),
        document_type=document_type,
        original_filename=original_filename,
        file_extension=file_ext,
        file_size_bytes=saved_size,
        storage_path=storage_path,
        mime_type=mime_type,
        processing_status=DocumentProcessingStatus.PENDING,
        total_chunks=0,
    )

    try:
        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        if process_immediately:
            db_document = process_medical_document(db=db, document=db_document)

        return db_document
    except Exception as exc:
        db.rollback()
        delete_document_file(storage_path)
        raise exc


def get_document_by_id(db: Session, identifier: Union[int, str]) -> MedicalDocument | None:
    """Retrieve MedicalDocument by integer ID or public document_id string."""
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        doc = db.scalars(select(MedicalDocument).where(MedicalDocument.id == int(identifier))).first()
        if doc:
            return doc
    return db.scalars(select(MedicalDocument).where(MedicalDocument.document_id == str(identifier).strip())).first()


def list_documents(
    db: Session,
    patient_id: int | None = None,
    document_type: DocumentType | None = None,
    processing_status: DocumentProcessingStatus | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[MedicalDocument], int]:
    """Retrieve filtered and paginated list of medical documents."""
    query = select(MedicalDocument)

    filters = []
    if patient_id is not None:
        filters.append(MedicalDocument.patient_id == patient_id)
    if document_type is not None:
        filters.append(MedicalDocument.document_type == document_type)
    if processing_status is not None:
        filters.append(MedicalDocument.processing_status == processing_status)

    if filters:
        query = query.where(*filters)

    all_docs = list(db.scalars(query).all())
    total = len(all_docs)

    query = query.order_by(MedicalDocument.created_at.desc())
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    documents = list(db.scalars(query).all())
    return documents, total


def get_document_chunks(
    db: Session,
    document_id: int,
    page: int = 1,
    size: int = 50,
) -> tuple[list[DocumentChunk], int]:
    """Retrieve paginated text chunks for an indexed document."""
    query = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    all_chunks = list(db.scalars(query).all())
    total = len(all_chunks)

    query = query.order_by(DocumentChunk.chunk_index.asc())
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    chunks = list(db.scalars(query).all())
    return chunks, total


def delete_medical_document(db: Session, document: MedicalDocument) -> None:
    """Delete document vectors, physical file, and database record (cascades chunks)."""
    import logging
    _logger = logging.getLogger(__name__)

    # Step 1: Remove vectors from ChromaDB
    try:
        from app.ai.vector_store import get_vector_store
        from app.core.config import settings
        from app.services.vector_indexing_service import remove_document_vectors
        vector_store = get_vector_store(
            db_path=settings.VECTOR_DB_PATH,
            collection_name=settings.VECTOR_COLLECTION_NAME,
        )
        removed = remove_document_vectors(document=document, vector_store=vector_store)
        _logger.debug(
            "Removed %d vectors for document '%s' prior to deletion.",
            removed,
            document.document_id,
        )
    except Exception as vec_exc:
        # Log warning but do NOT silently claim complete cleanup
        _logger.warning(
            "Vector cleanup failed for document '%s' during deletion: %s. "
            "Manual vector store cleanup may be required.",
            document.document_id,
            type(vec_exc).__name__,
        )

    # Step 2: Delete physical file
    delete_document_file(document.storage_path)

    # Step 3: Delete database record (cascades to document_chunks)
    db.delete(document)
    db.commit()
