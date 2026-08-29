"""Pydantic schemas for Clinical Risk Stratification & Scoring.

Phase 9.0.11: Clinical Cohort Analytics, Patient Registry Management & Longitudinal Risk Stratification.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class RiskType(str, Enum):
    READMISSION_30D = "readmission_30d"
    CARDIOVASCULAR_DECOMPENSATION = "cardiovascular_decompensation"
    CLINICAL_DETERIORATION = "clinical_deterioration"
    MEDICATION_ADHERENCE = "medication_adherence"
    GENERAL_MORTALITY = "general_mortality"


class RiskTier(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskFactor(BaseModel):
    factor_name: str = Field(..., description="Name of the clinical risk factor")
    category: str = Field(default="clinical", description="Category (vitals, comorbidity, medication, alert, adherence)")
    severity: str = Field(default="MODERATE", description="LOW, MODERATE, HIGH, CRITICAL")
    observed_value: Optional[str] = Field(None, description="Actual observed metric or diagnosis")
    clinical_rationale: str = Field(..., description="Explanation of why this increases patient risk")


class RiskMitigationAction(BaseModel):
    action_title: str = Field(..., description="Recommended clinical intervention")
    priority: str = Field(default="ROUTINE", description="STAT, URGENT, ROUTINE, LOW")
    suggested_task_type: Optional[str] = Field(None, description="Corresponding CareTaskType")
    target_timeline_days: int = Field(default=7, description="Recommended resolution window in days")
    rational: str = Field(..., description="Evidence or clinical basis for action")


class RiskStratifyRequest(BaseModel):
    risk_type: RiskType = Field(default=RiskType.READMISSION_30D, description="Type of clinical risk to evaluate")
    encounter_id: Optional[int] = Field(None, description="Optional associated clinical encounter ID")
    custom_context: Optional[str] = Field(None, description="Optional extra clinical observations or notes")


class RiskAssessmentCreate(BaseModel):
    risk_type: RiskType
    encounter_id: Optional[int] = None
    risk_score: float = Field(..., ge=0.0, le=100.0)
    risk_tier: RiskTier
    predicted_outcome: str
    contributing_factors: list[RiskFactor] = Field(default_factory=list)
    mitigation_recommendations: list[RiskMitigationAction] = Field(default_factory=list)


class RiskAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: str
    patient_id: int
    encounter_id: Optional[int] = None
    risk_type: RiskType
    risk_score: float
    risk_tier: RiskTier
    predicted_outcome: str
    contributing_factors_json: Optional[list[dict[str, Any]]] = None
    mitigation_recommendations_json: Optional[list[dict[str, Any]]] = None
    assessed_by_user_id: Optional[int] = None
    is_ai_generated: bool
    assessed_at: datetime
    created_at: datetime


class RiskAssessmentListResponse(BaseModel):
    items: list[RiskAssessmentResponse]
    total: int
