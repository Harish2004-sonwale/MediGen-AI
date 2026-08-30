"""Schemas for Background Asynchronous Task Worker Architecture.

Phase 9.0.3: Background Asynchronous Worker Architecture.
Provides structured schemas and models for:
- Task statuses (QUEUED, RUNNING, COMPLETED, FAILED, RETRYING, CANCELLED)
- Task types (DOCUMENT_PROCESSING, TIMELINE_SUMMARY, SAFETY_CHECK, BATCH_INDEXING)
- BackgroundTask domain and response models
- Filter and query parameter models
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class BackgroundTaskStatus(str, Enum):
    """Execution status lifecycle of a background task."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class BackgroundTaskType(str, Enum):
    """Categories of background tasks supported by MediGen AI."""

    DOCUMENT_PROCESSING = "document_processing"
    TIMELINE_SUMMARY = "timeline_summary"
    SAFETY_CHECK = "safety_check"
    BATCH_INDEXING = "batch_indexing"
    MEDIA_ANALYSIS = "media_analysis"
    NOTE_SYNTHESIS = "note_synthesis"
    TELEMETRY_EVALUATION = "telemetry_evaluation"
    CARE_PLAN_GENERATION = "care_plan_generation"
    COHORT_ANALYSIS = "cohort_analysis"
    RISK_STRATIFICATION = "risk_stratification"
    HANDOFF_SYNTHESIS = "handoff_synthesis"
    DISCHARGE_SYNTHESIS = "discharge_synthesis"
    ORDER_VERIFICATION = "order_verification"
    RESULT_INGESTION = "result_ingestion"
    QUALITY_MEASURE_CALCULATION = "quality_measure_calculation"
    QUALITY_GAP_ANALYSIS = "quality_gap_analysis"
    QUALITY_REPORT_GENERATION = "quality_report_generation"
    RPM_OBSERVATION_PROCESSING = "rpm_observation_processing"
    RPM_THRESHOLD_EVALUATION = "rpm_threshold_evaluation"
    RPM_ESCALATION_PROCESSING = "rpm_escalation_processing"
    PROM_SCORING = "prom_scoring"
    TELEHEALTH_REMINDER = "telehealth_reminder"
    TRIAL_MATCHING = "trial_matching"
    GENOMIC_ANALYSIS = "genomic_analysis"
    PRECISION_ELIGIBILITY = "precision_eligibility"
    CLINICAL_AGENT_RUN = "clinical_agent_run"
    CARE_COORDINATION_SYNTHESIS = "care_coordination_synthesis"
    IMAGING_ANALYSIS = "imaging_analysis"
    RADIOLOGY_REPORT_SYNTHESIS = "radiology_report_synthesis"
    CRITICAL_FINDING_ESCALATION = "critical_finding_escalation"
    AUDIT_LOG_INTEGRITY_CHECK = "audit_log_integrity_check"
    SECURITY_ANOMALY_SCAN = "security_anomaly_scan"
    DATA_RETENTION_EVALUATION = "data_retention_evaluation"
    COMPLIANCE_REPORT_GENERATION = "compliance_report_generation"









class BackgroundTask(BaseModel):

    """Core domain model representing an asynchronous background task."""

    task_id: str = Field(..., description="Unique public task identifier (e.g. TASK-20260829-A1B2C3D4)")
    task_type: BackgroundTaskType = Field(..., description="Classification of the background workload")
    status: BackgroundTaskStatus = Field(default=BackgroundTaskStatus.QUEUED, description="Current execution status")
    patient_id: Optional[str] = Field(default=None, description="Patient identifier context for patient isolation")
    created_by_user_id: Optional[int] = Field(default=None, description="User ID who enqueued the task")
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Task completion progress from 0.0 to 1.0")
    result_metadata: dict[str, Any] = Field(default_factory=dict, description="Structured execution result or statistics")
    error_message: Optional[str] = Field(default=None, description="Sanitized failure description if status is FAILED")
    retry_count: int = Field(default=0, ge=0, description="Number of times task has been retried")
    max_retries: int = Field(default=3, ge=0, description="Maximum permitted retry attempts")
    payload: dict[str, Any] = Field(default_factory=dict, description="Internal task input parameters (sanitized, no raw PHI)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Task submission timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Timestamp when worker began execution")
    completed_at: Optional[datetime] = Field(default=None, description="Timestamp when task reached terminal state")

    model_config = ConfigDict(from_attributes=True)


class BackgroundTaskResponse(BaseModel):
    """Public API response schema for a background task."""

    task_id: str = Field(..., description="Unique public task identifier")
    task_type: BackgroundTaskType = Field(..., description="Classification of the background workload")
    status: BackgroundTaskStatus = Field(..., description="Current execution status")
    patient_id: Optional[str] = Field(default=None, description="Associated patient identifier")
    progress: float = Field(..., description="Progress ratio between 0.0 and 1.0")
    result_metadata: dict[str, Any] = Field(default_factory=dict, description="Structured execution results")
    error_message: Optional[str] = Field(default=None, description="Sanitized failure details")
    retry_count: int = Field(..., description="Current retry attempt count")
    max_retries: int = Field(..., description="Maximum retries permitted")
    created_at: datetime = Field(..., description="Task submission timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Task execution start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Task completion timestamp")

    model_config = ConfigDict(from_attributes=True)


class TaskListResponse(BaseModel):
    """Paginated collection of background tasks."""

    items: list[BackgroundTaskResponse] = Field(..., description="List of background tasks")
    total: int = Field(..., description="Total count matching filter criteria")
    page: int = Field(..., ge=1, description="Current page number")
    size: int = Field(..., ge=1, description="Page size")

    @classmethod
    def create(cls, items: list[BackgroundTaskResponse], total: int, page: int, size: int) -> "TaskListResponse":
        return cls(items=items, total=total, page=page, size=size)


class DocumentTaskRequest(BaseModel):
    """Request payload to trigger asynchronous document processing."""

    priority: Optional[str] = Field(default="normal", description="Task priority (low, normal, high)")


class TimelineTaskRequest(BaseModel):
    """Request payload to trigger asynchronous clinical timeline summary compilation."""

    focus: Optional[str] = Field(default=None, description="Optional clinical focus area (e.g. 'cardiology', 'medications')")
