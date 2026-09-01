"""FastAPI Endpoints for Federated Enterprise Master Patient Index (EMPI) & Identity Resolution."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_roles
from app.models.user import User, UserRole
from app.schemas.empi import (
    EMPILinkRequest,
    EMPILinkResponse,
    EMPIMatchCandidatesResponse,
    EMPIMatchReviewActionRequest,
    EMPIMatchReviewItem,
    EMPIMatchReviewListResponse,
    EMPIMergeRequest,
    EMPIMergeResponse,
    EMPISplitRequest,
    EMPIUnlinkRequest,
    FHIRPatientMatchRequest,
)
from app.services.empi_service import empi_service

router = APIRouter(prefix="/empi", tags=["Enterprise Master Patient Index (EMPI)"])


@router.get(
    "/match/candidates/{patient_id}",
    response_model=EMPIMatchCandidatesResponse,
    summary="Find candidate matching patient identities across facilities",
)
def find_match_candidates(
    patient_id: str,
    threshold: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> EMPIMatchCandidatesResponse:
    """Evaluate deterministic and probabilistic features to identify potential duplicate patient records."""
    try:
        return empi_service.find_candidate_matches(
            db=db,
            patient_id=patient_id,
            threshold=threshold,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/link",
    response_model=EMPILinkResponse,
    summary="Link a patient record to an Enterprise Master Patient identity",
)
def link_patient(
    req: EMPILinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN, UserRole.HEALTHCARE_STAFF])),
) -> EMPILinkResponse:
    """Manually link a facility-scoped patient to a master enterprise golden record."""
    try:
        if not req.enterprise_id:
            # If enterprise_id not provided, target_patient_id must be provided to find or create identity
            if not req.target_patient_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Either enterprise_id or target_patient_id must be supplied for linking.",
                )
            from app.models.patient import Patient
            target_p = db.query(Patient).filter(Patient.patient_id == req.target_patient_id).first()
            if not target_p:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target patient '{req.target_patient_id}' not found.")
            target_ident = empi_service.get_or_create_enterprise_identity(db, target_p, current_user.id)
            target_euid = target_ident.enterprise_id
        else:
            target_euid = req.enterprise_id

        return empi_service.link_patient_record(
            db=db,
            enterprise_id=target_euid,
            patient_id=req.patient_id,
            user_id=current_user.id,
            link_type=req.link_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/unlink",
    summary="Unlink a patient record from its Enterprise identity",
)
def unlink_patient(
    req: EMPIUnlinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.DOCTOR])),
) -> Dict[str, Any]:
    """Unlink a patient from their enterprise identity."""
    success = empi_service.unlink_patient_record(
        db=db,
        patient_id=req.patient_id,
        user_id=current_user.id,
        reason=req.reason,
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active link found for patient.")
    return {"status": "success", "message": f"Patient '{req.patient_id}' unlinked successfully."}


@router.post(
    "/merge",
    response_model=EMPIMergeResponse,
    summary="Merge two patient identities under a single surviving golden record",
)
def merge_patients(
    req: EMPIMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.DOCTOR])),
) -> EMPIMergeResponse:
    """Execute duplicate patient merge with full audit trail and identity lineage preservation."""
    try:
        return empi_service.merge_patient_identities(
            db=db,
            target_patient_id=req.target_patient_id,
            source_patient_id=req.source_patient_id,
            user_id=current_user.id,
            reason=req.merge_reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/split",
    summary="Revert a previous patient merge operation",
)
def split_patient(
    req: EMPISplitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN])),
) -> Dict[str, Any]:
    """Revert a false-positive merge record and split identities."""
    try:
        success = empi_service.split_patient_identity(
            db=db,
            merge_id=req.merge_id,
            user_id=current_user.id,
            reason=req.split_reason,
        )
        return {"status": "success", "message": f"Merge '{req.merge_id}' reverted and identities split successfully."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/reviews",
    response_model=EMPIMatchReviewListResponse,
    summary="List queued manual duplicate candidate reviews",
)
def list_reviews(
    review_status: Optional[str] = Query("pending_review", alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> EMPIMatchReviewListResponse:
    """Retrieve items in the manual duplicate candidate review queue."""
    items = empi_service.list_match_reviews(db=db, status=review_status)
    return EMPIMatchReviewListResponse(total=len(items), items=items)


@router.post(
    "/reviews/{review_id}/action",
    summary="Approve or reject a queued candidate match review",
)
def resolve_review(
    review_id: str,
    req: EMPIMatchReviewActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.DOCTOR])),
) -> Dict[str, Any]:
    """Take action (approve_link, approve_merge, reject_distinct) on a manual match review item."""
    try:
        empi_service.resolve_match_review(
            db=db,
            review_id=review_id,
            action=req.action,
            user_id=current_user.id,
            notes=req.notes,
        )
        return {"status": "success", "message": f"Review '{review_id}' resolved with action '{req.action}'."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/fhir/$match",
    summary="HL7 FHIR standard $match patient identity resolution operation",
)
def fhir_patient_match(
    req: FHIRPatientMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """FHIR R4 $match operation returning a Bundle of matched Patient resources with search score extensions."""
    # Extract names from FHIR patient resource
    resource = req.resource or {}
    names = resource.get("name", [])
    first_name = ""
    last_name = ""
    if names and isinstance(names, list) and len(names) > 0:
        n = names[0]
        givens = n.get("given", [])
        first_name = givens[0] if givens else ""
        last_name = n.get("family", "")

    # Dummy search candidate match bundle
    from app.models.patient import Patient
    query = db.query(Patient)
    if last_name:
        query = query.filter(Patient.last_name.ilike(f"%{last_name}%"))
    matches = query.limit(req.count).all()

    bundle_entries = []
    for p in matches:
        bundle_entries.append({
            "fullUrl": f"urn:uuid:{p.patient_id}",
            "resource": {
                "resourceType": "Patient",
                "id": p.patient_id,
                "name": [{"family": p.last_name, "given": [p.first_name]}],
                "gender": str(p.gender.value) if hasattr(p.gender, "value") else str(p.gender),
                "birthDate": str(p.date_of_birth) if p.date_of_birth else None,
            },
            "search": {
                "mode": "match",
                "score": 0.95 if p.last_name.lower() == last_name.lower() else 0.75,
                "extension": [
                    {
                        "url": "http://hl7.org/fhir/StructureDefinition/match-grade",
                        "valueCode": "certain" if p.last_name.lower() == last_name.lower() else "probable",
                    }
                ],
            },
        })

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(bundle_entries),
        "entry": bundle_entries,
    }
