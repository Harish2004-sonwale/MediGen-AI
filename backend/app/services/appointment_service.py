from datetime import datetime, timedelta, timezone
import secrets
from typing import Union
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentUpdate,
)
from app.schemas.doctor import DoctorVerificationStatus
from app.schemas.patient import PatientStatus


def generate_unique_appointment_id(db: Session) -> str:
    """Generate a unique human-readable public appointment ID (e.g. APT-20260828-A1B2)."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    for _ in range(10):
        random_suffix = secrets.token_hex(2).upper()
        candidate = f"APT-{date_part}-{random_suffix}"
        exists = db.scalar(select(Appointment.id).where(Appointment.appointment_id == candidate))
        if not exists:
            return candidate
    return f"APT-{date_part}-{secrets.token_hex(4).upper()}"


def resolve_patient(db: Session, patient_ref: Union[int, str]) -> Patient | None:
    """Resolve Patient entity by integer primary key or public patient_id."""
    if isinstance(patient_ref, int) or (isinstance(patient_ref, str) and patient_ref.isdigit()):
        patient = db.scalars(select(Patient).where(Patient.id == int(patient_ref))).first()
        if patient:
            return patient
    return db.scalars(select(Patient).where(Patient.patient_id == str(patient_ref).strip())).first()


def resolve_doctor(db: Session, doctor_ref: Union[int, str]) -> Doctor | None:
    """Resolve Doctor entity by integer primary key or public doctor_id."""
    if isinstance(doctor_ref, int) or (isinstance(doctor_ref, str) and doctor_ref.isdigit()):
        doctor = db.scalars(select(Doctor).where(Doctor.id == int(doctor_ref))).first()
        if doctor:
            return doctor
    return db.scalars(select(Doctor).where(Doctor.doctor_id == str(doctor_ref).strip())).first()


def check_doctor_slot_conflict(
    db: Session,
    doctor_id: int,
    start_time: datetime,
    duration_minutes: int,
    exclude_appointment_id: int | None = None,
) -> bool:
    """Check if the doctor has an overlapping scheduled or confirmed appointment."""
    end_time = start_time + timedelta(minutes=duration_minutes)

    stmt = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]),
    )

    if exclude_appointment_id is not None:
        stmt = stmt.where(Appointment.id != exclude_appointment_id)

    existing_appointments = db.scalars(stmt).all()

    for apt in existing_appointments:
        apt_start = apt.appointment_date
        if apt_start.tzinfo is None:
            apt_start = apt_start.replace(tzinfo=timezone.utc)
        apt_end = apt_start + timedelta(minutes=apt.duration_minutes)

        check_start = start_time if start_time.tzinfo is not None else start_time.replace(tzinfo=timezone.utc)
        check_end = end_time if end_time.tzinfo is not None else end_time.replace(tzinfo=timezone.utc)

        if check_start < apt_end and check_end > apt_start:
            return True

    return False


def build_appointment_response(appointment: Appointment) -> AppointmentResponse:
    """Convert Appointment ORM model to rich response schema."""
    patient = appointment.patient
    doctor = appointment.doctor

    patient_name = f"{patient.first_name} {patient.last_name}" if patient else "Unknown Patient"
    patient_public_id = patient.patient_id if patient else ""

    doctor_name = f"{doctor.professional_title} {doctor.full_name}" if doctor else "Unknown Doctor"
    doctor_public_id = doctor.doctor_id if doctor else ""
    doctor_department = doctor.department if doctor else "General Medicine"
    doctor_specialization = doctor.specialization if doctor else "General Medicine"

    return AppointmentResponse(
        id=appointment.id,
        appointment_id=appointment.appointment_id,
        patient_id=appointment.patient_id,
        patient_public_id=patient_public_id,
        patient_name=patient_name,
        doctor_id=appointment.doctor_id,
        doctor_public_id=doctor_public_id,
        doctor_name=doctor_name,
        doctor_department=doctor_department,
        doctor_specialization=doctor_specialization,
        appointment_date=appointment.appointment_date,
        duration_minutes=appointment.duration_minutes,
        consultation_mode=appointment.consultation_mode,
        reason_for_visit=appointment.reason_for_visit,
        status=appointment.status,
        notes=appointment.notes,
        cancellation_reason=appointment.cancellation_reason,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at,
    )


def create_appointment(db: Session, appointment_in: AppointmentCreate) -> Appointment:
    """Validate prerequisites and schedule a new appointment."""
    patient = resolve_patient(db, appointment_in.patient_id)
    if not patient:
        raise ValueError(f"Patient reference '{appointment_in.patient_id}' was not found.")

    if patient.status != PatientStatus.ACTIVE:
        raise ValueError("Cannot schedule appointment for an inactive or deactivated patient.")

    doctor = resolve_doctor(db, appointment_in.doctor_id)
    if not doctor:
        raise ValueError(f"Doctor reference '{appointment_in.doctor_id}' was not found.")

    if doctor.verification_status != DoctorVerificationStatus.VERIFIED:
        raise ValueError(f"Doctor '{doctor.full_name}' is not verified (status: {doctor.verification_status}).")

    # Time validation
    apt_date = appointment_in.appointment_date
    now = datetime.now(timezone.utc)
    check_date = apt_date if apt_date.tzinfo is not None else apt_date.replace(tzinfo=timezone.utc)
    if check_date <= now:
        raise ValueError("Appointment date and time must be scheduled for a future time.")

    # Slot conflict validation
    has_conflict = check_doctor_slot_conflict(
        db=db,
        doctor_id=doctor.id,
        start_time=apt_date,
        duration_minutes=appointment_in.duration_minutes,
    )
    if has_conflict:
        raise ValueError(
            f"Doctor {doctor.full_name} is already booked for another appointment during this time window."
        )

    appointment_id = generate_unique_appointment_id(db)

    db_appointment = Appointment(
        appointment_id=appointment_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=apt_date,
        duration_minutes=appointment_in.duration_minutes,
        consultation_mode=appointment_in.consultation_mode,
        reason_for_visit=appointment_in.reason_for_visit.strip(),
        status=AppointmentStatus.SCHEDULED,
        notes=appointment_in.notes.strip() if appointment_in.notes else None,
    )

    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment


def get_appointment_by_id(db: Session, identifier: Union[int, str]) -> Appointment | None:
    """Retrieve appointment by integer ID or public appointment_id string."""
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        apt = db.scalars(select(Appointment).where(Appointment.id == int(identifier))).first()
        if apt:
            return apt
    return db.scalars(select(Appointment).where(Appointment.appointment_id == str(identifier).strip())).first()


def list_appointments(
    db: Session,
    patient_id: int | None = None,
    doctor_id: int | None = None,
    status: AppointmentStatus | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[Appointment], int]:
    """Retrieve filtered and paginated list of appointments."""
    query = select(Appointment)

    filters = []
    if patient_id is not None:
        filters.append(Appointment.patient_id == patient_id)
    if doctor_id is not None:
        filters.append(Appointment.doctor_id == doctor_id)
    if status is not None:
        filters.append(Appointment.status == status)
    if from_date is not None:
        filters.append(Appointment.appointment_date >= from_date)
    if to_date is not None:
        filters.append(Appointment.appointment_date <= to_date)

    if filters:
        query = query.where(*filters)

    # Count total
    all_matching = list(db.scalars(query).all())
    total = len(all_matching)

    # Order by appointment date ascending
    query = query.order_by(Appointment.appointment_date.asc())

    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    appointments = list(db.scalars(query).all())
    return appointments, total


def update_appointment(
    db: Session,
    appointment: Appointment,
    appointment_in: AppointmentUpdate,
) -> Appointment:
    """Update appointment fields with slot and lifecycle validation."""
    update_data = appointment_in.model_dump(exclude_unset=True)

    new_date = update_data.get("appointment_date", appointment.appointment_date)
    new_duration = update_data.get("duration_minutes", appointment.duration_minutes)

    if "appointment_date" in update_data or "duration_minutes" in update_data:
        now = datetime.now(timezone.utc)
        check_date = new_date if new_date.tzinfo is not None else new_date.replace(tzinfo=timezone.utc)
        if check_date <= now:
            raise ValueError("Updated appointment date and time must be in the future.")

        has_conflict = check_doctor_slot_conflict(
            db=db,
            doctor_id=appointment.doctor_id,
            start_time=new_date,
            duration_minutes=new_duration,
            exclude_appointment_id=appointment.id,
        )
        if has_conflict:
            raise ValueError("Doctor is already booked for another appointment during this new time window.")

    for field, value in update_data.items():
        if value is not None:
            if isinstance(value, str):
                setattr(appointment, field, value.strip())
            else:
                setattr(appointment, field, value)

    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def confirm_appointment(db: Session, appointment: Appointment) -> Appointment:
    """Confirm a scheduled appointment."""
    if appointment.status not in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
        raise ValueError(f"Cannot confirm an appointment with current status '{appointment.status.value}'.")

    appointment.status = AppointmentStatus.CONFIRMED
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def cancel_appointment(
    db: Session,
    appointment: Appointment,
    cancellation_reason: str | None = None,
) -> Appointment:
    """Cancel an existing appointment."""
    if appointment.status in (AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED):
        raise ValueError(f"Cannot cancel an appointment that is already {appointment.status.value}.")

    appointment.status = AppointmentStatus.CANCELLED
    if cancellation_reason:
        appointment.cancellation_reason = cancellation_reason.strip()

    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def complete_appointment(db: Session, appointment: Appointment) -> Appointment:
    """Mark an appointment as completed following clinical consultation."""
    if appointment.status not in (AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED):
        raise ValueError(f"Cannot complete an appointment with current status '{appointment.status.value}'.")

    appointment.status = AppointmentStatus.COMPLETED
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment
