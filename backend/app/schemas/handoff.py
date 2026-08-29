"""Pydantic schemas for Clinical Transitions of Care & Shift Handoffs.

Phase 9.0.12: Clinical Transitions of Care, Multi-Disciplinary Handoffs (I-PASS/SBAR) & Automated Discharge Protocol Synthesis.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class HandoffFramework(str, Enum):
    IPASS = "ipass"
    SBAR = "sbar"


class HandoffType(str, Enum):
    SHIFT_CHANGE = "shift_change"
    UNIT_TRANSFER = "unit_transfer"
    DISCHARGE_TRANSITION = "discharge_transition"
    SERVICE_CONSULTATION = "service_consultation"


class IllnessSeverity(str, Enum):
    STABLE = "stable"
    WATCHER = "watcher"
    UNSTABLE = "unstable"


class HandoffStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class HandoffActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(..., description="Unique action item identifier (e.g. ACT-01)")
    task_description: str = Field(..., min_length=2, description="Clinical task or order to follow up")
    role_required: str = Field(default="resident_or_attending", description="Responsible clinician role")
    priority: str = Field(default="ROUTINE", description="Priority: ROUTINE, URGENT, STAT")
    is_completed: bool = Field(default=False, description="Completion status flag")


class ContingencyPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(..., description="Unique contingency rule ID (e.g. CTG-01)")
    trigger_condition: str = Field(..., description="Condition trigger, e.g. If SBP > 180 or SpO2 < 90%")
    immediate_action: str = Field(..., description="Immediate clinical protocol to execute")
    escalation_contact: str = Field(default="Attending Physician", description="Escalation contact or service")


class HandoffCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    framework: HandoffFramework = Field(default=HandoffFramework.IPASS, description="Handoff methodology framework")
    handoff_type: HandoffType = Field(default=HandoffType.SHIFT_CHANGE, description="Clinical context of transition")
    illness_severity: IllnessSeverity = Field(default=IllnessSeverity.STABLE, description="I-PASS Illness Severity classification")
    receiver_user_id: Optional[int] = Field(default=None, description="Receiving clinician user ID")
    encounter_id: Optional[int] = Field(default=None, description="Associated clinical encounter ID")
    summary: str = Field(..., min_length=5, description="Patient summary or Situation/Background narrative")
    action_items: list[HandoffActionItem] = Field(default_factory=list, description="Pending clinical action items")
    situational_awareness: list[ContingencyPlan] = Field(default_factory=list, description="If/Then contingency guidelines")
    custom_instructions: Optional[str] = Field(default=None, description="Custom handover guidance or notes")


class HandoffSynthesizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    framework: HandoffFramework = Field(default=HandoffFramework.IPASS)
    handoff_type: HandoffType = Field(default=HandoffType.SHIFT_CHANGE)
    receiver_user_id: Optional[int] = None
    encounter_id: Optional[int] = None
    custom_context: Optional[str] = None


class HandoffUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    illness_severity: Optional[IllnessSeverity] = None
    summary: Optional[str] = None
    action_items: Optional[list[HandoffActionItem]] = None
    situational_awareness: Optional[list[ContingencyPlan]] = None
    receiver_user_id: Optional[int] = None
    status: Optional[HandoffStatus] = None


class HandoffAcknowledge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    synthesis_notes: str = Field(..., min_length=3, description="Receiver synthesis and read-back notes")


class HandoffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    handoff_id: str
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    encounter_id: Optional[int] = None
    sender_user_id: Optional[int] = None
    sender_name: Optional[str] = None
    receiver_user_id: Optional[int] = None
    receiver_name: Optional[str] = None
    framework: HandoffFramework
    handoff_type: HandoffType
    illness_severity: IllnessSeverity
    status: HandoffStatus
    summary: str
    action_items_json: Optional[list[dict[str, Any]]] = None
    situational_awareness_json: Optional[list[dict[str, Any]]] = None
    synthesis_notes: Optional[str] = None
    is_ai_generated: bool
    acknowledged_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class HandoffListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[HandoffResponse]
    total: number if False else int
