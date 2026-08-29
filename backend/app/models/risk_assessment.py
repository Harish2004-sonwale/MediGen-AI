"""SQLAlchemy ORM model for Clinical Risk Stratification Assessments.

Phase 9.0.11: Clinical Cohort Analytics, Patient Registry Management & Longitudinal Risk Stratification.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship

from app.database.base import Base



def utc_now():
    return datetime.now(timezone.utc)


class ClinicalRiskAssessment(Base):
    """Authoritative clinical risk assessment record."""

    __tablename__ = "clinical_risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(String(32), unique=True, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True)

    risk_type = Column(String(50), nullable=False, index=True)
    risk_score = Column(Float, nullable=False)  # 0.0 to 100.0
    risk_tier = Column(String(20), default="MODERATE", nullable=False, index=True)
    predicted_outcome = Column(String(255), nullable=False)

    contributing_factors_json = Column(JSON, nullable=True)
    mitigation_recommendations_json = Column(JSON, nullable=True)

    assessed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_ai_generated = Column(Boolean, default=True, nullable=False)

    assessed_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    patient = relationship("Patient")
    encounter = relationship("Encounter")
    assessed_by_user = relationship("User", foreign_keys=[assessed_by_user_id])

    def __repr__(self) -> str:
        return (
            f"<ClinicalRiskAssessment id={self.id} assessment_id='{self.assessment_id}' "
            f"patient_id={self.patient_id} type='{self.risk_type}' score={self.risk_score} tier='{self.risk_tier}'>"
        )
