from datetime import datetime
from enum import Enum
import math
from typing import Union
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.doctor import ConsultationMode


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class AppointmentBase(BaseModel):
    appointment_date: datetime = Field(
        ...,
        description="Scheduled appointment date and time (must be in the future)",
    )
    duration_minutes: int = Field(
        default=30,
        ge=10,
        le=240,
        description="Duration of appointment in minutes (10 to 240)",
    )
    consultation_mode: ConsultationMode = Field(
        default=ConsultationMode.IN_PERSON,
        description="Consultation format (in_person, telehealth, both)",
    )
    reason_for_visit: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Primary reason or chief symptom for the medical appointment",
    )
    notes: str | None = Field(
        default=None,
        description="Additional preparation notes or clinical context",
    )


class AppointmentCreate(AppointmentBase):
    patient_id: Union[int, str] = Field(
        ...,
        description="Patient ID (database integer ID or public patient_id string like PAT-...)",
    )
    doctor_id: Union[int, str] = Field(
        ...,
        description="Doctor ID (database integer ID or public doctor_id string like DOC-...)",
    )


class AppointmentUpdate(BaseModel):
    appointment_date: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=10, le=240)
    consultation_mode: ConsultationMode | None = None
    reason_for_visit: str | None = Field(default=None, min_length=3, max_length=255)
    notes: str | None = None
    status: AppointmentStatus | None = None
    cancellation_reason: str | None = Field(default=None, max_length=500)


class AppointmentCancelRequest(BaseModel):
    cancellation_reason: str | None = Field(
        default=None,
        max_length=500,
        description="Optional reason for cancelling the scheduled appointment",
    )


class AppointmentRejectRequest(BaseModel):
    rejection_reason: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Reason for declining the appointment request",
    )


class AppointmentResponse(BaseModel):
    id: int
    appointment_id: str
    patient_id: int
    patient_public_id: str
    patient_name: str
    doctor_id: int
    doctor_public_id: str
    doctor_name: str
    doctor_department: str
    doctor_specialization: str
    appointment_date: datetime
    duration_minutes: int
    consultation_mode: ConsultationMode
    reason_for_visit: str
    status: AppointmentStatus
    notes: str | None = None
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AppointmentListResponse(BaseModel):
    items: list[AppointmentResponse]
    total: int
    page: int
    size: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[AppointmentResponse],
        total: int,
        page: int,
        size: int,
    ) -> "AppointmentListResponse":
        total_pages = math.ceil(total / size) if size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )
