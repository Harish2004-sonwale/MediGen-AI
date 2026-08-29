"""Pydantic schemas for Clinical Follow-Up Tasks & Actionable Workflows.

Phase 9.0.10: Advanced Clinical Workflow Orchestration, Care Plans & Follow-Up Management.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TaskPriority(str, Enum):
    """Clinical priority tiers."""

    LOW = "LOW"
    ROUTINE = "ROUTINE"
    URGENT = "URGENT"
    STAT = "STAT"


class CareTaskStatus(str, Enum):
    """Clinical task workflow lifecycle status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CareTaskType(str, Enum):
    """Clinical task categories."""

    FOLLOWUP_APPOINTMENT = "followup_appointment"
    LAB_TEST_ORDER = "lab_test_order"
    DIAGNOSTIC_IMAGING_ORDER = "diagnostic_imaging_order"
    PATIENT_EDUCATION = "patient_education"
    MEDICATION_RECONCILIATION = "medication_reconciliation"
    TELEMETRY_CHECK = "telemetry_check"
    GENERAL_TASK = "general_task"


class CareTaskCreate(BaseModel):
    """Payload to create a new clinical follow-up task."""

    title: str = Field(..., min_length=3, max_length=255, description="Task title")
    task_type: CareTaskType = Field(default=CareTaskType.GENERAL_TASK)
    priority: TaskPriority = Field(default=TaskPriority.ROUTINE)
    instructions: Optional[str] = Field(default=None, description="Detailed clinical instructions")
    due_date: datetime = Field(..., description="Task deadline")
    assigned_user_id: Optional[int] = Field(default=None, description="Assigned clinician or staff ID")
    care_plan_id: Optional[int] = Field(default=None, description="Associated care plan ID")
    encounter_id: Optional[int] = Field(default=None, description="Associated encounter ID")
    appointment_id: Optional[int] = Field(default=None, description="Associated appointment ID")


class CareTaskUpdate(BaseModel):
    """Payload to update an existing clinical task."""

    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    task_type: Optional[CareTaskType] = None
    priority: Optional[TaskPriority] = None
    instructions: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_user_id: Optional[int] = None
    status: Optional[CareTaskStatus] = None


class CareTaskCompleteRequest(BaseModel):
    """Payload to mark a clinical task as completed."""

    completion_notes: Optional[str] = Field(
        default=None,
        description="Clinician or staff notes detailing task execution outcome",
    )


class CareTaskResponse(BaseModel):
    """Full representation of a clinical follow-up task."""

    id: int
    task_id: str
    patient_id: int
    care_plan_id: Optional[int]
    encounter_id: Optional[int]
    appointment_id: Optional[int]
    assigned_user_id: Optional[int]
    title: str
    task_type: CareTaskType
    priority: TaskPriority
    status: CareTaskStatus
    instructions: Optional[str]
    due_date: datetime
    is_overdue: bool
    completed_at: Optional[datetime]
    completion_notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CareTaskListResponse(BaseModel):
    """List envelope for clinical tasks."""

    items: list[CareTaskResponse]
    total: int
