from datetime import datetime
import secrets
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.doctor import (
    ConsultationMode,
    DoctorAdminUpdate,
    DoctorAvailabilityStatus,
    DoctorCreate,
    DoctorUpdate,
    DoctorVerificationStatus,
)
from app.services.user_service import get_user_by_id


def generate_unique_doctor_id(db: Session) -> str:
    """Generate a unique doctor identifier in the format DOC-YYYYMMDD-XXXX."""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    while True:
        suffix = secrets.token_hex(2).upper()
        candidate_id = f"DOC-{date_str}-{suffix}"
        existing = db.scalars(select(Doctor.id).where(Doctor.doctor_id == candidate_id)).first()
        if not existing:
            return candidate_id


def get_doctor_by_doctor_id(db: Session, doctor_id: str) -> Doctor | None:
    """Retrieve doctor by public doctor_id."""
    stmt = select(Doctor).where(Doctor.doctor_id == doctor_id.strip())
    return db.scalars(stmt).first()


def get_doctor_by_user_id(db: Session, user_id: int) -> Doctor | None:
    """Retrieve doctor profile associated with a specific user account."""
    stmt = select(Doctor).where(Doctor.user_id == user_id)
    return db.scalars(stmt).first()


def get_doctor_by_id(db: Session, id: int) -> Doctor | None:
    """Retrieve doctor by internal integer primary key."""
    stmt = select(Doctor).where(Doctor.id == id)
    return db.scalars(stmt).first()


def get_doctor_by_registration_number(db: Session, reg_number: str) -> Doctor | None:
    """Retrieve doctor by official medical registration number."""
    stmt = select(Doctor).where(Doctor.medical_registration_number == reg_number.strip())
    return db.scalars(stmt).first()


def create_doctor(
    db: Session,
    doctor_in: DoctorCreate,
    user_id: int,
) -> Doctor:
    """Create a new doctor profile associated with a user account."""
    user = get_user_by_id(db, user_id=user_id)
    if not user:
        raise ValueError(f"User account with ID {user_id} was not found.")

    existing_profile = get_doctor_by_user_id(db, user_id=user_id)
    if existing_profile:
        raise ValueError(f"User {user.email} already has an associated doctor profile ({existing_profile.doctor_id}).")

    existing_reg = get_doctor_by_registration_number(db, doctor_in.medical_registration_number)
    if existing_reg:
        raise ValueError(f"Medical registration number '{doctor_in.medical_registration_number}' is already registered.")

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
        email=user.email,
        phone=doctor_in.phone.strip() if doctor_in.phone else None,
        clinic_hospital_name=doctor_in.clinic_hospital_name.strip() if doctor_in.clinic_hospital_name else None,
        consultation_location=doctor_in.consultation_location.strip() if doctor_in.consultation_location else None,
        consultation_mode=doctor_in.consultation_mode,
        professional_bio=doctor_in.professional_bio.strip() if doctor_in.professional_bio else None,
        profile_image_url=doctor_in.profile_image_url.strip() if doctor_in.profile_image_url else None,
        verification_status=DoctorVerificationStatus.PENDING,
        availability_status=DoctorAvailabilityStatus.AVAILABLE,
    )
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor


def list_doctors(
    db: Session,
    page: int = 1,
    size: int = 20,
    department: str | None = None,
    specialization: str | None = None,
    min_experience: int | None = None,
    max_experience: int | None = None,
    location: str | None = None,
    consultation_mode: ConsultationMode | None = None,
    verification_status: DoctorVerificationStatus | None = None,
    availability_status: DoctorAvailabilityStatus | None = None,
    search: str | None = None,
    only_verified: bool = True,
) -> tuple[list[Doctor], int]:
    """Retrieve filtered and paginated list of doctors."""
    query = select(Doctor)
    count_query = select(func.count(Doctor.id))

    filters = []

    if only_verified:
        filters.append(Doctor.verification_status == DoctorVerificationStatus.VERIFIED)
    elif verification_status:
        filters.append(Doctor.verification_status == verification_status)

    if availability_status:
        filters.append(Doctor.availability_status == availability_status)

    if department:
        filters.append(Doctor.department.ilike(f"%{department.strip()}%"))

    if specialization:
        filters.append(Doctor.specialization.ilike(f"%{specialization.strip()}%"))

    if min_experience is not None:
        filters.append(Doctor.years_of_experience >= min_experience)

    if max_experience is not None:
        filters.append(Doctor.years_of_experience <= max_experience)

    if location:
        filters.append(
            or_(
                Doctor.consultation_location.ilike(f"%{location.strip()}%"),
                Doctor.clinic_hospital_name.ilike(f"%{location.strip()}%"),
            )
        )

    if consultation_mode:
        filters.append(Doctor.consultation_mode == consultation_mode)

    if search:
        search_pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Doctor.full_name.ilike(search_pattern),
                Doctor.department.ilike(search_pattern),
                Doctor.specialization.ilike(search_pattern),
                Doctor.clinic_hospital_name.ilike(search_pattern),
                Doctor.consultation_location.ilike(search_pattern),
                Doctor.doctor_id.ilike(search_pattern),
            )
        )

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    total = db.scalar(count_query) or 0

    # Order by experience descending, then name ascending
    query = query.order_by(Doctor.years_of_experience.desc(), Doctor.full_name.asc())

    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    doctors = list(db.scalars(query).all())
    return doctors, total


def update_doctor(
    db: Session,
    doctor: Doctor,
    doctor_in: DoctorUpdate | DoctorAdminUpdate,
    is_admin: bool = False,
) -> Doctor:
    """Update mutable doctor profile details."""
    update_data = doctor_in.model_dump(exclude_unset=True)

    if "medical_registration_number" in update_data:
        if not is_admin:
            update_data.pop("medical_registration_number")
        else:
            new_reg = update_data["medical_registration_number"].strip()
            if new_reg != doctor.medical_registration_number:
                existing = get_doctor_by_registration_number(db, new_reg)
                if existing and existing.id != doctor.id:
                    raise ValueError(f"Registration number '{new_reg}' is already taken.")
                update_data["medical_registration_number"] = new_reg

    if "verification_status" in update_data and not is_admin:
        update_data.pop("verification_status")

    if "rejection_reason" in update_data and not is_admin:
        update_data.pop("rejection_reason")

    for field, value in update_data.items():
        if value is not None and isinstance(value, str):
            value = value.strip()
        setattr(doctor, field, value)

    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def verify_doctor(db: Session, doctor: Doctor, note: str | None = None) -> Doctor:
    """Admin verification of doctor profile."""
    doctor.verification_status = DoctorVerificationStatus.VERIFIED
    doctor.rejection_reason = None
    doctor.availability_status = DoctorAvailabilityStatus.AVAILABLE
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def reject_doctor(db: Session, doctor: Doctor, reason: str) -> Doctor:
    """Admin rejection of doctor verification application."""
    doctor.verification_status = DoctorVerificationStatus.REJECTED
    doctor.rejection_reason = reason.strip()
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def deactivate_doctor(db: Session, doctor: Doctor) -> Doctor:
    """Soft deactivation of doctor profile."""
    doctor.verification_status = DoctorVerificationStatus.INACTIVE
    doctor.availability_status = DoctorAvailabilityStatus.UNAVAILABLE
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def activate_doctor(db: Session, doctor: Doctor) -> Doctor:
    """Reactivate doctor profile."""
    if doctor.verification_status == DoctorVerificationStatus.INACTIVE:
        doctor.verification_status = DoctorVerificationStatus.VERIFIED
    doctor.availability_status = DoctorAvailabilityStatus.AVAILABLE
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor
