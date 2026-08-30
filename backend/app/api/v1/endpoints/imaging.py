"""REST API Router for Medical Imaging AI, Multimodal Diagnostics & Radiology Workflow.

Phase 9.0.18: Medical Imaging AI, Multimodal Diagnostics & Radiology Workflow.
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.imaging import ImagingStudy, RadiologyReport
from app.models.user import User, UserRole
from app.schemas.imaging import (
    FindingReviewRequest,
    ImagingAnalysisResponse,
    ImagingAssetCreate,
    ImagingAssetListResponse,
    ImagingAssetResponse,
    ImagingFindingListResponse,
    ImagingFindingResponse,
    ImagingStudyCreate,
    ImagingStudyListResponse,
    ImagingStudyResponse,
    ImagingStudyUpdate,
    ImagingTimelineResponse,
    RadiologyReportCreate,
    RadiologyReportListResponse,
    RadiologyReportResponse,
    RadiologyReportUpdate,
    ReportAmendRequest,
    ReportFinalizeRequest,
)
from app.schemas.task import BackgroundTask, BackgroundTaskResponse
from app.services.imaging_service import imaging_service
from app.services.task_service import build_task_response, enqueue_imaging_analysis_task as enqueue_imaging_task


router = APIRouter()


def _check_patient_access(current_user: User, patient_id_str_or_num: str | int, db: Session) -> None:
    """Enforce strict patient isolation for PATIENT role."""
    if current_user.role == UserRole.PATIENT:
        target_patient = imaging_service._resolve_patient(db, patient_id_str_or_num)
        if target_patient.email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: cannot access medical imaging for another patient",
            )


def _map_study_response(study: ImagingStudy) -> ImagingStudyResponse:
    """Format an ImagingStudy ORM entity into a rich response with counts."""
    has_crit = any(f.is_critical for f in study.findings) if study.findings else False
    return ImagingStudyResponse(
        id=study.id,
        study_id=study.study_id,
        patient_id=study.patient_id,
        patient_identifier=study.patient.patient_id if study.patient else None,
        patient_name=f"{study.patient.first_name} {study.patient.last_name}" if study.patient else None,
        encounter_id=study.encounter_id,
        order_id=study.order_id,
        modality=study.modality,
        body_site=study.body_site,
        study_description=study.study_description,
        accession_number=study.accession_number,
        study_datetime=study.study_datetime,
        performing_department=study.performing_department,
        referring_provider=study.referring_provider,
        status=study.status,
        source=study.source,
        external_identifier=study.external_identifier,
        metadata_json=study.metadata_json,
        provenance_hash=study.provenance_hash,
        created_at=study.created_at,
        updated_at=study.updated_at,
        assets_count=len(study.assets) if study.assets else 0,
        findings_count=len(study.findings) if study.findings else 0,
        reports_count=len(study.reports) if study.reports else 0,
        has_critical_findings=has_crit,
    )


def _map_report_response(report: RadiologyReport) -> RadiologyReportResponse:
    """Format a RadiologyReport ORM entity into a rich response."""
    return RadiologyReportResponse(
        id=report.id,
        report_id=report.report_id,
        study_id=report.study_id,
        study_identifier=report.study.study_id if report.study else None,
        study_description=report.study.study_description if report.study else None,
        modality=report.study.modality if report.study else None,
        body_site=report.study.body_site if report.study else None,
        patient_id=report.patient_id,
        patient_identifier=report.patient.patient_id if report.patient else None,
        patient_name=f"{report.patient.first_name} {report.patient.last_name}" if report.patient else None,
        encounter_id=report.encounter_id,
        order_id=report.order_id,
        status=report.status,
        clinical_indication=report.clinical_indication,
        technique=report.technique,
        comparison_studies=report.comparison_studies,
        findings=report.findings,
        impression=report.impression,
        recommendations=report.recommendations,
        critical_findings_summary=report.critical_findings_summary,
        is_critical=report.is_critical,
        ai_assistance_metadata_json=report.ai_assistance_metadata_json,
        author_user_id=report.author_user_id,
        author_name=report.author_user.name if report.author_user else None,
        signed_by_user_id=report.signed_by_user_id,
        signed_by_name=report.signed_by_user.name if report.signed_by_user else None,
        signed_at=report.signed_at,
        amendment_reason=report.amendment_reason,
        amended_from_report_id=report.amended_from_report_id,
        provenance_hash=report.provenance_hash,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


# =============================================================================
# 1. IMAGING STUDY ENDPOINTS
# =============================================================================

@router.post(
    "/patients/{patient_id}/imaging/studies",
    response_model=ImagingStudyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create / ingest an Imaging Study for a patient",
)
def create_imaging_study(
    patient_id: str,
    payload: ImagingStudyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ImagingStudyResponse:
    """Register a clinical imaging study under patient context."""
    _check_patient_access(current_user, patient_id, db)
    # Ensure patient_id in payload matches route
    payload.patient_id = patient_id
    study = imaging_service.create_study(db, payload, current_user)
    return _map_study_response(study)


@router.get(
    "/patients/{patient_id}/imaging/studies",
    response_model=ImagingStudyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List imaging studies for a patient",
)
def list_patient_imaging_studies(
    patient_id: str,
    modality: Optional[str] = Query(None, description="Filter by modality (e.g. XRAY, CT, MRI)"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. ORDERED, COMPLETED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ImagingStudyListResponse:
    """Retrieve all imaging studies for a patient."""
    _check_patient_access(current_user, patient_id, db)
    studies, total = imaging_service.list_studies(
        db, patient_id=patient_id, modality=modality, study_status=status, skip=skip, limit=limit
    )
    return ImagingStudyListResponse(items=[_map_study_response(s) for s in studies], total=total)


@router.get(
    "/imaging/studies",
    response_model=ImagingStudyListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all imaging studies (Clinician / Admin only)",
)
def list_all_imaging_studies(
    patient_id: Optional[str] = Query(None),
    modality: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ImagingStudyListResponse:
    """List imaging studies across the department."""
    if current_user.role == UserRole.PATIENT:
        if not patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patient users must specify their own patient_id",
            )
        _check_patient_access(current_user, patient_id, db)

    studies, total = imaging_service.list_studies(
        db, patient_id=patient_id, modality=modality, study_status=status, skip=skip, limit=limit
    )
    return ImagingStudyListResponse(items=[_map_study_response(s) for s in studies], total=total)


@router.get(
    "/imaging/studies/{study_id}",
    response_model=ImagingStudyResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Imaging Study details",
)
def get_imaging_study_detail(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ImagingStudyResponse:
    """Retrieve complete imaging study details."""
    study = imaging_service.get_study(db, study_id)
    _check_patient_access(current_user, study.patient_id, db)
    return _map_study_response(study)


# =============================================================================
# 2. IMAGE ASSETS & SERIES ENDPOINTS
# =============================================================================

@router.post(
    "/imaging/studies/{study_id}/assets",
    response_model=ImagingAssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach an image asset / DICOM series to an imaging study",
)
def upload_study_asset(
    study_id: str,
    payload: ImagingAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ImagingAssetResponse:
    """Register an image asset for a study."""
    study = imaging_service.get_study(db, study_id)
    _check_patient_access(current_user, study.patient_id, db)
    asset = imaging_service.add_asset(db, study_id, payload, current_user)
    return ImagingAssetResponse.model_validate(asset)


@router.get(
    "/imaging/studies/{study_id}/assets",
    response_model=ImagingAssetListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all image assets / series for a study",
)
def list_study_assets(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ImagingAssetListResponse:
    """List assets for an imaging study."""
    study = imaging_service.get_study(db, study_id)
    _check_patient_access(current_user, study.patient_id, db)
    assets = imaging_service.list_assets(db, study_id)
    return ImagingAssetListResponse(items=[ImagingAssetResponse.model_validate(a) for a in assets], total=len(assets))


# =============================================================================
# 3. AI-ASSISTED INTERPRETATION & FINDINGS
# =============================================================================

@router.post(
    "/imaging/studies/{study_id}/analyze",
    response_model=ImagingAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute multimodal AI interpretation on an imaging study",
)
def analyze_imaging_study(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ImagingAnalysisResponse:
    """Trigger deterministic multimodal AI analysis on an imaging study."""
    study = imaging_service.get_study(db, study_id)
    _check_patient_access(current_user, study.patient_id, db)

    result = imaging_service.run_ai_analysis(db, study_id, current_user)

    findings_res = [ImagingFindingResponse.model_validate(f) for f in result["findings"]]
    report_res = _map_report_response(result["draft_report"]) if result.get("draft_report") else None

    return ImagingAnalysisResponse(
        study_id=result["study_id"],
        status=result["status"],
        findings_count=result["findings_count"],
        critical_findings_count=result["critical_findings_count"],
        findings=findings_res,
        draft_report=report_res,
        multimodal_context=result["multimodal_context"],
        provenance_hash=result["provenance_hash"],
        evaluated_at=result["evaluated_at"],
    )


@router.get(
    "/imaging/studies/{study_id}/findings",
    response_model=ImagingFindingListResponse,
    status_code=status.HTTP_200_OK,
    summary="List structured findings for an imaging study",
)
def list_study_findings(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ImagingFindingListResponse:
    """Retrieve all structured image findings for a study."""
    study = imaging_service.get_study(db, study_id)
    _check_patient_access(current_user, study.patient_id, db)
    findings = [ImagingFindingResponse.model_validate(f) for f in study.findings]
    return ImagingFindingListResponse(items=findings, total=len(findings))


@router.post(
    "/imaging/findings/{finding_id}/review",
    response_model=ImagingFindingResponse,
    status_code=status.HTTP_200_OK,
    summary="Clinician review sign-off for an individual finding",
)
def review_imaging_finding(
    finding_id: str,
    payload: FindingReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ImagingFindingResponse:
    """Clinician confirmation, rejection, or amendment of an AI finding."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN, UserRole.HEALTHCARE_STAFF):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to review findings")
    finding = imaging_service.review_finding(db, finding_id, payload.review_status, payload.review_notes, current_user)
    return ImagingFindingResponse.model_validate(finding)


