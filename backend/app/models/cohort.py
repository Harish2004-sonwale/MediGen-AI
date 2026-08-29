"""SQLAlchemy ORM models for Patient Cohorts, Disease Registries & Memberships.

Phase 9.0.11: Clinical Cohort Analytics, Patient Registry Management & Longitudinal Risk Stratification.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.base import Base



def utc_now():
    return datetime.now(timezone.utc)


class PatientCohort(Base):
    """Authoritative disease registry or patient cohort definition."""

    __tablename__ = "patient_cohorts"

    id = Column(Integer, primary_key=True, index=True)
    cohort_id = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    cohort_type = Column(String(50), default="disease_registry", nullable=False, index=True)
    criteria_json = Column(JSON, nullable=True)
    is_dynamic = Column(Boolean, default=True, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    memberships = relationship("CohortMembership", back_populates="cohort", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PatientCohort id={self.id} cohort_id='{self.cohort_id}' name='{self.name}' type='{self.cohort_type}'>"


class CohortMembership(Base):
    """Link table associating a patient to a patient cohort/registry."""

    __tablename__ = "cohort_memberships"
    __table_args__ = (
        UniqueConstraint("cohort_id", "patient_id", name="uq_cohort_patient_membership"),
    )

    id = Column(Integer, primary_key=True, index=True)
    cohort_id = Column(Integer, ForeignKey("patient_cohorts.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    enrolled_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    status = Column(String(30), default="active", nullable=False)  # active, graduated, excluded
    notes = Column(Text, nullable=True)

    # Relationships
    cohort = relationship("PatientCohort", back_populates="memberships")
    patient = relationship("Patient")

    def __repr__(self) -> str:
        return f"<CohortMembership id={self.id} cohort_id={self.cohort_id} patient_id={self.patient_id} status='{self.status}'>"
