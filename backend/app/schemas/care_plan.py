"""Pydantic schemas for Structured Clinical Care Plans & Goals.

Phase 9.0.10: Advanced Clinical Workflow Orchestration, Care Plans & Follow-Up Management.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class CarePlanStatus(str, Enum):
    """Clinical care plan lifecycle status."""

    DRAFT = "draft"
    REVIEWED = "reviewed"
    ACTIVE = "active"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"


class CarePlanCategory(str, Enum):
    """Clinical care plan domain classifications."""

    CHRONIC_DISEASE_MANAGEMENT = "chronic_disease_management"
    POST_DISCHARGE_FOLLOWUP = "post_discharge_followup"
    PREVENTIVE_CARE = "preventive_care"
    REHABILITATION = "rehabilitation"
    ACUTE_CARE_PLAN = "acute_care_plan"


class CarePlanGoal(BaseModel):
    """Structured clinical health target within a care plan."""

    goal_id: str = Field(..., description="Unique goal identifier (e.g. G-01)")
    title: str = Field(..., description="Description of the clinical goal")
    target_metric: Optional[str] = Field(default=None, description="Quantitative target (e.g. SBP < 130 mmHg)")
    target_date: Optional[datetime] = Field(default=None, description="Anticipated goal completion target date")
    status: str = Field(default="in_progress", description="Goal status (in_progress, achieved, cancelled)")
    notes: Optional[str] = Field(default=None, description="Progress notes or clinical context")


class CarePlanIntervention(BaseModel):
    """Structured clinical intervention or activity in a care plan."""

    intervention_id: str = Field(..., description="Unique intervention identifier (e.g. INT-01)")
    description: str = Field(..., description="Details of the intervention or clinical activity")
    category: str = Field(default="medical", description="Category (medical, lifestyle, monitoring, education)")
    responsible_party: Optional[str] = Field(default="clinician", description="Responsible party or care team role")
    status: str = Field(default="active", description="Intervention status (active, completed, discontinued)")


class CarePlanCreate(BaseModel):
    """Payload to create a new clinical care plan."""

    title: str = Field(..., min_length=3, max_length=255, description="Care plan title")
    category: CarePlanCategory = Field(default=CarePlanCategory.CHRONIC_DISEASE_MANAGEMENT)
    description: str = Field(..., min_length=5, description="Clinical summary and objectives")
    intent: str = Field(default="plan", max_length=30, description="FHIR intent (proposal, plan, order)")
    encounter_id: Optional[int] = Field(default=None, description="Associated encounter ID")
    goals: list[CarePlanGoal] = Field(default_factory=list, description="Clinical health goals")
    interventions: list[CarePlanIntervention] = Field(default_factory=list, description="Planned interventions")
    start_date: Optional[datetime] = Field(default=None, description="Effective start timestamp")
    end_date: Optional[datetime] = Field(default=None, description="Target completion timestamp")


class CarePlanUpdate(BaseModel):
    """Payload to update an editable draft or reviewed care plan."""

    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    category: Optional[CarePlanCategory] = None
    description: Optional[str] = Field(default=None, min_length=5)
    intent: Optional[str] = None
    goals: Optional[list[CarePlanGoal]] = None
    interventions: Optional[list[CarePlanIntervention]] = None
    end_date: Optional[datetime] = None


class CarePlanReviewRequest(BaseModel):
    """Physician review and signoff payload."""

    confirm_accuracy: bool = Field(..., description="Explicit clinician confirmation of clinical accuracy")
    clinician_notes: Optional[str] = Field(default=None, description="Optional signoff notes or clinical directives")
    activate_immediately: bool = Field(default=True, description="Whether to transition directly to active status")


class CarePlanSynthesizeRequest(BaseModel):
    """Payload to trigger AI-assisted Care Plan draft synthesis."""

    category: CarePlanCategory = Field(default=CarePlanCategory.CHRONIC_DISEASE_MANAGEMENT)
    custom_instructions: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional focus areas (e.g. 'Focus on post-MI cardiac rehab and blood pressure')",
    )


class CarePlanResponse(BaseModel):
    """Full representation of a clinical care plan."""

    id: int
    plan_id: str
    patient_id: int
    author_user_id: Optional[int]
    encounter_id: Optional[int]
    title: str
    category: CarePlanCategory
    status: CarePlanStatus
    intent: str
    description: str
    goals_json: Optional[list[dict[str, Any]]]
    interventions_json: Optional[list[dict[str, Any]]]
    is_ai_generated: bool
    reviewed_by_user_id: Optional[int]
    reviewed_at: Optional[datetime]
    start_date: datetime
    end_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CarePlanListResponse(BaseModel):
    """List envelope for clinical care plans."""

    items: list[CarePlanResponse]
    total: int
