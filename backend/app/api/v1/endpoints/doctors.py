import secrets
from typing import Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_role
from app.core.security import get_password_hash
from app.database import get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.encounter import Encounter
from app.models.user import User
from app.schemas.doctor import (
    ConsultationMode,
    DoctorAdminCreate,
    DoctorAdminProvisionResponse,
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
from app.services.audit_service import AuditService
from app.services.doctor_service import (
    activate_doctor,
    create_doctor,
    deactivate_doctor,
    generate_unique_doctor_id,
    get_doctor_by_doctor_id,
    get_doctor_by_registration_number,
    get_doctor_by_user_id,
    list_doctors,
    reject_doctor,
    update_doctor,
    verify_doctor,
)

router = APIRouter(tags=["Doctor Management"])


@router.post(
    "/doctors/admin-provision",
    response_model=DoctorAdminProvisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin provision a new doctor and create associated user credentials",
)
def admin_provision_doctor(
    doctor_in: DoctorAdminCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> DoctorAdminProvisionResponse:
    """Admin-only: atomically provision a doctor staff profile and user login."""
    email_clean = doctor_in.email.strip().lower()

    # 1. Check existing user account
    user = db.query(User).filter(User.email == email_clean).first()
    temp_pwd: str | None = None

    if user:
        if user.role != UserRole.DOCTOR:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"An account with email '{email_clean}' already exists with role '{user.role.value}'.",
            )
        existing_doc = get_doctor_by_user_id(db, user_id=user.id)
        if existing_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A doctor profile already exists for {email_clean} ({existing_doc.doctor_id}).",
            )
        user.is_active = True
        user.name = doctor_in.full_name.strip()
    else:
        # Create user account securely with temporary password
        if doctor_in.temporary_password and len(doctor_in.temporary_password.strip()) >= 8:
            temp_pwd = doctor_in.temporary_password.strip()
        else:
            temp_pwd = f"DocPass@{secrets.token_hex(4).upper()}!"

        user = User(
            email=email_clean,
            name=doctor_in.full_name.strip(),
            password_hash=get_password_hash(temp_pwd),
            role=UserRole.DOCTOR,
            is_active=True,
        )
        db.add(user)
        db.flush()

    # 2. Check registration number uniqueness
    existing_reg = get_doctor_by_registration_number(db, doctor_in.medical_registration_number)
    if existing_reg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Medical license/registration number '{doctor_in.medical_registration_number}' is already registered.",
        )

    # 3. Create Doctor Profile
    doctor_id = generate_unique_doctor_id(db)
    db_doctor = Doctor(
        doctor_id=doctor_id,
        user_id=user.id,
        full_name=doctor_in.full_name.strip(),
        professional_title=doctor_in.professional_title.strip() if doctor_in.professional_title else "Dr.",
        department=doctor_in.department.strip() if doctor_in.department else "General Medicine",
        specialization=doctor_in.specialization.strip(),
        qualifications=doctor_in.qualifications.strip() if doctor_in.qualifications else None,
        medical_degree=doctor_in.medical_degree.strip() if doctor_in.medical_degree else None,
        medical_registration_number=doctor_in.medical_registration_number.strip(),
        years_of_experience=doctor_in.years_of_experience,
        email=email_clean,
        phone=doctor_in.phone.strip() if doctor_in.phone else None,
        clinic_hospital_name=doctor_in.clinic_hospital_name.strip() if doctor_in.clinic_hospital_name else None,
        consultation_location=doctor_in.consultation_location.strip() if doctor_in.consultation_location else None,
        consultation_mode=doctor_in.consultation_mode,
        professional_bio=doctor_in.professional_bio.strip() if doctor_in.professional_bio else None,
        verification_status=DoctorVerificationStatus.VERIFIED,
        availability_status=DoctorAvailabilityStatus.AVAILABLE,
    )
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)

    # 4. Audit Log
    AuditService().emit_audit_event(
        db=db,
        action="CREATE_DOCTOR",
        resource_type="Doctor",
        resource_id=db_doctor.doctor_id,
        user_id=current_user.id,
        user_role=current_user.role.value,
        outcome="SUCCESS",
        metadata={
            "created_doctor_id": db_doctor.doctor_id,
            "email": email_clean,
            "department": db_doctor.department,
            "specialization": db_doctor.specialization,
        },
    )

    return DoctorAdminProvisionResponse(
        doctor=DoctorDetailResponse.model_validate(db_doctor),
        temporary_password=temp_pwd,
        message="Doctor account created successfully.",
    )


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
    summary="Deactivate or safely remove a doctor profile",
)
def deactivate_or_delete_doctor_profile(
    doctor_id: str,
    permanent: bool = Query(False, description="Permanent deletion only permitted if no clinical history exists"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> DoctorDetailResponse:
    """Admin-only: Soft-deactivate a doctor profile or permanently delete if zero clinical history."""
    doctor = get_doctor_by_doctor_id(db, doctor_id=doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with identifier '{doctor_id}' was not found.",
        )

    if permanent:
        # Check if doctor has clinical appointments or encounters
        has_appointments = (
            db.query(Appointment)
            .filter(or_(Appointment.doctor_id == doctor.doctor_id, Appointment.doctor_id == str(doctor.id)))
            .count()
            > 0
        )
        has_encounters = (
            db.query(Encounter)
            .filter(or_(Encounter.doctor_id == doctor.doctor_id, Encounter.doctor_id == str(doctor.id)))
            .count()
            > 0
        )

        if has_appointments or has_encounters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Doctor has existing clinical records (appointments/encounters) and cannot be permanently deleted. Deactivation has been applied instead.",
            )

        user_id = doctor.user_id
        res_dto = DoctorDetailResponse.model_validate(doctor)
        db.delete(doctor)
        db.commit()

        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.is_active = False
                db.commit()

        AuditService().emit_audit_event(
            db=db,
            action="DELETE_DOCTOR",
            resource_type="Doctor",
            resource_id=doctor_id,
            user_id=current_user.id,
            user_role=current_user.role.value,
            outcome="SUCCESS",
            metadata={"deleted_doctor_id": doctor_id, "permanent": True},
        )
        return res_dto

    # Default: Soft deactivation
    deactivated = deactivate_doctor(db, doctor=doctor)
    if doctor.user_id:
        user = db.query(User).filter(User.id == doctor.user_id).first()
        if user:
            user.is_active = False
            db.commit()

    AuditService().emit_audit_event(
        db=db,
        action="DEACTIVATE_DOCTOR",
        resource_type="Doctor",
        resource_id=doctor_id,
        user_id=current_user.id,
        user_role=current_user.role.value,
        outcome="SUCCESS",
        metadata={"deactivated_doctor_id": doctor_id},
    )
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
    if doctor.user_id:
        user = db.query(User).filter(User.id == doctor.user_id).first()
        if user:
            user.is_active = True
            db.commit()

    AuditService().emit_audit_event(
        db=db,
        action="VERIFY_DOCTOR",
        resource_type="Doctor",
        resource_id=doctor_id,
        user_id=current_user.id,
        user_role=current_user.role.value,
        outcome="SUCCESS",
        metadata={"verified_doctor_id": doctor_id},
    )
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
    if doctor.user_id:
        user = db.query(User).filter(User.id == doctor.user_id).first()
        if user:
            user.is_active = False
            db.commit()

    AuditService().emit_audit_event(
        db=db,
        action="REJECT_DOCTOR",
        resource_type="Doctor",
        resource_id=doctor_id,
        user_id=current_user.id,
        user_role=current_user.role.value,
        outcome="SUCCESS",
        metadata={"rejected_doctor_id": doctor_id, "reason": reject_in.rejection_reason},
    )
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
    if doctor.user_id:
        user = db.query(User).filter(User.id == doctor.user_id).first()
        if user:
            user.is_active = True
            db.commit()

    AuditService().emit_audit_event(
        db=db,
        action="ACTIVATE_DOCTOR",
        resource_type="Doctor",
        resource_id=doctor_id,
        user_id=current_user.id,
        user_role=current_user.role.value,
        outcome="SUCCESS",
        metadata={"activated_doctor_id": doctor_id},
    )
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
    if current_user.role == UserRole.ADMIN and doctor.user_id:
        user = db.query(User).filter(User.id == doctor.user_id).first()
        if user:
            user.is_active = False
            db.commit()

    AuditService().emit_audit_event(
        db=db,
        action="DEACTIVATE_DOCTOR",
        resource_type="Doctor",
        resource_id=doctor_id,
        user_id=current_user.id,
        user_role=current_user.role.value,
        outcome="SUCCESS",
        metadata={"deactivated_doctor_id": doctor_id},
    )
    return DoctorDetailResponse.model_validate(deactivated)

