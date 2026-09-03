from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_role
from app.core.security import create_access_token
from app.database import get_db
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.token import TokenResponse
from app.schemas.patient import (
    PatientAssignDoctorRequest,
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientSelfRegister,
    PatientStatus,
    PatientUpdate,
)
from app.schemas.user import UserResponse, UserRole
from app.services.patient_service import (
    assign_doctor_to_patient,
    create_patient,
    deactivate_patient,
    get_patient_by_email,
    get_patient_by_patient_id,
    get_patient_by_user_id,
    list_patients,
    self_register_patient,
    update_patient,
)

router = APIRouter(prefix="/patients", tags=["Patient Management"])

# Standard healthcare clinical permissions
CLINICAL_ACCESS_ROLES = (UserRole.ADMIN, UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF)
DEACTIVATION_ROLES = (UserRole.ADMIN, UserRole.DOCTOR)


def _format_patient_response(patient: any) -> PatientResponse:
    """Helper to convert Patient ORM model to PatientResponse with assigned doctor name."""
    resp = PatientResponse.model_validate(patient)
    if patient.assigned_doctor:
        doc = patient.assigned_doctor
        resp.assigned_doctor_name = f"{doc.professional_title} {doc.full_name} ({doc.specialization})"
    return resp


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Patient self-registration on public onboarding portal",
)
def register_new_patient_account(
    reg_in: PatientSelfRegister,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Allows a new patient to create an account, provide initial health problem, and queue for review."""
    try:
        patient, user = self_register_patient(db, reg_in=reg_in)
        access_token = create_access_token(subject=user.id, role=user.role.value)
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/me",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Get currently authenticated patient's profile",
)
def get_my_patient_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PatientResponse:
    """Retrieve logged-in patient's personal record based on account linkage or email."""
    patient = get_patient_by_user_id(db, current_user.id)
    if not patient:
        patient = get_patient_by_email(db, current_user.email)

    if not patient:
        # Auto-create baseline pending patient profile if missing for patient user
        if current_user.role == UserRole.PATIENT:
            from datetime import date
            names = current_user.name.split(" ", 1)
            first_name = names[0]
            last_name = names[1] if len(names) > 1 else "Patient"
            from app.schemas.patient import Gender
            patient = create_patient(
                db,
                patient_in=PatientCreate(
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=date(1990, 1, 1),
                    gender=Gender.PREFER_NOT_TO_SAY,
                    email=current_user.email,
                    user_id=current_user.id,
                    status=PatientStatus.PENDING_REVIEW,
                ),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No patient profile is associated with this clinician/admin account.",
            )

    return _format_patient_response(patient)


@router.post(
    "",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient by clinical staff or admin",
)
def create_new_patient(
    patient_in: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*CLINICAL_ACCESS_ROLES)),
) -> PatientResponse:
    """Register a new patient into the clinical management system."""
    try:
        patient = create_patient(db, patient_in=patient_in)
        return _format_patient_response(patient)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/{patient_id}/assign-doctor",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign or change attending doctor for patient (Admin)",
)
def assign_patient_doctor(
    patient_id: str,
    payload: PatientAssignDoctorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> PatientResponse:
    """Admin reviews new patient intake and assigns responsible attending physician."""
    patient = get_patient_by_patient_id(db, patient_id=patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' was not found",
        )
    try:
        updated = assign_doctor_to_patient(db, patient=patient, doctor_id=payload.doctor_id, notes=payload.notes)
        return _format_patient_response(updated)
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
    doctor_id: int | None = Query(None, description="Filter patients assigned to a specific doctor ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PatientListResponse:
    """Retrieve a paginated list of patients with optional filtering and search."""
    if current_user.role == UserRole.PATIENT:
        # Patients can only view their own patient profile
        patient = get_patient_by_user_id(db, current_user.id) or get_patient_by_email(db, current_user.email)
        items = [_format_patient_response(patient)] if patient else []
        return PatientListResponse.create(items=items, total=len(items), page=1, size=size)

    # If logged in as doctor and no explicit doctor_id was provided, show assigned patients or all accessible
    effective_doc_id = doctor_id
    if current_user.role == UserRole.DOCTOR and doctor_id is None:
        doc = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        # If doctor queries with specific doctor_id filter, apply it
        if doctor_id:
            effective_doc_id = doctor_id

    patients, total = list_patients(
        db,
        page=page,
        size=size,
        search=search,
        status=status_filter,
        doctor_id=effective_doc_id,
    )
    items = [_format_patient_response(p) for p in patients]
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
    current_user: User = Depends(get_current_active_user),
) -> PatientResponse:
    """Retrieve complete patient demographics by public patient identifier."""
    patient = get_patient_by_patient_id(db, patient_id=patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' was not found",
        )

    # Enforce data isolation for Patient role
    if current_user.role == UserRole.PATIENT:
        if patient.user_id != current_user.id and patient.email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You may only view your own patient profile.",
            )

    return _format_patient_response(patient)


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
    current_user: User = Depends(get_current_active_user),
) -> PatientResponse:
    """Update patient demographics. Patient role may only edit personal information."""
    patient = get_patient_by_patient_id(db, patient_id=patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' was not found",
        )

    if current_user.role == UserRole.PATIENT:
        if patient.user_id != current_user.id and patient.email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You may only edit your own personal information.",
            )
        # Prevent patient from changing status or doctor assignment
        update_dict = patient_in.model_dump(exclude_unset=True)
        update_dict.pop("status", None)
        update_dict.pop("assigned_doctor_id", None)
        patient_in = PatientUpdate(**update_dict)

    updated = update_patient(db, patient=patient, patient_in=patient_in)
    return _format_patient_response(updated)


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
    return _format_patient_response(deactivated)

