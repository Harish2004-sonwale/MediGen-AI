"""Pydantic schemas for Clinical AI Agents & Autonomous Care Coordination.

Phase 9.0.17: Advanced Clinical AI Agents & Autonomous Care Coordination.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class AgentType(str, Enum):
    CLINICAL_CONTEXT = "clinical_context"
    RISK_SURVEILLANCE = "risk_surveillance"
    CARE_COORDINATION = "care_coordination"
    DIAGNOSTIC_FOLLOWUP = "diagnostic_followup"
    MEDICATION_SAFETY = "medication_safety"
    QUALITY_GAP = "quality_gap"
    RPM_TELEHEALTH = "rpm_telehealth"
    TRANSITION_DISCHARGE = "transition_discharge"
    TRIAL_GENOMICS = "trial_genomics"
    MASTER_ORCHESTRATOR = "master_orchestrator"


class AgentRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    APPROVED = "approved"
    EXECUTED = "executed"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecommendationActionClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    RECOMMENDATION = "RECOMMENDATION"
    CLINICIAN_APPROVAL_REQUIRED = "CLINICIAN_APPROVAL_REQUIRED"
    HIGH_RISK = "HIGH_RISK"


class RecommendationPriority(str, Enum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ApprovalStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


# ==============================================================================
# EVIDENCE REFERENCE SCHEMAS
# ==============================================================================

class AgentEvidenceReferenceBase(BaseModel):
    entity_type: str = Field(..., description="Target clinical entity type")
    entity_identifier: str = Field(..., description="Business ID of clinical entity (e.g. ENC-001, ALR-001)")
    title: str = Field(..., description="Summary label of evidence")
    excerpt: Optional[str] = Field(None, description="Relevant clinical excerpt or observation snippet")
    confidence_score: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Traceability confidence score")


class AgentEvidenceReferenceCreate(AgentEvidenceReferenceBase):
    pass


class AgentEvidenceReferenceResponse(AgentEvidenceReferenceBase):
    id: int
    evidence_id: str
    recommendation_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# RECOMMENDATION SCHEMAS
# ==============================================================================

class ClinicalAgentRecommendationBase(BaseModel):
    category: str = Field(..., description="Recommendation category")
    title: str = Field(..., description="Short concise recommendation headline")
    description: str = Field(..., description="Detailed clinical proposal")
    rationale: str = Field(..., description="Clinical justification and reasoning trace")
    priority: RecommendationPriority = Field(default=RecommendationPriority.MEDIUM)
    action_class: RecommendationActionClass = Field(default=RecommendationActionClass.RECOMMENDATION)
    suggested_action_type: Optional[str] = Field(None, description="Action classification (e.g. create_care_task)")
    suggested_action_payload_json: Optional[Any] = Field(None, description="Payload required if action is executed")


class ClinicalAgentRecommendationCreate(ClinicalAgentRecommendationBase):
    evidence_references: Optional[list[AgentEvidenceReferenceCreate]] = Field(default_factory=list)


class ClinicalAgentRecommendationReviewRequest(BaseModel):
    approval_status: ApprovalStatus = Field(..., description="Clinician determination: approved or rejected")
    review_notes: Optional[str] = Field(None, description="Clinician rationale and review documentation")


class ClinicalAgentRecommendationResponse(ClinicalAgentRecommendationBase):
    id: int
    recommendation_id: str
    run_id: int
    patient_id: int
    approval_status: ApprovalStatus
    reviewed_by_user_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    execution_status: Optional[str] = None
    executed_at: Optional[datetime] = None
    execution_result_json: Optional[Any] = None
    provenance_hash: str
    created_at: datetime
    updated_at: datetime
    evidence_references: list[AgentEvidenceReferenceResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# AGENT DEFINITION SCHEMAS
# ==============================================================================

class ClinicalAgentDefinitionResponse(BaseModel):
    id: int
    agent_id: str
    name: str
    agent_type: AgentType
    description: str
    version: str
    is_active: bool
    capabilities_json: Optional[Any] = None
    default_action_class: RecommendationActionClass
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClinicalAgentDefinitionListResponse(BaseModel):
    total: int
    items: list[ClinicalAgentDefinitionResponse]


# ==============================================================================
# AGENT RUN SCHEMAS
# ==============================================================================

class ClinicalAgentRunCreateRequest(BaseModel):
    patient_id: str = Field(..., description="Patient identifier or ID")
    agent_type: AgentType = Field(default=AgentType.MASTER_ORCHESTRATOR, description="Target agent to invoke")
    include_subagents: Optional[list[AgentType]] = Field(default=None, description="Optional sub-agent selection")


class ClinicalAgentRunResponse(BaseModel):
    id: int
    run_id: str
    agent_type: AgentType
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    initiated_by_user_id: Optional[int] = None
    initiated_by_name: Optional[str] = None
    status: AgentRunStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    context_hash: str
    provenance_hash: str
    overall_summary: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    recommendations_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class ClinicalAgentRunDetailResponse(ClinicalAgentRunResponse):
    input_context_snapshot_json: Optional[Any] = None
    recommendations: list[ClinicalAgentRecommendationResponse] = Field(default_factory=list)


class ClinicalAgentRunListResponse(BaseModel):
    total: int
    items: list[ClinicalAgentRunResponse]


# ==============================================================================
# CARE COORDINATION SYNTHESIS SCHEMAS
# ==============================================================================

class CareCoordinationSynthesisResponse(BaseModel):
    patient_id: str
    patient_name: str
    run_id: str
    status: AgentRunStatus
    overall_summary: str
    provenance_hash: str
    urgent_recommendations_count: int
    high_recommendations_count: int
    pending_approvals_count: int
    recommendations: list[ClinicalAgentRecommendationResponse] = Field(default_factory=list)
