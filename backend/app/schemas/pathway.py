"""Pydantic schemas for Regional Clinical Pathways and Multi-Hospital Orchestration."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PathwayMilestoneCreate(BaseModel):
    name: str
    criteria_code: str
    expected_order_type: Optional[str] = None
    is_critical: bool = True


class PathwayMilestoneResponse(BaseModel):
    milestone_id: str
    stage_id: str
    name: str
    criteria_code: str
    expected_order_type: Optional[str] = None
    is_critical: bool

    model_config = ConfigDict(from_attributes=True)


class PathwayStageCreate(BaseModel):
    sequence_order: int
    name: str
    description: Optional[str] = None
    assigned_facility_id: Optional[str] = None
    target_duration_minutes: int = 180
    required_role: str = "doctor"
    clinical_criteria_json: Dict[str, Any] = Field(default_factory=dict)
    is_mandatory: bool = True
    milestones: List[PathwayMilestoneCreate] = Field(default_factory=list)


class PathwayStageResponse(BaseModel):
    stage_id: str
    pathway_id: str
    sequence_order: int
    name: str
    description: Optional[str] = None
    assigned_facility_id: Optional[str] = None
    target_duration_minutes: int
    required_role: str
    clinical_criteria_json: Dict[str, Any]
    is_mandatory: bool
    milestones: List[PathwayMilestoneResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RegionalPathwayCreate(BaseModel):
    code: str
    name: str
    category: str
    description: str
    target_duration_hours: int = 48
    stages: List[PathwayStageCreate] = Field(default_factory=list)


class RegionalPathwayResponse(BaseModel):
    pathway_id: str
    code: str
    name: str
    category: str
    description: str
    tenant_id: str
    version: int
    target_duration_hours: int
    is_active: bool
    created_at: datetime
    stages: List[PathwayStageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RegionalPathwayListResponse(BaseModel):
    total: int
    items: List[RegionalPathwayResponse]


class PathwayEnrollRequest(BaseModel):
    patient_id: str
    pathway_id: str
    assigned_care_team_user_id: Optional[int] = None


class PathwayAdvanceStageRequest(BaseModel):
    target_stage_id: Optional[str] = None
    variance_reason: Optional[str] = None


class PathwayMilestoneCompleteRequest(BaseModel):
    milestone_id: str
    notes: Optional[str] = None


class PatientPathwayEventResponse(BaseModel):
    event_id: str
    stage_id: str
    facility_id: str
    actor_user_id: int
    transition_type: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    variance_detected: bool
    variance_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PatientPathwayEnrollmentResponse(BaseModel):
    enrollment_id: str
    patient_id: str
    pathway_id: str
    facility_id: str
    current_stage_id: str
    status: str
    enrolled_at: datetime
    completed_at: Optional[datetime] = None
    assigned_care_team_user_id: Optional[int] = None
    completed_milestones: List[str]
    variance_notes: Optional[str] = None
    has_variance: bool
    updated_at: datetime
    pathway: Optional[RegionalPathwayResponse] = None
    events: List[PatientPathwayEventResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
