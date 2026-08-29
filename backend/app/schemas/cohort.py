"""Pydantic schemas for Patient Cohorts, Disease Registries & Population Health.

Phase 9.0.11: Clinical Cohort Analytics, Patient Registry Management & Longitudinal Risk Stratification.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class CohortType(str, Enum):
    DISEASE_REGISTRY = "disease_registry"
    RISK_WATCH_LIST = "risk_watch_list"
    POST_OP_MONITORING = "post_op_monitoring"
    QUALITY_MEASURE = "quality_measure"
    CUSTOM_COHORT = "custom_cohort"


class CohortCriteria(BaseModel):
    min_age: Optional[int] = Field(None, ge=0, le=130, description="Minimum patient age")
    max_age: Optional[int] = Field(None, ge=0, le=130, description="Maximum patient age")
    gender: Optional[str] = Field(None, description="Gender filter (male, female, other)")
    conditions: list[str] = Field(default_factory=list, description="List of condition keywords or ICD terms")
    medications: list[str] = Field(default_factory=list, description="List of medication keywords")
    min_systolic_bp: Optional[int] = Field(None, description="Minimum systolic BP threshold")
    max_systolic_bp: Optional[int] = Field(None, description="Maximum systolic BP threshold")
    min_spo2: Optional[float] = Field(None, description="Minimum SpO2 threshold")
    min_risk_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Minimum risk score threshold")
    risk_tier: Optional[str] = Field(None, description="Target risk tier (LOW, MODERATE, HIGH, CRITICAL)")
    active_alerts_only: bool = Field(False, description="Require active CDS alerts")


class CohortCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Cohort or Disease Registry title")
    description: str = Field(..., min_length=5, description="Clinical objective and cohort description")
    cohort_type: CohortType = Field(default=CohortType.DISEASE_REGISTRY, description="Type of patient cohort")
    criteria: Optional[CohortCriteria] = Field(default=None, description="Automated inclusion rules")
    is_dynamic: bool = Field(default=True, description="Whether membership is automatically re-evaluated")


class CohortUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, min_length=5)
    cohort_type: Optional[CohortType] = None
    criteria: Optional[CohortCriteria] = None
    is_dynamic: Optional[bool] = None


class CohortMembershipCreate(BaseModel):
    patient_id: str = Field(..., description="Target patient identifier (e.g. PAT-001 or integer ID)")
    notes: Optional[str] = Field(None, max_length=500, description="Clinical reason for enrollment")


class CohortMembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cohort_id: int
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    enrolled_at: datetime
    status: str
    notes: Optional[str] = None
    latest_risk_score: Optional[float] = None
    latest_risk_tier: Optional[str] = None


class CohortResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cohort_id: str
    name: str
    description: str
    cohort_type: CohortType
    criteria_json: Optional[dict[str, Any]] = None
    is_dynamic: bool
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    member_count: int = 0


class CohortListResponse(BaseModel):
    items: list[CohortResponse]
    total: int


class CohortAnalyticsResponse(BaseModel):
    cohort_id: str
    name: str
    cohort_type: str
    total_members: int
    risk_tier_distribution: dict[str, int]
    mean_risk_score: float
    high_risk_patient_count: int
    active_alerts_count: int
    active_care_plans_count: int
    overdue_tasks_count: int
    generated_at: datetime
