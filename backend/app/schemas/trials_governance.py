"""Pydantic v2 schemas for Clinical Trial Governance, Protocol Deviations, CAPA & Multi-Center Regulatory Auditing."""

from datetime import date, datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.trials_governance import (
    CAPARootCause,
    CAPAStatus,
    DeviationCategory,
    DeviationSeverity,
    DeviationStatus,
    IRBSubmissionType,
    StudySiteStatus,
)


# ==============================================================================
# Multi-Center Study Site Schemas
# ==============================================================================

class StudySiteCreate(BaseModel):
    trial_id: int
    facility_id: Optional[str] = None
    principal_investigator_user_id: Optional[int] = None
    site_name: str = Field(..., min_length=2, max_length=255)
    target_accrual: int = Field(default=20, ge=1)
    irb_approval_number: Optional[str] = None
    irb_approval_date: Optional[date] = None
    irb_expiry_date: Optional[date] = None


class StudySiteResponse(BaseModel):
    id: int
    site_id: str
    trial_id: int
    facility_id: Optional[str] = None
    principal_investigator_user_id: Optional[int] = None
    site_name: str
    target_accrual: int
    current_enrolled: int
    site_status: StudySiteStatus
    irb_approval_number: Optional[str] = None
    irb_approval_date: Optional[date] = None
    irb_expiry_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudySiteListResponse(BaseModel):
    total: int
    sites: List[StudySiteResponse]


# ==============================================================================
# Protocol Deviation & Regulatory Governance Schemas
# ==============================================================================

class ProtocolDeviationCreate(BaseModel):
    trial_id: int
    site_id: Optional[int] = None
    patient_id: Optional[str] = None  # Patient string identifier
    deviation_category: DeviationCategory
    severity: DeviationSeverity = DeviationSeverity.MINOR
    description: str = Field(..., min_length=10)
    occurred_at: datetime
    discovered_at: datetime
    impact_on_patient_safety: Optional[str] = None
    impact_on_data_integrity: Optional[str] = None
    requires_irb_submission: bool = False


class ProtocolDeviationUpdate(BaseModel):
    status: Optional[DeviationStatus] = None
    impact_on_patient_safety: Optional[str] = None
    impact_on_data_integrity: Optional[str] = None
    requires_irb_submission: Optional[bool] = None
    irb_submitted_at: Optional[datetime] = None


class ProtocolDeviationResponse(BaseModel):
    id: int
    deviation_id: str
    trial_id: int
    site_id: Optional[int] = None
    patient_id: Optional[int] = None
    reported_by_user_id: int
    deviation_category: DeviationCategory
    severity: DeviationSeverity
    status: DeviationStatus
    description: str
    occurred_at: datetime
    discovered_at: datetime
    impact_on_patient_safety: Optional[str] = None
    impact_on_data_integrity: Optional[str] = None
    requires_irb_submission: bool
    irb_submitted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProtocolDeviationListResponse(BaseModel):
    total: int
    deviations: List[ProtocolDeviationResponse]


# ==============================================================================
# CAPA (Corrective and Preventive Action) Schemas
# ==============================================================================

class CAPACreateRequest(BaseModel):
    deviation_id: int
    root_cause_category: CAPARootCause = CAPARootCause.INVESTIGATOR_OVERSIGHT
    root_cause_analysis: str = Field(..., min_length=10)
    corrective_action: str = Field(..., min_length=10)
    preventive_action: str = Field(..., min_length=10)
    assigned_owner_user_id: int
    target_resolution_date: date


class CAPAUpdateRequest(BaseModel):
    status: Optional[CAPAStatus] = None
    actual_resolution_date: Optional[date] = None
    effectiveness_check_notes: Optional[str] = None


class CAPAResponse(BaseModel):
    id: int
    capa_id: str
    deviation_id: int
    root_cause_category: CAPARootCause
    root_cause_analysis: str
    corrective_action: str
    preventive_action: str
    assigned_owner_user_id: int
    target_resolution_date: date
    actual_resolution_date: Optional[date] = None
    status: CAPAStatus
    effectiveness_check_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CAPAListResponse(BaseModel):
    total: int
    capas: List[CAPAResponse]


# ==============================================================================
# IRB Safety Notification Schemas
# ==============================================================================

class IRBNotificationCreateRequest(BaseModel):
    deviation_id: int
    irb_committee_name: str = Field(..., min_length=3, max_length=150)
    submission_type: IRBSubmissionType = IRBSubmissionType.INITIAL_DEVIATION_REPORT
    custom_remarks: Optional[str] = None


class IRBNotificationResponse(BaseModel):
    id: int
    notification_id: str
    deviation_id: int
    irb_committee_name: str
    submission_type: IRBSubmissionType
    document_content_json: dict[str, Any]
    submitted_by_user_id: int
    submission_timestamp: datetime
    acknowledgement_reference: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IRBNotificationListResponse(BaseModel):
    total: int
    notifications: List[IRBNotificationResponse]


# ==============================================================================
# Auto-Prescreening & Multi-Center Summary Schemas
# ==============================================================================

class TrialPrescreenMatchCriterionResult(BaseModel):
    criterion_id: str
    category: str
    criterion_type: str
    description: str
    is_met: bool
    patient_value: Optional[str] = None
    required: bool


class TrialPrescreenEvaluationItem(BaseModel):
    trial_id: int
    nct_number: Optional[str] = None
    title: str
    phase: str
    disease_condition: str
    eligibility_score: float  # 0.0 - 100.0%
    is_eligible: bool
    matched_criteria_count: int
    total_criteria_count: int
    disqualifying_reasons: List[str]
    criteria_results: List[TrialPrescreenMatchCriterionResult]


class TrialPrescreenEvaluationResponse(BaseModel):
    patient_id: str
    evaluated_at: datetime
    total_trials_screened: int
    eligible_trials_count: int
    evaluations: List[TrialPrescreenEvaluationItem]


class SiteAccrualMetric(BaseModel):
    site_id: str
    site_name: str
    facility_id: Optional[str] = None
    target_accrual: int
    current_enrolled: int
    accrual_percentage: float
    open_deviations_count: int
    critical_deviations_count: int
    status: StudySiteStatus


class MultiCenterTrialGovernanceSummary(BaseModel):
    trial_id: int
    trial_title: str
    total_target_accrual: int
    total_enrolled: int
    overall_accrual_rate: float
    active_sites_count: int
    total_deviations_count: int
    open_capas_count: int
    sites_metrics: List[SiteAccrualMetric]
