"""FastAPI Endpoints for Regional Multi-Hospital Clinical Pathways & Care Plan Synchronization."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_roles
from app.core.tenant_context import resolve_facility_id
from app.models.user import User, UserRole
from app.schemas.pathway import (
    PathwayAdvanceStageRequest,
    PathwayEnrollRequest,
    PathwayMilestoneCompleteRequest,
    PatientPathwayEnrollmentResponse,
    RegionalPathwayCreate,
    RegionalPathwayListResponse,
    RegionalPathwayResponse,
)
from app.services.pathway_service import pathway_service

router = APIRouter(prefix="/pathways", tags=["Regional Clinical Pathways"])


@router.post(
    "",
    response_model=RegionalPathwayResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Define a new regional clinical pathway",
)
def create_pathway(
    pathway_in: RegionalPathwayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.DOCTOR])),
) -> RegionalPathwayResponse:
    """Create a multi-stage regional clinical protocol."""
    try:
        return pathway_service.create_pathway(
            db=db,
            pathway_in=pathway_in,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "",
    response_model=RegionalPathwayListResponse,
    summary="List available regional clinical pathways",
)
def list_pathways(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RegionalPathwayListResponse:
    """Retrieve all active regional pathway definitions."""
    items = pathway_service.list_pathways(db=db)
    return RegionalPathwayListResponse(total=len(items), items=items)


@router.get(
    "/{pathway_id}",
    response_model=RegionalPathwayResponse,
    summary="Get clinical pathway details by ID",
)
def get_pathway(
    pathway_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> RegionalPathwayResponse:
    """Retrieve a specific pathway definition."""
    try:
        return pathway_service.get_pathway(db=db, pathway_id=pathway_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/enroll",
    response_model=PatientPathwayEnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a patient in a regional clinical pathway",
)
def enroll_patient(
    req: PathwayEnrollRequest,
    db: Session = Depends(get_db),
    facility_id: str = Depends(resolve_facility_id),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN, UserRole.HEALTHCARE_STAFF])),
) -> PatientPathwayEnrollmentResponse:
    """Instantiate a patient pathway starting at Stage 1."""
    try:
        return pathway_service.enroll_patient(
            db=db,
            patient_id=req.patient_id,
            pathway_id=req.pathway_id,
            user=current_user,
            facility_id=facility_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/enrollments/{enrollment_id}/advance-stage",
    response_model=PatientPathwayEnrollmentResponse,
    summary="Advance patient to the next pathway stage across facilities",
)
def advance_stage(
    enrollment_id: str,
    req: PathwayAdvanceStageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN])),
) -> PatientPathwayEnrollmentResponse:
    """Advance to the subsequent stage, check cross-facility authorization, and dispatch outbox event."""
    try:
        return pathway_service.advance_stage(
            db=db,
            enrollment_id=enrollment_id,
            user=current_user,
            target_stage_id=req.target_stage_id,
            variance_reason=req.variance_reason,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/enrollments/{enrollment_id}/milestones/{milestone_id}/complete",
    response_model=PatientPathwayEnrollmentResponse,
    summary="Mark a pathway milestone as completed",
)
def complete_milestone(
    enrollment_id: str,
    milestone_id: str,
    req: PathwayMilestoneCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN])),
) -> PatientPathwayEnrollmentResponse:
    """Mark a critical or recommended pathway milestone as fulfilled."""
    try:
        return pathway_service.complete_milestone(
            db=db,
            enrollment_id=enrollment_id,
            milestone_id=milestone_id,
            user=current_user,
            notes=req.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/patient/{patient_id}",
    response_model=List[PatientPathwayEnrollmentResponse],
    summary="List pathway enrollments for a patient",
)
def get_patient_pathways(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> List[PatientPathwayEnrollmentResponse]:
    """Retrieve all regional clinical pathway enrollments for a patient."""
    return pathway_service.get_patient_enrollments(db=db, patient_id=patient_id)
