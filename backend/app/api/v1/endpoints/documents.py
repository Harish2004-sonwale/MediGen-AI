from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.document import MedicalDocument
from app.models.patient import Patient
from app.models.user import User
from app.schemas.document import (
    DocumentChunkListResponse,
    DocumentChunkResponse,
    DocumentListResponse,
    DocumentProcessingStatus,
    DocumentResponse,
    DocumentType,
)
from app.schemas.user import UserRole
from app.services.appointment_service import resolve_patient
from app.services.document_processing_service import process_medical_document
from app.services.document_service import (
    build_chunk_response,
    build_document_response,
    create_medical_document,
    delete_medical_document,
    get_document_by_id,
    get_document_chunks,
    has_patient_clinical_access,
    list_documents,
)

router = APIRouter(tags=["Medical Documents"])


@router.post(
    "/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a medical document",
)
def upload_medical_document(
    file: UploadFile = File(..., description="Document file (PDF, TXT, DOCX)"),
    patient_id: str = Form(..., description="Target patient ID or public patient_id"),
    title: str = Form(..., min_length=2, max_length=255, description="Document title"),
    document_type: DocumentType = Form(DocumentType.OTHER, description="Clinical classification"),
    encounter_id: str | None = Form(None, description="Optional associated encounter ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentResponse:
    """Upload, validate, store, and process a patient medical document."""
    try:
        document = create_medical_document(
            db=db,
            patient_ref=patient_id,
            title=title,
            document_type=document_type,
            upload_file=file,
            current_user=current_user,
            encounter_ref=encounter_id,
            process_immediately=True,
        )
        return build_document_response(document)
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/documents",
    response_model=DocumentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter medical documents",
)
def get_documents_list(
    patient_id: str | None = Query(None, description="Filter by patient ID or public patient_id"),
    document_type: DocumentType | None = Query(None, description="Filter by document type"),
    processing_status: DocumentProcessingStatus | None = Query(
        None,
        description="Filter by processing status",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    page_size: int | None = Query(None, ge=1, le=100, description="Items per page alias"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentListResponse:
    """Retrieve filtered and paginated list of authorized medical documents."""
    effective_size = page_size if page_size is not None else size
    target_patient_id: int | None = None

    if current_user.role == UserRole.PATIENT:
        patient = db.scalars(select(Patient).where(Patient.email == current_user.email)).first()
        if not patient:
            return DocumentListResponse.create(items=[], total=0, page=page, size=effective_size)
        target_patient_id = patient.id
    elif patient_id is not None:
        patient = resolve_patient(db, patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient '{patient_id}' was not found.",
            )
        if not has_patient_clinical_access(db, current_user, patient):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access medical documents for this patient.",
            )
        target_patient_id = patient.id

    docs, total = list_documents(
        db=db,
        patient_id=target_patient_id,
        document_type=document_type,
        processing_status=processing_status,
        page=page,
        size=effective_size,
    )

    items = [build_document_response(doc) for doc in docs]
    return DocumentListResponse.create(items=items, total=total, page=page, size=effective_size)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get medical document metadata",
)
def get_document_metadata(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentResponse:
    """Retrieve document metadata and processing state."""
    doc = get_document_by_id(db, identifier=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical document '{document_id}' was not found.",
        )

    if not has_patient_clinical_access(db, current_user, doc.patient):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this medical document.",
        )

    return build_document_response(doc)


@router.post(
    "/documents/{document_id}/reprocess",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Reprocess a medical document (extraction & chunking)",
)
def reprocess_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentResponse:
    """Re-run extraction and chunking pipeline on an existing medical document."""
    doc = get_document_by_id(db, identifier=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical document '{document_id}' was not found.",
        )

    if current_user.role == UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients cannot trigger document reprocessing.",
        )

    if not has_patient_clinical_access(db, current_user, doc.patient):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to reprocess this medical document.",
        )

    processed_doc = process_medical_document(db=db, document=doc)
    return build_document_response(processed_doc)


@router.get(
    "/documents/{document_id}/chunks",
    response_model=DocumentChunkListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get extracted text chunks for an indexed document",
)
def get_document_chunks_endpoint(
    document_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=200, description="Chunks per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentChunkListResponse:
    """Retrieve paginated text chunks for clinical review or debugging."""
    doc = get_document_by_id(db, identifier=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical document '{document_id}' was not found.",
        )

    if current_user.role == UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients do not have direct access to raw clinical document chunks.",
        )

    if not has_patient_clinical_access(db, current_user, doc.patient):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access chunks for this medical document.",
        )

    chunks, total = get_document_chunks(db=db, document_id=doc.id, page=page, size=size)
    items = [build_chunk_response(c) for c in chunks]
    return DocumentChunkListResponse.create(items=items, total=total, page=page, size=size)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a medical document",
)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, str]:
    """Delete a medical document and associated chunks."""
    doc = get_document_by_id(db, identifier=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medical document '{document_id}' was not found.",
        )

    if current_user.role == UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients cannot delete medical documents.",
        )

    if not has_patient_clinical_access(db, current_user, doc.patient):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this medical document.",
        )

    delete_medical_document(db, doc)
    return {"detail": f"Medical document '{document_id}' successfully deleted."}
