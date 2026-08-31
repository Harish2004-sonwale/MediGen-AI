"""SQLAlchemy model for Multi-Modal Medical Diagnostics and Clinical Imaging."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.schemas.media import MediaBodySite, MediaModality, MediaStatus

if TYPE_CHECKING:
    from app.models.encounter import Encounter
    from app.models.patient import Patient
    from app.models.user import User


class DiagnosticMedia(Base):
    """DiagnosticMedia ORM model representing uploaded clinical media and multi-modal AI analysis."""

    __tablename__ = "diagnostic_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    media_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    uploader_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    encounter_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("encounters.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    facility_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True, default="FAC-001")
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    modality: Mapped[MediaModality] = mapped_column(
        Enum(
            MediaModality,
            name="media_modality",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MediaModality.OTHER,
        index=True,
        nullable=False,
    )
    body_site: Mapped[Optional[MediaBodySite]] = mapped_column(
        Enum(
            MediaBodySite,
            name="media_body_site",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[MediaStatus] = mapped_column(
        Enum(
            MediaStatus,
            name="media_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=MediaStatus.UPLOADED,
        index=True,
        nullable=False,
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    findings_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structured_findings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    anomalies_detected: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    requires_clinician_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    clinician_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    clinician_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", backref="diagnostic_media")
    uploader: Mapped[Optional["User"]] = relationship("User")
    encounter: Mapped[Optional["Encounter"]] = relationship("Encounter")
