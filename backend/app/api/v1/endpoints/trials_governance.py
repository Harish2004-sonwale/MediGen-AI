"""API endpoints for Clinical Trial Governance, Multi-Center Sites, Protocol Deviations, CAPA & Automated Prescreening.

Phase 9.0.27: Enterprise Clinical Trial Auto-Enrollment, Protocol Deviations & Multi-Center Regulatory Auditing.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_roles
from app.models.trials_governance import (
    DeviationCategory,
    DeviationSeverity,
    DeviationStatus,
)
from app.models.user import User
from app.schemas.trials_governance import (
    CAPACreateRequest,
    CAPAResponse,
    IRBNotificationCreateRequest,
    IRBNotificationResponse,
    MultiCenterTrialGovernanceSummary,
    ProtocolDeviationCreate,
    ProtocolDeviationResponse,
    ProtocolDeviationListResponse,
    StudySiteCreate,
    StudySiteListResponse,
    StudySiteResponse,
    TrialPrescreenEvaluationResponse,
)
from app.services.trials_governance_service import TrialsGovernanceService

router = APIRouter()


@router.get("/prescreen/{patient_id}", response_model=TrialPrescreenEvaluationResponse)
def evaluate_patient_prescreening(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Evaluates patient eligibility against all active clinical trial protocols.
    """
    try:
        res = TrialsGovernanceService.evaluate_patient_prescreening(db=db, patient_id=patient_id)
        return TrialPrescreenEvaluationResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/sites", response_model=StudySiteListResponse)
def list_study_sites(
    trial_id: Optional[int] = Query(None, description="Filter by clinical trial ID"),
    facility_id: Optional[str] = Query(None, description="Filter by facility context"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Lists multi-center study sites participating in clinical research.
    """
    fac = facility_id or getattr(current_user, "default_facility_id", None)
    sites = TrialsGovernanceService.list_study_sites(db=db, trial_id=trial_id, facility_id=fac)
    return StudySiteListResponse(
        total=len(sites),
        sites=[StudySiteResponse.model_validate(s) for s in sites],
    )


@router.post("/sites", response_model=StudySiteResponse, status_code=status.HTTP_201_CREATED)
def create_study_site(
    payload: StudySiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "doctor"])),
):
    """
    Registers a new multi-center study site.
    """
    facility_id = payload.facility_id or getattr(current_user, "default_facility_id", None)
    site = TrialsGovernanceService.create_study_site(
        db=db,
        trial_id=payload.trial_id,
        site_name=payload.site_name,
        facility_id=facility_id,
        principal_investigator_user_id=payload.principal_investigator_user_id or current_user.id,
        target_accrual=payload.target_accrual,
        irb_approval_number=payload.irb_approval_number,
        irb_approval_date=payload.irb_approval_date,
        irb_expiry_date=payload.irb_expiry_date,
    )
    return StudySiteResponse.model_validate(site)


@router.get("/deviations", response_model=ProtocolDeviationListResponse)
def list_protocol_deviations(
    trial_id: Optional[int] = Query(None, description="Filter by trial ID"),
    severity: Optional[DeviationSeverity] = Query(None, description="Filter by severity"),
    status_filter: Optional[DeviationStatus] = Query(None, alias="status", description="Filter by deviation status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Lists trial protocol deviations and GCP non-compliance records.
    """
    deviations = TrialsGovernanceService.list_protocol_deviations(
        db=db, trial_id=trial_id, severity=severity, status=status_filter
    )
    return ProtocolDeviationListResponse(
        total=len(deviations),
        deviations=[ProtocolDeviationResponse.model_validate(d) for d in deviations],
    )


@router.post("/deviations", response_model=ProtocolDeviationResponse, status_code=status.HTTP_201_CREATED)
def report_protocol_deviation(
    payload: ProtocolDeviationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "healthcare_staff"])),
):
    """
    Reports a protocol deviation with automatic GCP risk categorization and IRB submission determination.
    """
    deviation = TrialsGovernanceService.report_protocol_deviation(
        db=db,
        trial_id=payload.trial_id,
        reported_by_user_id=current_user.id,
        deviation_category=payload.deviation_category,
        severity=payload.severity,
        description=payload.description,
        occurred_at=payload.occurred_at,
        discovered_at=payload.discovered_at,
        site_id=payload.site_id,
        patient_id=payload.patient_id,
        impact_on_patient_safety=payload.impact_on_patient_safety,
        impact_on_data_integrity=payload.impact_on_data_integrity,
        requires_irb_submission=payload.requires_irb_submission,
    )
    return ProtocolDeviationResponse.model_validate(deviation)


@router.post("/deviations/{deviation_id}/capa", response_model=CAPAResponse, status_code=status.HTTP_201_CREATED)
def create_capa_record(
    deviation_id: int,
    payload: CAPACreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "healthcare_staff"])),
):
    """
    Assigns a formal Corrective and Preventive Action (CAPA) plan to a protocol deviation.
    """
    try:
        capa = TrialsGovernanceService.create_capa_record(
            db=db,
            deviation_id=deviation_id,
            root_cause_category=payload.root_cause_category,
            root_cause_analysis=payload.root_cause_analysis,
            corrective_action=payload.corrective_action,
            preventive_action=payload.preventive_action,
            assigned_owner_user_id=payload.assigned_owner_user_id,
            target_resolution_date=payload.target_resolution_date,
        )
        return CAPAResponse.model_validate(capa)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/deviations/{deviation_id}/submit-irb", response_model=IRBNotificationResponse)
def submit_irb_notification(
    deviation_id: int,
    payload: IRBNotificationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "healthcare_staff"])),
):
    """
    Submits a regulatory safety filing / protocol deviation notification to the Institutional Review Board (IRB).
    """
    try:
        notif = TrialsGovernanceService.submit_irb_notification(
            db=db,
            deviation_id=deviation_id,
            irb_committee_name=payload.irb_committee_name,
            submission_type=payload.submission_type,
            submitted_by_user_id=current_user.id,
            custom_remarks=payload.custom_remarks,
        )
        return IRBNotificationResponse.model_validate(notif)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/trials/{trial_id}/summary", response_model=MultiCenterTrialGovernanceSummary)
def get_trial_governance_summary(
    trial_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieves multi-center study site accrual performance, deviation safety metrics, and CAPA resolution statistics.
    """
    try:
        res = TrialsGovernanceService.get_trial_governance_summary(db=db, trial_id=trial_id)
        return MultiCenterTrialGovernanceSummary(**res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
