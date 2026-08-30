"""Pydantic schemas for Remote Patient Monitoring (RPM), PROMs & Telehealth.

Phase 9.0.15: Remote Patient Monitoring (RPM), Patient-Reported Outcomes (PROMs) & Telehealth Protocols.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


# ==============================================================================
# ENUMS
# ==============================================================================

class ObservationClassification(str, Enum):
    NORMAL = "normal"
    ABNORMAL = "abnormal"
    CRITICAL = "critical"


class DeviceType(str, Enum):
    BLOOD_PRESSURE_CUFF = "blood_pressure_cuff"
    PULSE_OXIMETER = "pulse_oximeter"
    GLUCOMETER = "glucometer"
    SMART_SCALE = "smart_scale"
    WEARABLE_SENSOR = "wearable_sensor"
    THERMOMETER = "thermometer"


class DeviceStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    REVOKED = "revoked"


class ProgramStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    DISCHARGED = "discharged"


class EscalationSeverity(str, Enum):
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EscalationStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class PROMDomain(str, Enum):
    MENTAL_HEALTH = "mental_health"
    FUNCTIONAL_STATUS = "functional_status"
    SYMPTOM_BURDEN = "symptom_burden"
    QUALITY_OF_LIFE = "quality_of_life"


class TelehealthStatus(str, Enum):
    SCHEDULED = "scheduled"
    WAITING_ROOM = "waiting_room"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


# ==============================================================================
# RPM PROGRAM SCHEMAS
# ==============================================================================

class RPMProgramEnrollRequest(BaseModel):
    patient_id: str
    condition_name: str = Field(..., description="Target clinical condition e.g. Hypertension, CHF, Diabetes")
    program_name: str = Field(..., description="Protocol program title")
    target_cadence_days: int = Field(1, description="Expected measurement interval in days")
    clinical_goals: Optional[list[str]] = None


class RPMProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    program_id: str
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    enrolled_by_user_id: Optional[int] = None
    condition_name: str
    program_name: str
    status: str
    target_cadence_days: int
    clinical_goals_json: Optional[list[str]] = None
    discharged_at: Optional[datetime] = None
    discharge_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RPMProgramListResponse(BaseModel):
    items: list[RPMProgramResponse]
    total: int


# ==============================================================================
# RPM DEVICE SCHEMAS
# ==============================================================================

class RPMDeviceCreate(BaseModel):
    device_id: Optional[str] = None
    patient_id: Optional[str] = None
    device_type: DeviceType
    manufacturer: str
    model_number: str
    serial_number: str
    supported_measurements: Optional[list[str]] = None


class RPMDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    patient_id: Optional[int] = None
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    device_type: str
    manufacturer: str
    model_number: str
    serial_number: str
    status: str
    supported_measurements_json: Optional[list[str]] = None
    last_sync_at: Optional[datetime] = None
    created_at: datetime


class RPMDeviceListResponse(BaseModel):
    items: list[RPMDeviceResponse]
    total: int


# ==============================================================================
# RPM OBSERVATION SCHEMAS
# ==============================================================================

class RPMObservationCreate(BaseModel):
    patient_id: str
    device_id: Optional[str] = None
    observation_type: str = Field(..., description="e.g. systolic_bp, diastolic_bp, heart_rate, spo2_percent, glucose_mgdl, weight_kg, temperature_c")
    numeric_value: float
    secondary_value: Optional[float] = Field(None, description="e.g. diastolic value if primary is systolic")
    unit_of_measure: str = Field(..., description="e.g. mmHg, bpm, %, mg/dL, kg, C")
    source_type: str = "bluetooth_sync"
    measured_at: Optional[datetime] = None
    raw_payload: Optional[dict[str, Any]] = None


class RPMObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    observation_id: str
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    device_id: Optional[int] = None
    device_identifier: Optional[str] = None
    observation_type: str
    numeric_value: float
    secondary_value: Optional[float] = None
    unit_of_measure: str
    classification: str
    source_type: str
    measured_at: datetime
    ingested_at: datetime
    is_acknowledged: bool
    raw_payload_json: Optional[dict[str, Any]] = None


class RPMObservationListResponse(BaseModel):
    items: list[RPMObservationResponse]
    total: int


class RPMTelemetrySummary(BaseModel):
    patient_id: str
    patient_name: str
    active_program_name: Optional[str] = None
    total_observations_count: int
    recent_readings: list[RPMObservationResponse]
    critical_alerts_count: int
    average_systolic_bp: Optional[float] = None
    average_diastolic_bp: Optional[float] = None
    average_heart_rate: Optional[float] = None
    average_spo2: Optional[float] = None
    average_glucose: Optional[float] = None


# ==============================================================================
# RPM THRESHOLD & ESCALATION SCHEMAS
# ==============================================================================

class RPMThresholdRuleCreate(BaseModel):
    patient_id: Optional[str] = None
    observation_type: str
    normal_min: Optional[float] = None
    normal_max: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    consecutive_readings_trigger: int = 2


class RPMThresholdRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rule_id: str
    patient_id: Optional[int] = None
    observation_type: str
    normal_min: Optional[float] = None
    normal_max: Optional[float] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    consecutive_readings_trigger: int
    is_active: bool
    created_at: datetime


class RPMEscalationAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_id: str
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    observation_id: Optional[int] = None
    observation_identifier: Optional[str] = None
    severity: str
    status: str
    escalation_reason: str
    clinical_action_taken: Optional[str] = None
    linked_care_task_id: Optional[int] = None
    acknowledged_by_user_id: Optional[int] = None
    resolved_by_user_id: Optional[int] = None
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


class RPMEscalationAlertListResponse(BaseModel):
    items: list[RPMEscalationAlertResponse]
    total: int


class RPMEscalationAcknowledgeRequest(BaseModel):
    notes: Optional[str] = None


class RPMEscalationResolveRequest(BaseModel):
    clinical_action_taken: str
    create_care_task: bool = True


# ==============================================================================
# PATIENT-REPORTED OUTCOMES (PROMS) SCHEMAS
# ==============================================================================

class PROMQuestion(BaseModel):
    id: str
    prompt: str
    options: list[dict[str, Any]] = Field(..., description="Array of {label: str, score: float}")


class PROMDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prom_id: str
    title: str
    domain: str
    version: str
    questions_json: list[dict[str, Any]]
    scoring_method: str
    interpretation_ranges_json: list[dict[str, Any]]
    is_active: bool
    created_at: datetime


class PROMDefinitionListResponse(BaseModel):
    items: list[PROMDefinitionResponse]
    total: int


class PROMResponseSubmitRequest(BaseModel):
    prom_id: str = Field(..., description="e.g. PROM-PHQ9, PROM-GAD7, PROM-PROMIS10")
    patient_id: str
    encounter_id: Optional[str] = None
    answers: dict[str, Any] = Field(..., description="Question ID to selected score/option map")
    clinical_notes: Optional[str] = None


class PROMResponseDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    response_id: str
    prom_id: int
    prom_code: Optional[str] = None
    prom_title: Optional[str] = None
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    encounter_id: Optional[int] = None
    answers_json: dict[str, Any]
    calculated_score: float
    severity_interpretation: str
    clinical_notes: Optional[str] = None
    completed_at: datetime
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None


class PROMResponseListResponse(BaseModel):
    items: list[PROMResponseDetail]
    total: int


# ==============================================================================
# TELEHEALTH & VIRTUAL CARE SCHEMAS
# ==============================================================================

class TelehealthSessionCreate(BaseModel):
    patient_id: str
    clinician_user_id: Optional[int] = None
    appointment_id: Optional[str] = None
    encounter_id: Optional[str] = None
    scheduled_start: datetime
    visit_reason: str = Field(..., description="Indication for virtual consultation")


class TelehealthSessionUpdate(BaseModel):
    status: Optional[TelehealthStatus] = None
    session_notes: Optional[str] = None
    followup_instructions: Optional[str] = None
    create_followup_task: Optional[bool] = False


class TelehealthSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    clinician_user_id: int
    clinician_name: Optional[str] = None
    appointment_id: Optional[int] = None
    encounter_id: Optional[int] = None
    status: str
    scheduled_start: datetime
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    visit_reason: str
    pre_visit_rpm_summary_json: Optional[dict[str, Any]] = None
    pre_visit_prom_summary_json: Optional[dict[str, Any]] = None
    session_notes: Optional[str] = None
    followup_instructions: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TelehealthSessionListResponse(BaseModel):
    items: list[TelehealthSessionResponse]
    total: int
