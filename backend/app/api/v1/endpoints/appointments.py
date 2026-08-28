from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCancelRequest,
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentUpdate,
)
from app.schemas.user import UserRole
from app.services.appointment_service import (
    build_appointment_response,
    cancel_appointment,
    complete_appointment,
    confirm_appointment,
    create_appointment,
    get_appointment_by_id,
    list_appointments,
    update_appointment,
)

router = APIRouter(tags=["Appointments"])


def _check_appointment_access(appointment: Appointment, current_user: User, db: Session) -> None:
    """Verify if the user has permission to view or manage the appointment."""
    if current_user.role in (UserRole.ADMIN, UserRole.HEALTHCARE_STAFF):
        return

    if current_user.role == UserRole.DOCTOR:
        doctor = db.scalars(select(Doctor).where(Doctor.user_id == current_user.id)).first()
        if doctor and appointment.doctor_id == doctor.id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access appointments for another doctor.",
        )

    # Patient role or regular user matching patient email
    if current_user.role == UserRole.PATIENT or current_user.email:
        patient = appointment.patient
        if patient and patient.email and patient.email.lower() == current_user.email.lower():
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this appointment.",
        )


@router.post(
    "/appointments",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule a new appointment",
)
def schedule_appointment(
    appointment_in: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AppointmentResponse:
    """Create a new patient-doctor appointment with validation and conflict checks."""
    try:
        appointment = create_appointment(db, appointment_in=appointment_in)
        return build_appointment_response(appointment)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/appointments",
    response_model=AppointmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter scheduled appointments",
)
def get_appointments_list(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    patient_id: int | None = Query(None, description="Filter by patient database ID"),
    doctor_id: int | None = Query(None, description="Filter by doctor database ID"),
    status_filter: AppointmentStatus | None = Query(None, alias="status", description="Filter by appointment status"),
    from_date: datetime | None = Query(None, description="Filter appointments from this datetime onwards"),
    to_date: datetime | None = Query(None, description="Filter appointments up to this datetime"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AppointmentListResponse:
    """Retrieve appointments filtered by role permissions and query parameters."""
    target_patient_id = patient_id
    target_doctor_id = doctor_id

    # Role-based restriction
    if current_user.role == UserRole.DOCTOR:
        doctor = db.scalars(select(Doctor).where(Doctor.user_id == current_user.id)).first()
        if doctor:
            target_doctor_id = doctor.id
        else:
            return AppointmentListResponse.create(items=[], total=0, page=page, size=size)
    elif current_user.role == UserRole.PATIENT:
        patient = db.scalars(select(Patient).where(Patient.email == current_user.email)).first()
        if patient:
            target_patient_id = patient.id
        else:
            return AppointmentListResponse.create(items=[], total=0, page=page, size=size)

    appointments, total = list_appointments(
        db,
        patient_id=target_patient_id,
        doctor_id=target_doctor_id,
        status=status_filter,
        from_date=from_date,
        to_date=to_date,
        page=page,
        size=size,
    )

    items = [build_appointment_response(apt) for apt in appointments]
    return AppointmentListResponse.create(items=items, total=total, page=page, size=size)


@router.get(
    "/appointments/{appointment_id}",
    response_model=AppointmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get appointment details by ID",
)
def get_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AppointmentResponse:
    """Retrieve specific appointment details by integer ID or public appointment_id."""
    appointment = get_appointment_by_id(db, identifier=appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment '{appointment_id}' was not found.",
        )

    _check_appointment_access(appointment, current_user, db)
    return build_appointment_response(appointment)


@router.patch(
    "/appointments/{appointment_id}",
    response_model=AppointmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update scheduled appointment",
)
def patch_appointment(
    appointment_id: str,
    appointment_in: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AppointmentResponse:
    """Update appointment details, time, or clinical notes."""
    appointment = get_appointment_by_id(db, identifier=appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment '{appointment_id}' was not found.",
        )

    _check_appointment_access(appointment, current_user, db)

    try:
        updated = update_appointment(db, appointment=appointment, appointment_in=appointment_in)
        return build_appointment_response(updated)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/appointments/{appointment_id}/confirm",
    response_model=AppointmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm scheduled appointment",
)
def confirm_scheduled_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AppointmentResponse:
    """Confirm a scheduled appointment (Admin, Staff, or assigned Doctor)."""
    appointment = get_appointment_by_id(db, identifier=appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment '{appointment_id}' was not found.",
        )

    _check_appointment_access(appointment, current_user, db)

    if current_user.role == UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients cannot confirm their own appointments. Confirmation is performed by clinic staff or doctors.",
        )

    try:
        confirmed = confirm_appointment(db, appointment=appointment)
        return build_appointment_response(confirmed)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel an appointment",
)
def cancel_scheduled_appointment(
    appointment_id: str,
    cancel_in: AppointmentCancelRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AppointmentResponse:
    """Cancel an appointment with documented cancellation reason."""
    appointment = get_appointment_by_id(db, identifier=appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment '{appointment_id}' was not found.",
        )

    _check_appointment_access(appointment, current_user, db)

    reason = cancel_in.cancellation_reason if cancel_in else None
    try:
        cancelled = cancel_appointment(db, appointment=appointment, cancellation_reason=reason)
        return build_appointment_response(cancelled)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/appointments/{appointment_id}/complete",
    response_model=AppointmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete an appointment",
)
def complete_scheduled_appointment(
    appointment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> AppointmentResponse:
    """Mark an appointment as completed after consultation (Staff, Admin, or assigned Doctor)."""
    appointment = get_appointment_by_id(db, identifier=appointment_id)
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment '{appointment_id}' was not found.",
        )

    _check_appointment_access(appointment, current_user, db)

    if current_user.role == UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients cannot mark appointments as completed.",
        )

    try:
        completed = complete_appointment(db, appointment=appointment)
        return build_appointment_response(completed)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
