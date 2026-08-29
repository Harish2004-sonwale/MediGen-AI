"""SQLAlchemy model for Clinical Decision Support Alerts."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.schemas.alert import AlertSeverity, AlertStatus

if TYPE_CHECKING:
    from app.models.encounter import Encounter
    from app.models.patient import Patient
    from app.models.user import User
    from app.models.vital import VitalTelemetry


class ClinicalAlert(Base):
    """ClinicalAlert ORM model tracking persistent CDS alerts and acknowledgement lifecycle."""

    __tablename__ = "clinical_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
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
    reading_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("vital_telemetry.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    alert_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(
            AlertSeverity,
            name="alert_severity",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AlertSeverity.MODERATE,
        index=True,
        nullable=False,
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(
            AlertStatus,
            name="alert_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AlertStatus.ACTIVE,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    parameters_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    recurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Clinician Review / Action Fields
    acknowledged_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    dismissal_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    last_triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", backref="clinical_alerts")
    encounter: Mapped[Optional["Encounter"]] = relationship("Encounter")
    vital_reading: Mapped[Optional["VitalTelemetry"]] = relationship("VitalTelemetry")
    acknowledged_by: Mapped[Optional["User"]] = relationship("User")
