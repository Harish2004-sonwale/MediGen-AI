from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.database import get_db
from app.models.user import User
from app.schemas.encounter import (
    EncounterCreate,
    EncounterListResponse,
    EncounterResponse,
    EncounterStatus,
    EncounterUpdate,
)
from app.schemas.user import UserRole
from app.services.encounter_service import (
    create_encounter,
    get_encounter_by_encounter_id,
    list_patient_encounters,
    update_encounter,
)

router = APIRouter(tags=["Medical Records & Encounters"])

CLINICAL_ACCESS_ROLES = (UserRole.ADMIN, UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF)


@router.post(
    "/patients/{patient_id}/encounters",
    response_model=EncounterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new clinical encounter for a patient",
)
def create_patient_encounter(
    patient_id: str,
    encounter_in: EncounterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*CLINICAL_ACCESS_ROLES)),
) -> EncounterResponse:
    """Record a clinician-authored clinical encounter for an existing patient."""
    try:
        encounter = create_encounter(
            db,
            patient_public_id=patient_id,
            encounter_in=encounter_in,
            attending_user_id=current_user.id,
        )
        return EncounterResponse.from_orm_model(encounter)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/patients/{patient_id}/encounters",
    response_model=EncounterListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all clinical encounters for a patient",
)
def get_patient_encounters(
    patient_id: str,
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    status_filter: EncounterStatus | None = Query(None, alias="status", description="Filter by encounter status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*CLINICAL_ACCESS_ROLES)),
) -> EncounterListResponse:
    """Retrieve chronological clinical encounters recorded for a patient."""
    try:
        encounters, total = list_patient_encounters(
            db,
            patient_public_id=patient_id,
            page=page,
            size=size,
            status=status_filter,
        )
        items = [EncounterResponse.from_orm_model(enc) for enc in encounters]
        return EncounterListResponse.create(items=items, total=total, page=page, size=size)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/encounters/{encounter_id}",
    response_model=EncounterResponse,
    status_code=status.HTTP_200_OK,
    summary="Get clinical encounter details",
)
def get_encounter(
    encounter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*CLINICAL_ACCESS_ROLES)),
) -> EncounterResponse:
    """Retrieve clinical encounter details by public encounter identifier."""
    encounter = get_encounter_by_encounter_id(db, encounter_id=encounter_id)
    if not encounter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical encounter with identifier '{encounter_id}' was not found",
        )
    return EncounterResponse.from_orm_model(encounter)


@router.patch(
    "/encounters/{encounter_id}",
    response_model=EncounterResponse,
    status_code=status.HTTP_200_OK,
    summary="Update clinical encounter record",
)
def update_patient_encounter(
    encounter_id: str,
    encounter_in: EncounterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*CLINICAL_ACCESS_ROLES)),
) -> EncounterResponse:
    """Update clinician notes, assessment, plan, or status for an encounter."""
    encounter = get_encounter_by_encounter_id(db, encounter_id=encounter_id)
    if not encounter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical encounter with identifier '{encounter_id}' was not found",
        )
    updated = update_encounter(db, encounter=encounter, encounter_in=encounter_in)
    return EncounterResponse.from_orm_model(updated)