# =============================================================================
# 4. RADIOLOGY REPORT WORKFLOW
# =============================================================================

@router.get(
    "/imaging/reports/{report_id}",
    response_model=RadiologyReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Radiology Diagnostic Report details",
)
def get_radiology_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RadiologyReportResponse:
    """Retrieve radiology report by report_id."""
    report = imaging_service.get_report(db, report_id)
    _check_patient_access(current_user, report.patient_id, db)
    return _map_report_response(report)


@router.put(
    "/imaging/reports/{report_id}",
    response_model=RadiologyReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit draft radiology report",
)
def update_radiology_report(
    report_id: str,
    payload: RadiologyReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RadiologyReportResponse:
    """Edit draft report narrative sections."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN, UserRole.HEALTHCARE_STAFF):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to edit reports")
    report = imaging_service.update_draft_report(db, report_id, payload, current_user)
    return _map_report_response(report)


@router.post(
    "/imaging/reports/{report_id}/submit-review",
    response_model=RadiologyReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit draft report for radiologist review",
)
def submit_report_for_review(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RadiologyReportResponse:
    """Transition report to RADIOLOGIST_REVIEW status."""
    report = imaging_service.submit_report_for_review(db, report_id, current_user)
    return _map_report_response(report)


@router.post(
    "/imaging/reports/{report_id}/finalize",
    response_model=RadiologyReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Sign off and finalize radiology report (DOCTOR / ADMIN only)",
)
def finalize_radiology_report(
    report_id: str,
    payload: ReportFinalizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RadiologyReportResponse:
    """Attest and finalize a radiology diagnostic report."""
    report = imaging_service.finalize_report(db, report_id, payload, current_user)
    return _map_report_response(report)


@router.post(
    "/imaging/reports/{report_id}/amend",
    response_model=RadiologyReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Create an amended radiology report (DOCTOR / ADMIN only)",
)
def amend_radiology_report(
    report_id: str,
    payload: ReportAmendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RadiologyReportResponse:
    """Issue a formal amendment for a previously finalized report."""
    amended = imaging_service.amend_report(db, report_id, payload, current_user)
    return _map_report_response(amended)


# =============================================================================
# 5. LONGITUDINAL IMAGING TIMELINE & ASYNC TASKS
# =============================================================================

@router.get(
    "/patients/{patient_id}/imaging/timeline",
    response_model=ImagingTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve longitudinal imaging timeline for patient",
)
def get_patient_imaging_timeline(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ImagingTimelineResponse:
    """Chronological imaging event timeline."""
    _check_patient_access(current_user, patient_id, db)
    items = imaging_service.get_imaging_timeline(db, patient_id)
    return ImagingTimelineResponse(patient_id=patient_id, total_studies=len(items), items=items)


@router.post(
    "/imaging/tasks/studies/{study_id}/analyze",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue asynchronous background imaging analysis task",
)
def enqueue_imaging_analysis_task(
    study_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BackgroundTaskResponse:
    """Enqueue background analysis job."""
    task = enqueue_imaging_task(db=db, study_id_str=study_id, current_user=current_user)
    return build_task_response(task)
