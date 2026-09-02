# ==============================================================================
# MediGen AI - Phase 9.0.26: Enterprise CDS Rules, PGx & Order Sets Schemas
# ==============================================================================

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

from app.models.cds_pgx import (
    CPICLevel,
    PGxRiskSeverity,
    OrderSetCategory,
    OrderSetItemType,
    OrderSetExecutionStatus,
    CDSRuleTriggerEvent,
)


# --- PGx Rule Schemas ---

class PGxRuleBase(BaseModel):
    rule_id: str
    cpic_level: CPICLevel
    gene_symbol: str
    phenotype: str
    drug_code: str
    drug_name: str
    risk_severity: PGxRiskSeverity
    clinical_implication: str
    recommendation_text: str
    alternative_drugs: List[str] = Field(default_factory=list)
    evidence_source: str = "CPIC Guidelines v2024"
    is_active: bool = True


class PGxRuleCreate(PGxRuleBase):
    pass


class PGxRuleResponse(PGxRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PGxRuleListResponse(BaseModel):
    total: int
    rules: List[PGxRuleResponse]


# --- Clinical Order Set Schemas ---

class OrderSetItemBase(BaseModel):
    item_id: str
    item_type: OrderSetItemType
    code: str
    name: str
    default_dosage: Optional[str] = None
    default_route: Optional[str] = None
    default_frequency: Optional[str] = None
    clinical_instructions: Optional[str] = None
    is_required: bool = True
    sequence_order: int = 1


class OrderSetItemCreate(OrderSetItemBase):
    pass


class OrderSetItemResponse(OrderSetItemBase):
    id: int
    order_set_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderSetBase(BaseModel):
    order_set_id: str
    code: str
    title: str
    description: Optional[str] = None
    category: OrderSetCategory
    target_icd10: Optional[str] = None
    facility_id: Optional[str] = None
    version: str = "1.0.0"
    is_active: bool = True


class OrderSetCreate(OrderSetBase):
    items: List[OrderSetItemCreate] = Field(default_factory=list)


class OrderSetResponse(OrderSetBase):
    id: int
    created_at: datetime
    updated_at: datetime
    items: List[OrderSetItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class OrderSetListResponse(BaseModel):
    total: int
    order_sets: List[OrderSetResponse]


class OrderSetExecuteRequest(BaseModel):
    patient_id: str
    selected_item_ids: Optional[List[str]] = None  # If None, execute all required items
    custom_instructions: Optional[str] = None
    notes: Optional[str] = None


class OrderSetExecuteResponse(BaseModel):
    execution_id: str
    order_set_id: str
    patient_id: str
    facility_id: str
    status: OrderSetExecutionStatus
    executed_items_count: int
    generated_order_ids: List[str]
    message: str
    created_at: datetime


# --- Real-Time CDS & PGx Evaluation Schemas ---

class CDSEvaluationRequest(BaseModel):
    patient_id: str
    trigger_event: CDSRuleTriggerEvent = CDSRuleTriggerEvent.ORDER_SELECT
    proposed_drug_code: Optional[str] = None  # RxNorm or drug name
    proposed_drug_name: Optional[str] = None
    proposed_dosage: Optional[str] = None
    context_encounter_id: Optional[str] = None


class CDSCardSuggestion(BaseModel):
    label: str
    uuid: Optional[str] = None
    actions: List[Dict[str, Any]] = Field(default_factory=list)


class CDSEvaluationCard(BaseModel):
    summary: str
    detail: str
    indicator: str = "warning"  # info, warning, critical
    source_label: str
    source_url: Optional[str] = None
    rule_type: str  # pgx_interaction, drug_drug, order_set_suggestion, dosing_warning
    severity: PGxRiskSeverity
    gene_symbol: Optional[str] = None
    phenotype: Optional[str] = None
    drug_name: Optional[str] = None
    alternative_drugs: List[str] = Field(default_factory=list)
    suggestions: List[CDSCardSuggestion] = Field(default_factory=list)


class CDSEvaluationResponse(BaseModel):
    patient_id: str
    has_alerts: bool
    cards: List[CDSEvaluationCard] = Field(default_factory=list)
    active_biomarkers: Dict[str, str] = Field(default_factory=dict)  # gene -> phenotype


class CDSRuleOverrideRequest(BaseModel):
    patient_id: str
    rule_type: str
    trigger_event: CDSRuleTriggerEvent = CDSRuleTriggerEvent.ORDER_SELECT
    severity: str = "warning"
    card_summary: str
    card_detail: str
    override_reason: str


class CDSRuleOverrideResponse(BaseModel):
    audit_id: str
    patient_id: str
    is_overridden: bool
    override_reason: str
    message: str
    created_at: datetime
