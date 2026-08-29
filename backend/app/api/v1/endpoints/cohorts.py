"""FastAPI API router for Patient Cohorts, Disease Registries & Clinical Risk Stratification.

Phase 9.0.11: Clinical Cohort Analytics, Patient Registry Management & Longitudinal Risk Stratification.
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.cohort import (
    CohortAnalyticsResponse,
    CohortCreate,
    CohortListResponse,
    CohortMembershipCreate,
    CohortMembershipResponse,
    CohortResponse,
    CohortUpdate,
)
from app.schemas.risk_assessment import (
    RiskAssessmentListResponse,
    RiskAssessmentResponse,
    RiskStratifyRequest,
    RiskType,
)
from app.schemas.task import BackgroundTaskResponse
from app.services import cohort_service

router = APIRouter(tags=["Clinical Cohorts & Risk Stratification"])


# ==============================================================================
# COHORT & REGISTRY MANAGEMENT
# ==============================================================================

@router.post(
    "/cohorts",
    response_model=CohortResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new patient cohort or disease registry",
)
def create_cohort(
    cohort_in: CohortCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CohortResponse:
    """Create a new disease registry or patient cohort with optional inclusion criteria."""
    return cohort_service.create_cohort(db=db, cohort_in=cohort_in, current_user=current_user)


@router.get(
    "/cohorts",
    response_model=CohortListResponse,
    status_code=status.HTTP_200_OK,
    summary="List patient cohorts and disease registries",
)
def list_cohorts(
    cohort_type: Optional[str] = Query(None, description="Filter by cohort type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CohortListResponse:
    """List cohorts with current member count and metadata."""
    return cohort_service.list_cohorts(db=db, current_user=current_user, cohort_type=cohort_type)


@router.get(
    "/cohorts/{cohort_id}",
    response_model=CohortResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve cohort details",
)
def get_cohort(
    cohort_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CohortResponse:
    """Retrieve details and criteria definition for a specific cohort."""
    return cohort_service.get_cohort(db=db, cohort_id=cohort_id, current_user=current_user)


@router.patch(
    "/cohorts/{cohort_id}",
    response_model=CohortResponse,
    status_code=status.HTTP_200_OK,
    summary="Update cohort details or criteria",
)
def update_cohort(
    cohort_id: str,
    cohort_in: CohortUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CohortResponse:
    """Update title, description, or dynamic criteria rules for a cohort."""
    return cohort_service.update_cohort(db=db, cohort_id=cohort_id, cohort_in=cohort_in, current_user=current_user)


@router.delete(
    "/cohorts/{cohort_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a patient cohort (Admin only)",
)
def delete_cohort(
    cohort_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Delete a cohort and all membership records."""
    return cohort_service.delete_cohort(db=db, cohort_id=cohort_id, current_user=current_user)


# ==============================================================================
# COHORT MEMBERSHIP
# ==============================================================================

@router.get(
    "/cohorts/{cohort_id}/members",
    response_model=list[CohortMembershipResponse],
    status_code=status.HTTP_200_OK,
    summary="List patient members of a cohort",
)
def list_cohort_members(
    cohort_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[CohortMembershipResponse]:
    """List all enrolled patient members with latest risk score snapshot."""
    return cohort_service.list_cohort_members(db=db, cohort_id=cohort_id, current_user=current_user)


@router.post(
    "/cohorts/{cohort_id}/members",
    response_model=CohortMembershipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll patient in cohort",
)
def add_cohort_member(
    cohort_id: str,
    member_in: CohortMembershipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CohortMembershipResponse:
    """Manually enroll a patient in a cohort."""
    return cohort_service.add_cohort_member(
        db=db,
        cohort_id=cohort_id,
        patient_id_str=member_in.patient_id,
        notes=member_in.notes,
        current_user=current_user,
    )


@router.delete(
    "/cohorts/{cohort_id}/members/{patient_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove patient from cohort",
)
def remove_cohort_member(
    cohort_id: str,
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    """Remove a patient from a cohort/registry."""
    return cohort_service.remove_cohort_member(
        db=db,
        cohort_id=cohort_id,
        patient_id_str=patient_id,
        current_user=current_user,
    )


@router.get(
    "/cohorts/{cohort_id}/analytics",
    response_model=CohortAnalyticsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve cohort population analytics",
)
def get_cohort_analytics(
    cohort_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CohortAnalyticsResponse:
    """Calculate aggregate risk tier distribution, mean scores, alert counts, and task metrics."""
    return cohort_service.get_cohort_analytics(db=db, cohort_id=cohort_id, current_user=current_user)


# ==============================================================================
# CLINICAL RISK STRATIFICATION
# ==============================================================================

@router.post(
    "/patients/{patient_id}/risk-assessments",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Calculate clinical risk assessment for patient",
)
def assess_patient_risk(
    patient_id: str,
    request: RiskStratifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RiskAssessmentResponse:
    """Calculate multi-factorial clinical risk score, contributing factors, and mitigation actions."""
    return cohort_service.assess_patient_risk(
        db=db,
        patient_id_str=patient_id,
        risk_type=request.risk_type,
        current_user=current_user,
        encounter_id=request.encounter_id,
        custom_context=request.custom_context,
    )


@router.get(
    "/patients/{patient_id}/risk-assessments",
    response_model=RiskAssessmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List patient historical risk assessments",
)
def list_patient_risk_assessments(
    patient_id: str,
    risk_type: Optional[str] = Query(None, description="Filter by risk type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RiskAssessmentListResponse:
    """Retrieve chronological risk assessments for a patient."""
    return cohort_service.list_patient_risk_assessments(
        db=db,
        patient_id_str=patient_id,
        current_user=current_user,
        risk_type=risk_type,
    )


@router.get(
    "/risk-assessments/{assessment_id}",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve risk assessment details",
)
def get_risk_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RiskAssessmentResponse:
    """Retrieve full risk assessment details including contributing factors and recommendations."""
    return cohort_service.get_risk_assessment(db=db, assessment_id=assessment_id, current_user=current_user)


# ==============================================================================
# ASYNCHRONOUS WORKER TASK ENQUEUE
# ==============================================================================

@router.post(
    "/tasks/cohorts/{cohort_id}/evaluate",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue background dynamic cohort evaluation",
)
def enqueue_cohort_evaluation(
    cohort_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BackgroundTaskResponse:
    """Enqueue asynchronous background task to re-evaluate dynamic cohort membership rules."""
    task = cohort_service.enqueue_cohort_evaluation(db=db, cohort_id=cohort_id, current_user=current_user)
    return BackgroundTaskResponse.model_validate(task)


@router.post(
    "/tasks/patients/{patient_id}/stratify-risk",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue background patient risk stratification",
)
def enqueue_patient_risk_stratification(
    patient_id: str,
    request: RiskStratifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BackgroundTaskResponse:
    """Enqueue asynchronous background task to calculate clinical risk scores."""
    task = cohort_service.enqueue_patient_risk_stratification(
        db=db,
        patient_id=patient_id,
        risk_type=request.risk_type,
        current_user=current_user,
    )
    return BackgroundTaskResponse.model_validate(task)
