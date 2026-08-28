from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.database import get_db
from app.models.user import User
from app.schemas.patient import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientStatus,
    PatientUpdate,
)
from app.schemas.user import UserRole
from app.services.patient_service import (
    create_patient,
    deactivate_patient,
    get_patient_by_patient_id,
    list_patients,
    update_patient,
)

router = APIRouter(prefix="/patients", tags=["Patient Management"])

# Standard healthcare clinical permissions
CLINICAL_ACCESS_ROLES = (UserRole.ADMIN, UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF)
DEACTIVATION_ROLES = (UserRole.ADMIN, UserRole.DOCTOR)


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient",
)
def create_new_patient(
    patient_in: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*CLINICAL_ACCESS_ROLES)),
) -> PatientResponse:
    """Register a new patient into the clinical management system."""
    try:
        patient = create_patient(db, patient_in=patient_in)
        return PatientResponse.model_validate(patient)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=PatientListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and search patients with pagination",
)
def get_patients(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    search: str | None = Query(None, description="Search query by name, ID, phone, or email"),
    status_filter: PatientStatus | None = Query(None, alias="status", description="Filter by patient status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*CLINICAL_ACCESS_ROLES)),
) -> PatientListResponse:
    """Retrieve a paginated list of patients with optional filtering and search."""
    patients, total = list_patients(
        db,
        page=page,
        size=size,
        search=search,
        status=status_filter,
    )
    items = [PatientResponse.model_validate(p) for p in patients]
    return PatientListResponse.create(items=items, total=total, page=page, size=size)


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Get patient profile by identifier",
)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*CLINICAL_ACCESS_ROLES)),
) -> PatientResponse:
    """Retrieve complete patient demographics by public patient identifier."""
    patient = get_patient_by_patient_id(db, patient_id=patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' was not found",
        )
    return PatientResponse.model_validate(patient)


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Update patient information",
)
def update_patient_details(
    patient_id: str,
    patient_in: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*CLINICAL_ACCESS_ROLES)),
) -> PatientResponse:
    """Update patient demographics. Immutable fields (id, patient_id, created_at) are protected."""
    patient = get_patient_by_patient_id(db, patient_id=patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' was not found",
        )
    updated = update_patient(db, patient=patient, patient_in=patient_in)
    return PatientResponse.model_validate(updated)


@router.delete(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate a patient profile (Soft delete)",
)
def deactivate_patient_record(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*DEACTIVATION_ROLES)),
) -> PatientResponse:
    """Soft-delete / deactivate a patient record. Hard deletion is prevented to preserve clinical history."""
    patient = get_patient_by_patient_id(db, patient_id=patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' was not found",
        )
    deactivated = deactivate_patient(db, patient=patient)
    return PatientResponse.model_validate(deactivated)
