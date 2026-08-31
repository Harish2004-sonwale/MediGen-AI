"""Pydantic schemas for Computerized Physician Order Entry (CPOE) and Diagnostic Results.

Phase 9.0.13: Computerized Physician Order Entry (CPOE), Diagnostic Order Lifecycle & Closed-Loop Critical Result Tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class OrderCategory(str, Enum):
    LABORATORY = "laboratory"
    IMAGING = "imaging"
    MEDICATION = "medication"
    NURSING = "nursing"
    CONSULTATION = "consultation"


class OrderPriority(str, Enum):
    ROUTINE = "routine"
    URGENT = "urgent"
    STAT = "stat"


class OrderStatus(str, Enum):
    DRAFT = "draft"
    PLACED = "placed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DiagnosticResultStatus(str, Enum):
    PRELIMINARY = "preliminary"
    FINAL = "final"
    AMENDED = "amended"
    CORRECTED = "corrected"


class AbnormalFlag(str, Enum):
    NORMAL = "normal"
    ABNORMAL_LOW = "abnormal_low"
    ABNORMAL_HIGH = "abnormal_high"
    PANIC_CRITICAL = "panic_critical"


# ==============================================================================
# CLINICAL ORDER SCHEMAS
# ==============================================================================

class ClinicalOrderCreate(BaseModel):
    encounter_id: Optional[int] = Field(default=None, description="Optional associated clinical encounter ID")
    order_category: OrderCategory = Field(default=OrderCategory.LABORATORY, description="Category of clinical order")
    order_type: str = Field(..., max_length=100, description="Specific order code or name (e.g. cbc_with_diff, chest_xray_pa)")
    priority: OrderPriority = Field(default=OrderPriority.ROUTINE, description="Urgency priority")
    clinical_indication: str = Field(..., min_length=3, description="Medical rationale for order")
    specimen_source: Optional[str] = Field(default=None, max_length=100, description="Specimen source if applicable (e.g. venous blood, urine)")
    order_details: Optional[dict[str, Any]] = Field(default=None, description="Additional order configuration parameters")


class ClinicalOrderUpdate(BaseModel):
    priority: Optional[OrderPriority] = None
    status: Optional[OrderStatus] = None
    clinical_indication: Optional[str] = None
    specimen_source: Optional[str] = None
    order_details: Optional[dict[str, Any]] = None
    version: Optional[int] = Field(default=None, description="Current version of the order for optimistic locking concurrency control")


class ClinicalOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: str
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    encounter_id: Optional[int] = None
    ordering_user_id: Optional[int] = None
    ordering_user_name: Optional[str] = None
    facility_id: Optional[str] = None
    version: int = 1
    order_category: OrderCategory
    order_type: str
    priority: OrderPriority
    status: OrderStatus
    clinical_indication: str
    specimen_source: Optional[str] = None
    order_details_json: Optional[dict[str, Any]] = None
    ai_safety_flags_json: Optional[list[dict[str, Any]]] = None
    is_ai_suggested: bool
    placed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ClinicalOrderListResponse(BaseModel):
    items: list[ClinicalOrderResponse]
    total: int


# ==============================================================================
# DIAGNOSTIC RESULT SCHEMAS
# ==============================================================================

class DiagnosticResultCreate(BaseModel):
    encounter_id: Optional[int] = Field(default=None, description="Associated encounter ID")
    test_name: str = Field(..., max_length=255, description="Name of test performed")
    test_code_loinc: Optional[str] = Field(default=None, max_length=50, description="Standard LOINC code")
    status: DiagnosticResultStatus = Field(default=DiagnosticResultStatus.FINAL, description="Result verification status")
    abnormal_flag: AbnormalFlag = Field(default=AbnormalFlag.NORMAL, description="Abnormal or panic flag")
    findings_summary: str = Field(..., description="Narrative summary or interpretation")
    numeric_value: Optional[float] = Field(default=None, description="Primary numerical measurement")
    unit_of_measure: Optional[str] = Field(default=None, max_length=50, description="Measurement unit (e.g. mg/dL, ng/mL, mEq/L)")
    reference_range_low: Optional[float] = Field(default=None, description="Normal lower reference limit")
    reference_range_high: Optional[float] = Field(default=None, description="Normal upper reference limit")
    critical_threshold_low: Optional[float] = Field(default=None, description="Panic critical lower limit")
    critical_threshold_high: Optional[float] = Field(default=None, description="Panic critical upper limit")
    structured_components: Optional[list[dict[str, Any]]] = Field(default=None, description="Multi-parameter sub-components")


class DiagnosticResultUpdate(BaseModel):
    status: Optional[DiagnosticResultStatus] = None
    abnormal_flag: Optional[AbnormalFlag] = None
    findings_summary: Optional[str] = None
    numeric_value: Optional[float] = None
    structured_components: Optional[list[dict[str, Any]]] = None


class DiagnosticResultReviewRequest(BaseModel):
    review_notes: Optional[str] = Field(default=None, description="Clinician review and verification notes")


class DiagnosticResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    result_id: str
    order_id: int
    order_identifier: Optional[str] = None
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    encounter_id: Optional[int] = None
    test_name: str
    test_code_loinc: Optional[str] = None
    status: DiagnosticResultStatus
    abnormal_flag: AbnormalFlag
    findings_summary: str
    numeric_value: Optional[float] = None
    unit_of_measure: Optional[str] = None
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None
    critical_threshold_low: Optional[float] = None
    critical_threshold_high: Optional[float] = None
    structured_components_json: Optional[list[dict[str, Any]]] = None
    reviewed_by_user_id: Optional[int] = None
    reviewed_by_user_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    resulted_at: datetime
    created_at: datetime
    updated_at: datetime


class DiagnosticResultListResponse(BaseModel):
    items: list[DiagnosticResultResponse]
    total: int


# ==============================================================================
# AI ORDER BUNDLE SUGGESTION SCHEMAS
# ==============================================================================

class OrderBundleSuggestRequest(BaseModel):
    encounter_id: Optional[int] = Field(default=None, description="Encounter context")
    clinical_protocol: Optional[str] = Field(
        default=None,
        description="Optional clinical protocol name (e.g. sepsis_bundle, chest_pain_acs, dka_protocol, general_admission)",
    )
    custom_indication: Optional[str] = Field(default=None, description="Specific clinical indication")


class OrderBundleItem(BaseModel):
    order_category: OrderCategory
    order_type: str
    priority: OrderPriority
    clinical_indication: str
    specimen_source: Optional[str] = None
    order_details: Optional[dict[str, Any]] = None


class OrderBundleSuggestResponse(BaseModel):
    protocol_name: str
    clinical_rationale: str
    suggested_orders: list[OrderBundleItem]
    pre_order_safety_warnings: list[str] = Field(default_factory=list)
