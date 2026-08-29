"""SQLAlchemy model for Vital Telemetry Ingestion."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.encounter import Encounter
    from app.models.patient import Patient


class VitalTelemetry(Base):
    """VitalTelemetry ORM model storing structured physiological measurements."""

    __tablename__ = "vital_telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    reading_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    encounter_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("encounters.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Core Vital Signs
    heart_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    systolic_bp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    diastolic_bp: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    respiratory_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    temperature_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spo2_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Source & Device Provenance
    device_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual_entry", nullable=False)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", backref="vital_readings")
    encounter: Mapped[Optional["Encounter"]] = relationship("Encounter")
