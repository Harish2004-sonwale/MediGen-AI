"""SQLAlchemy ORM Model for Clinical Discharge Protocols & Continuity of Care.

Phase 9.0.12: Clinical Transitions of Care, Multi-Disciplinary Handoffs (I-PASS/SBAR) & Automated Discharge Protocol Synthesis.
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
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class DischargeProtocol(Base):
    """Represents a structured multi-disciplinary clinical discharge package."""

    __tablename__ = "discharge_protocols"

    id = Column(Integer, primary_key=True, index=True)
    discharge_id = Column(String(32), unique=True, index=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    encounter_id = Column(
        Integer,
        ForeignKey("encounters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    attending_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    nurse_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    pharmacist_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    status = Column(
        String(20), default="draft", nullable=False, index=True
    )  # draft, under_review, ready_for_discharge, completed, cancelled
    disposition = Column(
        String(40), default="home_self_care", nullable=False
    )  # home_self_care, home_health_services, skilled_nursing_facility, rehab_facility, hospice, transfer_acute_care
    discharge_date = Column(DateTime(timezone=True), nullable=True)

    hospital_course_summary = Column(Text, nullable=False)
    primary_discharge_diagnosis = Column(String(255), nullable=False)
    secondary_diagnoses_json = Column(JSON, nullable=True)  # List of string diagnoses
    medication_reconciliation_json = Column(
        JSON, nullable=True
    )  # List of MedicationReconciliationItem dicts
    followup_instructions_json = Column(
        JSON, nullable=True
    )  # List of FollowupAppointmentItem dicts
    pending_tests_json = Column(
        JSON, nullable=True
    )  # List of PendingDiagnosticItem dicts
    warning_symptoms_json = Column(
        JSON, nullable=True
    )  # List of WarningSymptomItem dicts
    activity_and_diet_instructions = Column(Text, nullable=True)

    is_ai_generated = Column(Boolean, default=True, nullable=False)
    signed_off_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    patient = relationship("Patient", backref="discharge_protocols")
    encounter = relationship("Encounter", backref="discharge_protocols")
    attending = relationship("User", foreign_keys=[attending_user_id])
    nurse = relationship("User", foreign_keys=[nurse_user_id])
    pharmacist = relationship("User", foreign_keys=[pharmacist_user_id])

    def __repr__(self) -> str:
        return f"<DischargeProtocol {self.discharge_id} patient={self.patient_id} status={self.status} disposition={self.disposition}>"
