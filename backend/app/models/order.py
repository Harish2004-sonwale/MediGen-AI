"""SQLAlchemy ORM models for Computerized Physician Order Entry (CPOE) and Diagnostic Results.

Phase 9.0.13: Computerized Physician Order Entry (CPOE), Diagnostic Order Lifecycle & Closed-Loop Critical Result Tracking.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.base import Base


class ClinicalOrder(Base):
    """Represents a structured clinical order (lab, imaging, medication, nursing, consult)."""

    __tablename__ = "clinical_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id = Column(String(32), unique=True, index=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True, index=True)
    ordering_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    order_category = Column(String(30), nullable=False, default="laboratory", index=True)  # laboratory, imaging, medication, nursing, consultation
    order_type = Column(String(100), nullable=False, index=True)  # cbc_with_diff, chest_xray_pa, etc.
    priority = Column(String(20), nullable=False, default="routine")  # routine, urgent, stat
    status = Column(String(20), nullable=False, default="draft", index=True)  # draft, placed, in_progress, completed, cancelled

    clinical_indication = Column(Text, nullable=False)
    specimen_source = Column(String(100), nullable=True)
    order_details_json = Column(JSON, nullable=True)
    ai_safety_flags_json = Column(JSON, nullable=True)
    is_ai_suggested = Column(Boolean, default=False, nullable=False)

    placed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    patient = relationship("Patient", backref="clinical_orders")
    encounter = relationship("Encounter", backref="clinical_orders")
    ordering_user = relationship("User", foreign_keys=[ordering_user_id])
    results = relationship("DiagnosticResult", back_populates="order", cascade="all, delete-orphan")


class DiagnosticResult(Base):
    """Represents a diagnostic result / laboratory panel associated with an order."""

    __tablename__ = "diagnostic_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    result_id = Column(String(32), unique=True, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("clinical_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True)
    encounter_id = Column(Integer, ForeignKey("encounters.id", ondelete="SET NULL"), nullable=True, index=True)

    test_name = Column(String(255), nullable=False, index=True)
    test_code_loinc = Column(String(50), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="final", index=True)  # preliminary, final, amended, corrected
    abnormal_flag = Column(String(20), nullable=False, default="normal", index=True)  # normal, abnormal_low, abnormal_high, panic_critical

    findings_summary = Column(Text, nullable=False)
    numeric_value = Column(Float, nullable=True)
    unit_of_measure = Column(String(50), nullable=True)
    reference_range_low = Column(Float, nullable=True)
    reference_range_high = Column(Float, nullable=True)
    critical_threshold_low = Column(Float, nullable=True)
    critical_threshold_high = Column(Float, nullable=True)
    structured_components_json = Column(JSON, nullable=True)

    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    resulted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    order = relationship("ClinicalOrder", back_populates="results")
    patient = relationship("Patient", backref="diagnostic_results")
    encounter = relationship("Encounter", backref="diagnostic_results")
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by_user_id])
