"""SQLAlchemy ORM Model for Clinical Transitions of Care & Shift Handoffs.

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


class ClinicalHandoff(Base):
    """Represents a structured clinical handover between clinicians or departments."""

    __tablename__ = "clinical_handoffs"

    id = Column(Integer, primary_key=True, index=True)
    handoff_id = Column(String(32), unique=True, index=True, nullable=False)
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
    sender_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    receiver_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    framework = Column(String(20), default="ipass", nullable=False)  # ipass, sbar
    handoff_type = Column(
        String(30), default="shift_change", nullable=False
    )  # shift_change, unit_transfer, discharge_transition, service_consultation
    illness_severity = Column(
        String(20), default="stable", nullable=False
    )  # stable, watcher, unstable
    status = Column(
        String(20), default="draft", nullable=False, index=True
    )  # draft, active, acknowledged, completed, cancelled

    summary = Column(Text, nullable=False)
    action_items_json = Column(JSON, nullable=True)  # List of HandoffActionItem dicts
    situational_awareness_json = Column(
        JSON, nullable=True
    )  # List of ContingencyPlan dicts
    synthesis_notes = Column(Text, nullable=True)  # Receiver readback notes

    is_ai_generated = Column(Boolean, default=True, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

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
    patient = relationship("Patient", backref="handoffs")
    encounter = relationship("Encounter", backref="handoffs")
    sender = relationship("User", foreign_keys=[sender_user_id])
    receiver = relationship("User", foreign_keys=[receiver_user_id])

    def __repr__(self) -> str:
        return f"<ClinicalHandoff {self.handoff_id} patient={self.patient_id} framework={self.framework} status={self.status}>"
