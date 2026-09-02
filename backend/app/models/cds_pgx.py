# ==============================================================================
# MediGen AI - Phase 9.0.26: Enterprise CDS Rules, PGx & Order Sets ORM Models
# ==============================================================================

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
import enum

from app.database.base import Base


class CPICLevel(str, enum.Enum):
    LEVEL_A = "A"
    LEVEL_B = "B"
    LEVEL_C = "C"
    LEVEL_D = "D"


class PGxRiskSeverity(str, enum.Enum):
    CONTRAINDICATED = "contraindicated"
    HIGH_RISK = "high_risk"
    MODERATE_RISK = "moderate_risk"
    INFORMATIONAL = "informational"


class OrderSetCategory(str, enum.Enum):
    CRITICAL_CARE = "critical_care"
    CARDIOLOGY = "cardiology"
    ENDOCRINOLOGY = "endocrinology"
    NEUROLOGY = "neurology"
    ONCOLOGY = "oncology"
    INFECTIOUS_DISEASE = "infectious_disease"
    GENERAL_MEDICINE = "general_medicine"


class OrderSetItemType(str, enum.Enum):
    MEDICATION = "medication"
    LAB = "lab"
    RADIOLOGY = "radiology"
    NURSING = "nursing"
    CONSULT = "consult"


class OrderSetExecutionStatus(str, enum.Enum):
    DRAFT = "draft"
    EXECUTED = "executed"
    PARTIALLY_EXECUTED = "partially_executed"
    CANCELLED = "cancelled"


class CDSRuleTriggerEvent(str, enum.Enum):
    PATIENT_VIEW = "patient-view"
    ORDER_SELECT = "order-select"
    ORDER_SIGN = "order-sign"
    APPOINTMENT_BOOK = "appointment-book"


class PGxRuleDefinition(Base):
    """
    CPIC / PharmGKB Pharmacogenomic (PGx) Clinical Rule Definition.
    Maps patient genotype/phenotype to medication recommendations and risk levels.
    """
    __tablename__ = "pgx_rule_definitions"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(64), unique=True, nullable=False, index=True)
    cpic_level = Column(SAEnum(CPICLevel), default=CPICLevel.LEVEL_A, nullable=False)
    gene_symbol = Column(String(32), nullable=False, index=True)  # e.g., CYP2D6, CYP2C19, DPYD
    phenotype = Column(String(64), nullable=False, index=True)  # e.g., Poor Metabolizer, Ultrarapid
    drug_code = Column(String(64), nullable=False, index=True)  # RxNorm code
    drug_name = Column(String(128), nullable=False)  # e.g., Clopidogrel, Codeine
    risk_severity = Column(SAEnum(PGxRiskSeverity), default=PGxRiskSeverity.HIGH_RISK, nullable=False)
    clinical_implication = Column(Text, nullable=False)
    recommendation_text = Column(Text, nullable=False)
    alternative_drugs = Column(JSON, default=list)  # List of safer alternative medication names
    evidence_source = Column(String(128), default="CPIC Guidelines v2024")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ClinicalOrderSet(Base):
    """
    Multidisciplinary Evidence-Based Clinical Order Set (e.g. Sepsis Resuscitation, DKA Inpatient).
    """
    __tablename__ = "clinical_order_sets"

    id = Column(Integer, primary_key=True, index=True)
    order_set_id = Column(String(64), unique=True, nullable=False, index=True)
    code = Column(String(64), unique=True, nullable=False, index=True)  # e.g., SEPSIS_BUNDLE
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(SAEnum(OrderSetCategory), default=OrderSetCategory.GENERAL_MEDICINE, nullable=False)
    target_icd10 = Column(String(32), nullable=True)  # e.g., A41.9, E11.0
    facility_id = Column(String(64), nullable=True, index=True)  # Multi-tenant facility scope
    version = Column(String(16), default="1.0.0", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    items = relationship("ClinicalOrderSetItem", back_populates="order_set", cascade="all, delete-orphan")
    executions = relationship("OrderSetExecution", back_populates="order_set")


class ClinicalOrderSetItem(Base):
    """
    Individual order entry within a clinical order set.
    """
    __tablename__ = "clinical_order_set_items"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(String(64), unique=True, nullable=False, index=True)
    order_set_id = Column(String(64), ForeignKey("clinical_order_sets.order_set_id", ondelete="CASCADE"), nullable=False, index=True)
    item_type = Column(SAEnum(OrderSetItemType), nullable=False)
    code = Column(String(64), nullable=False)  # RxNorm / LOINC / CPT
    name = Column(String(255), nullable=False)
    default_dosage = Column(String(64), nullable=True)
    default_route = Column(String(32), nullable=True)  # IV, Oral, SubQ
    default_frequency = Column(String(32), nullable=True)  # Q4H, ONCE, STAT
    clinical_instructions = Column(Text, nullable=True)
    is_required = Column(Boolean, default=True, nullable=False)
    sequence_order = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    order_set = relationship("ClinicalOrderSet", back_populates="items")


class OrderSetExecution(Base):
    """
    Audit record of an order set execution for a specific patient encounter.
    """
    __tablename__ = "order_set_executions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(64), unique=True, nullable=False, index=True)
    order_set_id = Column(String(64), ForeignKey("clinical_order_sets.order_set_id"), nullable=False, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    facility_id = Column(String(64), nullable=False, index=True)
    ordering_provider_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(SAEnum(OrderSetExecutionStatus), default=OrderSetExecutionStatus.EXECUTED, nullable=False)
    executed_items_count = Column(Integer, default=0, nullable=False)
    generated_order_ids = Column(JSON, default=list)  # List of Order IDs created in database
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    order_set = relationship("ClinicalOrderSet", back_populates="executions")


class CDSRuleEvaluationAudit(Base):
    """
    Audit log of CDS rules and PGx checks triggered during clinician workflows.
    """
    __tablename__ = "cds_rule_evaluation_audits"

    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(String(64), unique=True, nullable=False, index=True)
    patient_id = Column(String(64), nullable=False, index=True)
    facility_id = Column(String(64), nullable=True, index=True)
    rule_type = Column(String(32), nullable=False)  # pgx_interaction, drug_drug, order_set_gap
    trigger_event = Column(SAEnum(CDSRuleTriggerEvent), default=CDSRuleTriggerEvent.ORDER_SELECT, nullable=False)
    severity = Column(String(16), default="warning", nullable=False)  # critical, warning, info
    card_summary = Column(String(255), nullable=False)
    card_detail = Column(Text, nullable=False)
    is_overridden = Column(Boolean, default=False, nullable=False)
    override_reason = Column(Text, nullable=True)
    clinician_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
