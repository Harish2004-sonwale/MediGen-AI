from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.schemas.doctor import (
    ConsultationMode,
    DoctorAvailabilityStatus,
    DoctorVerificationStatus,
)

if TYPE_CHECKING:
    from app.models.user import User


class Doctor(Base):
    """Doctor ORM model representing verified medical professional profiles."""

    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    doctor_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    professional_title: Mapped[str] = mapped_column(String(50), default="Dr.", nullable=False)
    department: Mapped[str] = mapped_column(String(100), default="General Medicine", nullable=False, index=True)
    specialization: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    qualifications: Mapped[str | None] = mapped_column(String(255), nullable=True)
    medical_degree: Mapped[str | None] = mapped_column(String(100), nullable=True)
    medical_registration_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    years_of_experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    clinic_hospital_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    consultation_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    consultation_mode: Mapped[ConsultationMode] = mapped_column(
        Enum(ConsultationMode, name="consultation_mode", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=ConsultationMode.IN_PERSON,
        nullable=False,
    )
    professional_bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    profile_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_status: Mapped[DoctorVerificationStatus] = mapped_column(
        Enum(
            DoctorVerificationStatus,
            name="doctor_verification_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=DoctorVerificationStatus.PENDING,
        index=True,
        nullable=False,
    )
    availability_status: Mapped[DoctorAvailabilityStatus] = mapped_column(
        Enum(
            DoctorAvailabilityStatus,
            name="doctor_availability_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=DoctorAvailabilityStatus.AVAILABLE,
        index=True,
        nullable=False,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    user: Mapped["User"] = relationship("User", back_populates="doctor_profile", lazy="joined")

    def __repr__(self) -> str:
        return f"<Doctor id={self.id} doctor_id={self.doctor_id} name={self.full_name} spec={self.specialization} status={self.verification_status}>"
