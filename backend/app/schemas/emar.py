"""Pydantic v2 schemas for Closed-Loop Medication Administration (eMAR) & Barcode Verification (BCMA)."""

from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.emar import (
    BCMAVerificationStatus,
    HighAlertMedicationCategory,
    MARStatus,
)


# ==============================================================================
# Medication Barcode Directory Schemas
# ==============================================================================

class MedicationBarcodeCreate(BaseModel):
    barcode: str = Field(..., min_length=4, max_length=128)
    medication_name: str = Field(..., min_length=2, max_length=255)
    rxnorm_code: str = Field(..., min_length=2, max_length=64)
    ndc_code: Optional[str] = None
    standard_dose: str = Field(..., min_length=1, max_length=64)
    dosage_form: str = "tablet"
    route: str = "oral"
    is_high_alert: bool = False
    high_alert_category: Optional[HighAlertMedicationCategory] = None


class MedicationBarcodeResponse(BaseModel):
    id: int
    barcode: str
    medication_name: str
    rxnorm_code: str
    ndc_code: Optional[str] = None
    standard_dose: str
    dosage_form: str
    route: str
    is_high_alert: bool
    high_alert_category: Optional[HighAlertMedicationCategory] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MedicationBarcodeListResponse(BaseModel):
    total: int
    items: List[MedicationBarcodeResponse]


# ==============================================================================
# eMAR (Medication Administration Record) Schemas
# ==============================================================================

class MARCreateRequest(BaseModel):
    patient_id: str
    order_id: Optional[int] = None
    facility_id: Optional[str] = None
    medication_name: str
    medication_code: str
    prescribed_dose: str
    prescribed_route: str
    prescribed_frequency: str = "daily"
    scheduled_time: datetime
    is_high_alert: bool = False
    requires_dual_witness: bool = False


class MARScheduleDosesRequest(BaseModel):
    patient_id: str
    order_id: Optional[int] = None
    facility_id: Optional[str] = None
    medication_name: str
    medication_code: str
    prescribed_dose: str
    prescribed_route: str
    frequency_code: str  # BID, TID, Q4H, Q6H, Q8H, Q12H, DAILY, STAT, PRN
    start_time: Optional[datetime] = None
    total_doses: int = Field(default=4, ge=1, le=24)
    is_high_alert: bool = False
    requires_dual_witness: bool = False


class MARAdministerRequest(BaseModel):
    administered_dose: Optional[str] = None
    administered_route: Optional[str] = None
    site_of_administration: Optional[str] = None
    scanned_patient_barcode: Optional[str] = None
    scanned_med_barcode: Optional[str] = None
    vital_signs_pre_admin: Optional[dict[str, Any]] = None
    variance_reason: Optional[str] = None
    patient_response_notes: Optional[str] = None


class MARHoldRefuseRequest(BaseModel):
    status: MARStatus  # HELD or REFUSED
    clinical_reason: str = Field(..., min_length=5)
    patient_response_notes: Optional[str] = None


class DualSignoffRequest(BaseModel):
    witness_user_email: str
    witness_password: str
    witness_notes: Optional[str] = None


class MARRecordResponse(BaseModel):
    id: int
    mar_id: str
    order_id: Optional[int] = None
    patient_id: int
    patient_identifier: Optional[str] = None
    facility_id: str
    medication_name: str
    medication_code: str
    prescribed_dose: str
    prescribed_route: str
    prescribed_frequency: str
    scheduled_time: datetime
    actual_admin_time: Optional[datetime] = None
    status: MARStatus
    administering_nurse_id: Optional[int] = None
    administering_nurse_name: Optional[str] = None
    administered_dose: Optional[str] = None
    administered_route: Optional[str] = None
    site_of_administration: Optional[str] = None
    is_high_alert: bool
    requires_dual_witness: bool
    dual_witness_user_id: Optional[int] = None
    dual_witness_user_name: Optional[str] = None
    dual_witness_timestamp: Optional[datetime] = None
    variance_reason: Optional[str] = None
    patient_response_notes: Optional[str] = None
    vital_signs_pre_admin_json: Optional[dict[str, Any]] = None
    barcode_scanned_patient_id: Optional[str] = None
    barcode_scanned_med_id: Optional[str] = None
    verification_passed: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MARScheduleListResponse(BaseModel):
    total: int
    records: List[MARRecordResponse]


# ==============================================================================
# BCMA 5-Rights Verification Schemas
# ==============================================================================

class BCMAVerify5RightsRequest(BaseModel):
    mar_id: Optional[str] = None
    patient_id: str
    scanned_patient_barcode: str
    scanned_med_barcode: str
    intended_dose: Optional[str] = None
    intended_route: Optional[str] = None


class RightVerificationResult(BaseModel):
    passed: bool
    expected: str
    scanned: str
    details: Optional[str] = None


class BCMAVerify5RightsResponse(BaseModel):
    verification_status: BCMAVerificationStatus
    overall_passed: bool
    patient_verification: RightVerificationResult
    medication_verification: RightVerificationResult
    dose_verification: RightVerificationResult
    route_verification: RightVerificationResult
    time_verification: RightVerificationResult
    is_high_alert: bool
    requires_dual_signoff: bool
    matched_mar_record: Optional[MARRecordResponse] = None
    discrepancy_warnings: List[str]
    verification_token: str
    timestamp: datetime


class BCMALogResponse(BaseModel):
    id: int
    verification_id: str
    mar_id: Optional[int] = None
    patient_id: int
    user_id: int
    scanned_patient_barcode: str
    scanned_med_barcode: str
    patient_matched: bool
    medication_matched: bool
    dose_matched: bool
    route_matched: bool
    time_matched: bool
    verification_status: BCMAVerificationStatus
    mismatch_details_json: Optional[dict[str, Any]] = None
    override_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
