"""API Router for Clinical Safety and Decision Support.

Phase 8.9: Longitudinal Clinical Intelligence & Safety Layer.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.safety import ClinicalSafetyReport, SafetyCheckRequest
from app.services.safety_service import evaluate_patient_safety

router = APIRouter(tags=["Clinical Safety"])


@router.post(
    "/patients/{patient_id}/safety/check",
    response_model=ClinicalSafetyReport,
    status_code=status.HTTP_200_OK,
    summary="Run clinical decision support safety evaluation for a patient",
)
def run_safety_check(
    patient_id: str,
    payload: Optional[SafetyCheckRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalSafetyReport:
    """Analyze patient records and optional candidate items for medication duplication, allergy conflicts, drug-drug interactions, and contraindications."""
    try:
        return evaluate_patient_safety(
            db=db,
            patient_id_str=patient_id,
            current_user=current_user,
            request=payload,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc).strip("'"),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
