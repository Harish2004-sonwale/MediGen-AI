"""REST API Endpoints for Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting.

Phase 9.0.14: Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting Engine.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_active_user,
    require_role,
)
from app.database import get_db
from app.models.patient import Patient
from app.models.user import User, UserRole

require_clinical_role = require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)
require_staff_or_admin = require_role(UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN)

from app.schemas.quality import (
    QualityMeasureGapListResponse,
    QualityMeasureGapResponse,
    QualityMeasureGapUpdate,
    QualityMeasureListResponse,
    QualityMeasureReportCreate,
    QualityMeasureReportListResponse,
    QualityMeasureReportResponse,
    QualityMeasureResponse,
    QualityMeasureResultListResponse,
    QualityMeasureResultResponse,
)
from app.schemas.task import BackgroundTask
from app.services import quality_service

router = APIRouter()


def _resolve_patient_id(db: Session, patient_identifier: str) -> int:
    """Resolve numerical patient ID from string identifier."""
    if patient_identifier.isdigit():
        return int(patient_identifier)
    p = db.query(Patient).filter(Patient.patient_id == patient_identifier).first()
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_identifier}' not found.",
        )
    return p.id


# ==============================================================================
# MEASURE DEFINITION ENDPOINTS
# ==============================================================================

@router.get(
    "/measures",
    response_model=QualityMeasureListResponse,
    status_code=status.HTTP_200_OK,
    summary="List standardized clinical quality measures (CQMs)",
)
def list_quality_measures(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    is_active: Optional[bool] = Query(None, description="Filter active/retired measures"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> QualityMeasureListResponse:
    """Retrieve all defined quality measures."""
    measures = quality_service.get_quality_measures(db, domain=domain, is_active=is_active)
    return QualityMeasureListResponse(items=measures, total=len(measures))


@router.get(
    "/measures/{measure_id}",
    response_model=QualityMeasureResponse,
    status_code=status.HTTP_200_OK,
    summary="Get details for a specific quality measure",
)
def get_quality_measure(
    measure_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> QualityMeasureResponse:
    """Retrieve measure metadata and numerator/denominator definitions."""
    measure = quality_service.get_quality_measure_by_id(db, measure_id)
    return QualityMeasureResponse.model_validate(measure)


# ==============================================================================
# PATIENT QUALITY EVALUATION ENDPOINTS
# ==============================================================================

@router.post(
    "/patients/{patient_identifier}/evaluate",
    response_model=QualityMeasureResultListResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate patient against all active clinical quality measures",
)
def evaluate_patient_measures(
    patient_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinical_role),
) -> QualityMeasureResultListResponse:
    """Evaluate patient clinical data deterministically and synchronize care gaps."""
    pid = _resolve_patient_id(db, patient_identifier)
    results = quality_service.evaluate_patient_quality_measures(db, pid, calculated_by_user_id=current_user.id)
    return QualityMeasureResultListResponse(items=results, total=len(results))


@router.get(
    "/patients/{patient_identifier}/results",
    response_model=QualityMeasureResultListResponse,
    status_code=status.HTTP_200_OK,
    summary="List clinical quality results and compliance status for a patient",
)
def list_patient_quality_results(
    patient_identifier: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> QualityMeasureResultListResponse:
    """Retrieve evaluated quality measure results for a patient with RBAC patient isolation."""
    pid = _resolve_patient_id(db, patient_identifier)

    # Patient isolation check
    if current_user.role == UserRole.PATIENT:
        p = db.query(Patient).filter(Patient.id == pid).first()
        if not p or not p.email or p.email.strip().lower() != current_user.email.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only view your own quality metrics.",
            )


    results = quality_service.list_patient_quality_results(db, pid)
    return QualityMeasureResultListResponse(items=results, total=len(results))


# ==============================================================================
# GAPS IN CARE ENDPOINTS
# ==============================================================================

@router.get(
    "/gaps",
    response_model=QualityMeasureGapListResponse,
    status_code=status.HTTP_200_OK,
    summary="List active and historical gaps in care across population",
)
def list_quality_gaps(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (open, in_remediation, resolved)"),
    severity: Optional[str] = Query(None, description="Filter by severity (LOW, MODERATE, HIGH, CRITICAL)"),
    patient_id: Optional[str] = Query(None, description="Filter by patient identifier"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinical_role),
) -> QualityMeasureGapListResponse:
    """List population care gaps with prioritization."""
    pid = _resolve_patient_id(db, patient_id) if patient_id else None
    gaps = quality_service.list_quality_gaps(db, status_filter=status_filter, severity=severity, patient_id=pid)
    return QualityMeasureGapListResponse(items=gaps, total=len(gaps))


@router.patch(
    "/gaps/{gap_id}",
    response_model=QualityMeasureGapResponse,
    status_code=status.HTTP_200_OK,
    summary="Update care gap status or remediation details",
)
def update_quality_gap(
    gap_id: str,
    payload: QualityMeasureGapUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinical_role),
) -> QualityMeasureGapResponse:
    """Update care gap resolution notes or status."""
    return quality_service.update_quality_gap(db, gap_id, payload)


@router.post(
    "/gaps/{gap_id}/create-care-task",
    response_model=QualityMeasureGapResponse,
    status_code=status.HTTP_200_OK,
    summary="Auto-create linked CareTask for gap remediation",
)
def create_care_task_for_gap(
    gap_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinical_role),
) -> QualityMeasureGapResponse:
    """Convert care gap into actionable CareTask in patient CarePlan."""
    return quality_service.create_care_task_for_gap(db, gap_id, current_user_id=current_user.id)


# ==============================================================================
# AUDIT & COMPLIANCE REPORTING ENDPOINTS
# ==============================================================================

@router.post(
    "/reports/generate",
    response_model=QualityMeasureReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate population-level HEDIS/MIPS compliance audit report",
)
def generate_compliance_report(
    payload: QualityMeasureReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin),
) -> QualityMeasureReportResponse:
    """Generate an immutable population compliance audit report with data provenance."""
    return quality_service.generate_compliance_report(db, payload, current_user_id=current_user.id)


@router.get(
    "/reports",
    response_model=QualityMeasureReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List historical compliance audit reports",
)
def list_compliance_reports(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin),
) -> QualityMeasureReportListResponse:
    """Retrieve generated compliance reports."""
    reports = quality_service.list_compliance_reports(db, limit=limit)
    return QualityMeasureReportListResponse(items=reports, total=len(reports))


@router.get(
    "/reports/{report_id}",
    response_model=QualityMeasureReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get compliance audit report details",
)
def get_compliance_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_or_admin),
) -> QualityMeasureReportResponse:
    """Retrieve compliance report breakdown and audit hash."""
    report = quality_service.get_compliance_report_by_id(db, report_id)
    resp = QualityMeasureReportResponse.model_validate(report)
    if report.generated_by_user:
        resp.generated_by_user_name = report.generated_by_user.name
    return resp


# ==============================================================================
# ASYNC TASK DISPATCH ENDPOINTS
# ==============================================================================

@router.post(
    "/tasks/calculate",
    response_model=BackgroundTask,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue background quality measure calculation job",
)
def enqueue_quality_calculation_task(
    patient_id: Optional[str] = Query(None, description="Optional patient identifier for focused calculation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinical_role),
) -> BackgroundTask:
    """Trigger asynchronous background quality calculation worker."""
    pid = _resolve_patient_id(db, patient_id) if patient_id else None
    return quality_service.enqueue_quality_calculation_task(db, patient_id=pid, user_id=current_user.id)
