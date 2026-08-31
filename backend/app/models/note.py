"""SQLAlchemy model for Clinical Notes & AI Scribe Synthesis."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.schemas.note import NoteStatus, NoteType

if TYPE_CHECKING:
    from app.models.encounter import Encounter
    from app.models.patient import Patient
    from app.models.user import User


class ClinicalNote(Base):
    """ClinicalNote ORM model representing structured medical notes and physician signoffs."""

    __tablename__ = "clinical_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    note_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    author_user_id: Mapped[Optional[int]] = mapped_column(
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
    note_type: Mapped[NoteType] = mapped_column(
        Enum(
            NoteType,
            name="note_type",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=NoteType.SOAP,
        index=True,
        nullable=False,
    )
    status: Mapped[NoteStatus] = mapped_column(
        Enum(
            NoteStatus,
            name="note_status",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=NoteStatus.DRAFT,
        index=True,
        nullable=False,
    )
    content_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_clinician_review: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    signed_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    signed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", backref="clinical_notes")
    author: Mapped[Optional["User"]] = relationship("User", foreign_keys=[author_user_id])
    signed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[signed_by_user_id])
    encounter: Mapped[Optional["Encounter"]] = relationship("Encounter")
