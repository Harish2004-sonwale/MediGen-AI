from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.schemas.encounter import EncounterStatus, EncounterType

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.user import User


class Encounter(Base):
    """Encounter ORM model representing clinician-authored medical consultations and records."""

    __tablename__ = "encounters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    encounter_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    attending_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    encounter_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        index=True,
        nullable=False,
    )
    encounter_type: Mapped[EncounterType] = mapped_column(
        Enum(EncounterType, name="encounter_type", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=EncounterType.INITIAL_CONSULTATION,
        nullable=False,
    )
    chief_complaint: Mapped[str] = mapped_column(String(255), nullable=False)
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EncounterStatus] = mapped_column(
        Enum(EncounterStatus, name="encounter_status", native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=EncounterStatus.COMPLETED,
        index=True,
        nullable=False,
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
        onupdate=func.now(),
        default=func.now(),
        nullable=False,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="encounters", lazy="joined")
    attending_user: Mapped["User | None"] = relationship("User", back_populates="encounters", lazy="joined")

    def __repr__(self) -> str:
        return f"<Encounter id={self.id} encounter_id={self.encounter_id} patient_id={self.patient_id} type={self.encounter_type}>"
