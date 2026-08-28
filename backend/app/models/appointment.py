from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.schemas.appointment import AppointmentStatus
from app.schemas.doctor import ConsultationMode

if TYPE_CHECKING:
    from app.models.doctor import Doctor
    from app.models.patient import Patient


class Appointment(Base):
    """Appointment ORM model representing patient-doctor consultation schedules."""

    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    appointment_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    doctor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("doctors.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    appointment_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    consultation_mode: Mapped[ConsultationMode] = mapped_column(
        Enum(
            ConsultationMode,
            name="consultation_mode",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ConsultationMode.IN_PERSON,
        nullable=False,
    )
    reason_for_visit: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(
            AppointmentStatus,
            name="appointment_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AppointmentStatus.SCHEDULED,
        index=True,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=func.now(),
        nullable=False,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", lazy="joined")
    doctor: Mapped["Doctor"] = relationship("Doctor", lazy="joined")

    def __repr__(self) -> str:
        return f"<Appointment id={self.id} appointment_id={self.appointment_id} status={self.status} date={self.appointment_date}>"
