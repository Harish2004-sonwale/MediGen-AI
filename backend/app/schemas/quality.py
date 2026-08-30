"""Pydantic schemas for Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting.

Phase 9.0.14: Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting Engine.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class QualityDomain(str, Enum):
    CHRONIC_DISEASE_MANAGEMENT = "chronic_disease_management"
    PREVENTIVE_CARE = "preventive_care"
    PATIENT_SAFETY = "patient_safety"
    CARE_COORDINATION = "care_coordination"


class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    EXCLUDED = "excluded"
    MISSING_DATA = "missing_data"


class GapSeverity(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class GapStatus(str, Enum):
    OPEN = "open"
    IN_REMEDIATION = "in_remediation"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ReportScope(str, Enum):
    ORGANIZATION = "organization"
    PROVIDER = "provider"
    COHORT = "cohort"
    MEASURE = "measure"


# ==============================================================================
# QUALITY MEASURE DEFINITION SCHEMAS
# ==============================================================================

class QualityMeasureCreate(BaseModel):
    measure_id: str = Field(..., max_length=64, description="Unique code (e.g. CQM-001-DM-HBA1C)")
    title: str = Field(..., max_length=255, description="Standard measure title")
    description: str = Field(..., description="Detailed clinical measure description")
    version: str = Field(default="1.0.0", max_length=20)
    domain: QualityDomain = Field(default=QualityDomain.CHRONIC_DISEASE_MANAGEMENT)
    hedis_mips_reference: Optional[str] = Field(default=None, max_length=100)
    denominator_criteria_json: Optional[dict[str, Any]] = None
    numerator_criteria_json: Optional[dict[str, Any]] = None
    exclusion_criteria_json: Optional[dict[str, Any]] = None
    target_compliance_rate: float = Field(default=80.0, ge=0.0, le=100.0)
    is_active: bool = Field(default=True)


class QualityMeasureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    measure_id: str
    title: str
    description: str
    version: str
    domain: QualityDomain
    hedis_mips_reference: Optional[str] = None
    denominator_criteria_json: Optional[dict[str, Any]] = None
    numerator_criteria_json: Optional[dict[str, Any]] = None
    exclusion_criteria_json: Optional[dict[str, Any]] = None
    target_compliance_rate: float
    is_active: bool
    created_at: datetime
    updated_at: datetime


class QualityMeasureListResponse(BaseModel):
    items: list[QualityMeasureResponse]
    total: int


# ==============================================================================
# PATIENT-LEVEL QUALITY RESULT SCHEMAS
# ==============================================================================

class QualityMeasureResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    result_id: str
    measure_id: int
    measure_code: Optional[str] = None
    measure_title: Optional[str] = None
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    measurement_period_start: Optional[datetime] = None
    measurement_period_end: Optional[datetime] = None
    is_eligible: bool
    is_excluded: bool
    exclusion_reason: Optional[str] = None
    is_numerator_compliant: bool
    compliance_status: ComplianceStatus
    evidence_json: Optional[dict[str, Any]] = None
    gap_reason: Optional[str] = None
    remediation_action: Optional[str] = None
    calculated_by_user_id: Optional[int] = None
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime


class QualityMeasureResultListResponse(BaseModel):
    items: list[QualityMeasureResultResponse]
    total: int


# ==============================================================================
# GAP IN CARE SCHEMAS
# ==============================================================================

class QualityMeasureGapUpdate(BaseModel):
    status: Optional[GapStatus] = None
    recommended_action: Optional[str] = None
    due_date: Optional[datetime] = None


class QualityMeasureGapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    gap_id: str
    result_id: int
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    measure_id: int
    measure_code: Optional[str] = None
    measure_title: Optional[str] = None
    gap_type: str
    severity: GapSeverity
    status: GapStatus
    gap_description: str
    missing_data_elements: Optional[str] = None
    recommended_action: str
    due_date: Optional[datetime] = None
    linked_care_task_id: Optional[int] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class QualityMeasureGapListResponse(BaseModel):
    items: list[QualityMeasureGapResponse]
    total: int


# ==============================================================================
# COMPLIANCE AUDIT REPORT SCHEMAS
# ==============================================================================

class QualityMeasureReportCreate(BaseModel):
    title: Optional[str] = Field(default=None, description="Optional title for audit report")
    report_scope: ReportScope = Field(default=ReportScope.ORGANIZATION)
    measurement_period_start: Optional[datetime] = None
    measurement_period_end: Optional[datetime] = None


class QualityMeasureSummary(BaseModel):
    measure_code: str
    measure_title: str
    domain: str
    eligible_count: int
    numerator_count: int
    excluded_count: int
    compliance_rate: float
    target_rate: float
    benchmark_met: bool


class QualityMeasureReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: str
    title: str
    reporting_period_start: datetime
    reporting_period_end: datetime
    report_scope: ReportScope
    total_eligible_population: int
    total_numerator_compliant: int
    overall_performance_rate: float
    measure_summaries_json: list[QualityMeasureSummary]
    audit_metadata_json: Optional[dict[str, Any]] = None
    generated_by_user_id: Optional[int] = None
    generated_by_user_name: Optional[str] = None
    generated_at: datetime
    created_at: datetime


class QualityMeasureReportListResponse(BaseModel):
    items: list[QualityMeasureReportResponse]
    total: int
