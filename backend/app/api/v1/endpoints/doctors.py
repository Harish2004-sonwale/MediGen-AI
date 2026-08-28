from typing import Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_role
from app.database import get_db
from app.models.user import User
from app.schemas.doctor import (
    ConsultationMode,
    DoctorAdminUpdate,
    DoctorAvailabilityStatus,
    DoctorCreate,
    DoctorDetailResponse,
    DoctorListResponse,
    DoctorPublicResponse,
    DoctorRejectRequest,
    DoctorUpdate,
    DoctorVerificationStatus,
    DoctorVerifyRequest,
)
from app.schemas.user import UserRole
from app.services.doctor_service import (
    activate_doctor,
    create_doctor,
    deactivate_doctor,
    get_doctor_by_doctor_id,
    get_doctor_by_user_id,
    list_doctors,
    reject_doctor,
    update_doctor,
    verify_doctor,
)

router = APIRouter(tags=["Doctor Management"])


@router.post(
    "/doctors",
    response_model=DoctorDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or register a doctor profile",
)
def register_doctor_profile(
    doctor_in: DoctorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DoctorDetailResponse:
    """Create a new doctor profile associated with a user account."""
    if current_user.role == UserRole.ADMIN:
        target_user_id = doctor_in.user_id if doctor_in.user_id is not None else current_user.id
    elif current_user.role == UserRole.DOCTOR:
        target_user_id = current_user.id
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and medical doctors can create doctor profiles.",
        )

    try:
        doctor = create_doctor(db, doctor_in=doctor_in, user_id=target_user_id)
        return DoctorDetailResponse.model_validate(doctor)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/doctors",
    response_model=DoctorListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search, filter, and list doctors",
)
def get_doctors_directory(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    page_size: int | None = Query(None, ge=1, le=100, description="Items per page alias"),
    department: str | None = Query(None, description="Filter by clinical department (e.g. Dentistry, Cardiology)"),
    specialization: str | None = Query(None, description="Filter by medical specialization (e.g. Orthodontist)"),
    min_experience: int | None = Query(None, ge=0, description="Filter by minimum years of experience"),
    max_experience: int | None = Query(None, ge=0, description="Filter by maximum years of experience"),
    location: str | None = Query(None, description="Filter by city, clinic, or hospital location"),
    consultation_mode: ConsultationMode | None = Query(None, description="Filter by consultation mode"),
    availability: DoctorAvailabilityStatus | None = Query(None, description="Filter by availability status"),
    availability_status: DoctorAvailabilityStatus | None = Query(
        None,
        description="Filter by availability status",
    ),
    verification_status: DoctorVerificationStatus | None = Query(
        None,
        description="Filter by verification status (Admin only)",
    ),
    search: str | None = Query(None, description="Keyword search across name, department, specialization, clinic"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DoctorListResponse:
    """Retrieve filtered and paginated doctor profiles."""
    is_admin = current_user.role == UserRole.ADMIN
    only_verified = not is_admin
    effective_size = page_size if page_size is not None else size
    effective_availability = availability if availability is not None else availability_status

    doctors, total = list_doctors(
        db,
        page=page,
        size=effective_size,
        department=department,
        specialization=specialization,
        min_experience=min_experience,
        max_experience=max_experience,
        location=location,
        consultation_mode=consultation_mode,
        verification_status=verification_status if is_admin else None,
        availability_status=effective_availability,
        search=search,
        only_verified=only_verified,
    )

    if is_admin:
        items = [DoctorDetailResponse.model_validate(d) for d in doctors]
    else:
        items = [DoctorPublicResponse.model_validate(d) for d in doctors]

    return DoctorListResponse.create(items=items, total=total, page=page, size=effective_size)


@router.get(
    "/doctors/me",
    response_model=DoctorDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current doctor's own profile",
)
def get_my_doctor_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> DoctorDetailResponse:
    """Retrieve full profile information for the authenticated doctor."""
    doctor = get_doctor_by_user_id(db, user_id=current_user.id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found for the current user account.",
        )
    return DoctorDetailResponse.model_validate(doctor)


@router.patch(
    "/doctors/me",
    response_model=DoctorDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current doctor's own professional profile",
)
def update_my_doctor_profile(
    doctor_in: DoctorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> DoctorDetailResponse:
    """Update professional information for the authenticated doctor."""
    doctor = get_doctor_by_user_id(db, user_id=current_user.id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found for the current user account.",
        )
    try:
        updated = update_doctor(db, doctor=doctor, doctor_in=doctor_in, is_admin=(current_user.role == UserRole.ADMIN))
        return DoctorDetailResponse.model_validate(updated)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/doctors/{doctor_id}",
    response_model=Union[DoctorDetailResponse, DoctorPublicResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve doctor profile by ID",
)
def get_doctor_profile(
    doctor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Union[DoctorDetailResponse, DoctorPublicResponse]:
    """Retrieve doctor profile details."""
    doctor = get_doctor_by_doctor_id(db, doctor_id=doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with identifier '{doctor_id}' was not found.",
        )

    is_admin = current_user.role == UserRole.ADMIN
    is_self = doctor.user_id == current_user.id

    if is_admin or is_self:
        return DoctorDetailResponse.model_validate(doctor)

    # Non-admins / patients only see verified doctors
    if doctor.verification_status != DoctorVerificationStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with identifier '{doctor_id}' was not found.",
        )

    return DoctorPublicResponse.model_validate(doctor)


@router.patch(
    "/doctors/{doctor_id}",
    response_model=DoctorDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update doctor profile",
)
def update_doctor_profile(
    doctor_id: str,
    doctor_in: Union[DoctorAdminUpdate, DoctorUpdate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DoctorDetailResponse:
    """Update doctor profile details."""
    doctor = get_doctor_by_doctor_id(db, doctor_id=doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with identifier '{doctor_id}' was not found.",
        )

    is_admin = current_user.role == UserRole.ADMIN
    is_self = doctor.user_id == current_user.id

    if not is_admin and not is_self:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify another doctor's profile.",
        )

    try:
        updated = update_doctor(db, doctor=doctor, doctor_in=doctor_in, is_admin=is_admin)
        return DoctorDetailResponse.model_validate(updated)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/doctors/{doctor_id}",
    response_model=DoctorDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate a doctor profile",
)
def deactivate_doctor_profile(
    doctor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> DoctorDetailResponse:
    """Soft deactivate a doctor profile (Admin only)."""
    doctor = get_doctor_by_doctor_id(db, doctor_id=doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with identifier '{doctor_id}' was not found.",
        )
    deactivated = deactivate_doctor(db, doctor=doctor)
    return DoctorDetailResponse.model_validate(deactivated)


@router.post(
    "/doctors/{doctor_id}/verify",
    response_model=DoctorDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify a doctor's credentials and profile",
)
def verify_doctor_profile(
    doctor_id: str,
    verify_in: DoctorVerifyRequest = DoctorVerifyRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> DoctorDetailResponse:
    """Admin approval of doctor credentials and verification."""
    doctor = get_doctor_by_doctor_id(db, doctor_id=doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with identifier '{doctor_id}' was not found.",
        )
    verified = verify_doctor(db, doctor=doctor, note=verify_in.note)
    return DoctorDetailResponse.model_validate(verified)


@router.post(
    "/doctors/{doctor_id}/reject",
    response_model=DoctorDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject a doctor's verification application",
)
def reject_doctor_profile(
    doctor_id: str,
    reject_in: DoctorRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> DoctorDetailResponse:
    """Admin rejection of doctor verification application with reason."""
    doctor = get_doctor_by_doctor_id(db, doctor_id=doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with identifier '{doctor_id}' was not found.",
        )
    rejected = reject_doctor(db, doctor=doctor, reason=reject_in.rejection_reason)
    return DoctorDetailResponse.model_validate(rejected)


@router.post(
    "/doctors/{doctor_id}/activate",
    response_model=DoctorDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate doctor profile availability",
)
def activate_doctor_availability(
    doctor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DoctorDetailResponse:
    """Set doctor availability status to available."""
    doctor = get_doctor_by_doctor_id(db, doctor_id=doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with identifier '{doctor_id}' was not found.",
        )
    if current_user.role != UserRole.ADMIN and doctor.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this doctor's availability.",
        )
    activated = activate_doctor(db, doctor=doctor)
    return DoctorDetailResponse.model_validate(activated)


@router.post(
    "/doctors/{doctor_id}/deactivate",
    response_model=DoctorDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Set doctor availability status to unavailable",
)
def set_doctor_unavailable(
    doctor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DoctorDetailResponse:
    """Set doctor availability status to unavailable."""
    doctor = get_doctor_by_doctor_id(db, doctor_id=doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with identifier '{doctor_id}' was not found.",
        )
    if current_user.role != UserRole.ADMIN and doctor.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to modify this doctor's availability.",
        )
    deactivated = deactivate_doctor(db, doctor=doctor)
    return DoctorDetailResponse.model_validate(deactivated)
