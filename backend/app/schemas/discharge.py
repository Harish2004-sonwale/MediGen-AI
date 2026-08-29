"""Pydantic schemas for Clinical Discharge Protocols & Continuity of Care.

Phase 9.0.12: Clinical Transitions of Care, Multi-Disciplinary Handoffs (I-PASS/SBAR) & Automated Discharge Protocol Synthesis.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class DischargeDisposition(str, Enum):
    HOME_SELF_CARE = "home_self_care"
    HOME_HEALTH_SERVICES = "home_health_services"
    SKILLED_NURSING_FACILITY = "skilled_nursing_facility"
    REHAB_FACILITY = "rehab_facility"
    HOSPICE = "hospice"
    TRANSFER_ACUTE_CARE = "transfer_acute_care"


class DischargeStatus(str, Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    READY_FOR_DISCHARGE = "ready_for_discharge"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MedicationReconciliationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    medication_name: str = Field(..., description="Name of medication")
    dose: str = Field(..., description="Dosage and strength")
    route: str = Field(default="oral", description="Route of administration")
    frequency: str = Field(..., description="Dosing frequency")
    reconciliation_status: str = Field(
        ...,
        description="continued | dosage_adjusted | discontinued | newly_prescribed",
    )
    clinical_rationale: str = Field(..., description="Rationale for continuation, change, or discontinuation")


class FollowupAppointmentItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_or_specialty: str = Field(..., description="Physician, clinic, or medical subspecialty")
    timeframe: str = Field(..., description="Recommended timeframe, e.g. '7-10 days'")
    purpose: str = Field(..., description="Clinical purpose of follow-up encounter")
    contact_phone: Optional[str] = Field(default=None, description="Clinic phone number")


class PendingDiagnosticItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_name: str = Field(..., description="Name of ordered lab or imaging study")
    ordered_date: Optional[str] = Field(default=None, description="Date ordered")
    follow_up_physician: str = Field(..., description="Clinician responsible for reviewing result")
    instructions: str = Field(..., description="Action instructions if abnormal")


class WarningSymptomItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symptom_title: str = Field(..., description="Red flag symptom description")
    urgency_level: str = Field(default="EMERGENCY_911", description="EMERGENCY_911 | URGENT_SAME_DAY | CALL_CLINIC")
    action_instructions: str = Field(..., description="Immediate instructions for patient or caregiver")


class DischargeProtocolCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    encounter_id: Optional[int] = Field(default=None, description="Inpatient or observation encounter ID")
    disposition: DischargeDisposition = Field(default=DischargeDisposition.HOME_SELF_CARE)
    discharge_date: Optional[datetime] = Field(default=None, description="Planned or actual discharge timestamp")
    hospital_course_summary: str = Field(..., min_length=10, description="Narrative summary of inpatient stay and interventions")
    primary_discharge_diagnosis: str = Field(..., min_length=3, description="Principal discharge diagnosis")
    secondary_diagnoses: list[str] = Field(default_factory=list, description="Secondary or chronic ongoing diagnoses")
    medication_reconciliation: list[MedicationReconciliationItem] = Field(default_factory=list, description="Reconciled discharge medications")
    followup_appointments: list[FollowupAppointmentItem] = Field(default_factory=list, description="Scheduled follow-up consultations")
    pending_tests: list[PendingDiagnosticItem] = Field(default_factory=list, description="Pending diagnostics and cultures")
    warning_symptoms: list[WarningSymptomItem] = Field(default_factory=list, description="Disease-specific red flag warning signs")
    activity_and_diet_instructions: Optional[str] = Field(default=None, description="Activity restrictions, physical therapy, and nutrition guidelines")


class DischargeProtocolSynthesizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    encounter_id: Optional[int] = None
    disposition: DischargeDisposition = Field(default=DischargeDisposition.HOME_SELF_CARE)
    custom_instructions: Optional[str] = None


class DischargeProtocolUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    disposition: Optional[DischargeDisposition] = None
    discharge_date: Optional[datetime] = None
    hospital_course_summary: Optional[str] = None
    primary_discharge_diagnosis: Optional[str] = None
    secondary_diagnoses: Optional[list[str]] = None
    medication_reconciliation: Optional[list[MedicationReconciliationItem]] = None
    followup_appointments: Optional[list[FollowupAppointmentItem]] = None
    pending_tests: Optional[list[PendingDiagnosticItem]] = None
    warning_symptoms: Optional[list[WarningSymptomItem]] = None
    activity_and_diet_instructions: Optional[str] = None
    status: Optional[DischargeStatus] = None


class DischargeSignoffRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signoff_role: str = Field(..., description="attending_physician | registered_nurse | clinical_pharmacist")
    clinical_notes: Optional[str] = Field(default=None, description="Signoff comments or validation confirmation")


class DischargeProtocolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    discharge_id: str
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    encounter_id: Optional[int] = None
    attending_user_id: Optional[int] = None
    attending_name: Optional[str] = None
    nurse_user_id: Optional[int] = None
    nurse_name: Optional[str] = None
    pharmacist_user_id: Optional[int] = None
    pharmacist_name: Optional[str] = None
    status: DischargeStatus
    disposition: DischargeDisposition
    discharge_date: Optional[datetime] = None
    hospital_course_summary: str
    primary_discharge_diagnosis: str
    secondary_diagnoses_json: Optional[list[str]] = None
    medication_reconciliation_json: Optional[list[dict[str, Any]]] = None
    followup_instructions_json: Optional[list[dict[str, Any]]] = None
    pending_tests_json: Optional[list[dict[str, Any]]] = None
    warning_symptoms_json: Optional[list[dict[str, Any]]] = None
    activity_and_diet_instructions: Optional[str] = None
    is_ai_generated: bool
    signed_off_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DischargeProtocolListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[DischargeProtocolResponse]
    total: int
