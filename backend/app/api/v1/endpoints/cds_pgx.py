# ==============================================================================
# MediGen AI - Phase 9.0.26: Enterprise CDS Rules, PGx & Order Sets Endpoints
# ==============================================================================

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_current_user, get_db, require_role, require_roles
from app.models.user import User
from app.models.cds_pgx import OrderSetCategory
from app.schemas.cds_pgx import (
    PGxRuleListResponse,
    PGxRuleResponse,
    OrderSetListResponse,
    OrderSetResponse,
    OrderSetExecuteRequest,
    OrderSetExecuteResponse,
    CDSEvaluationRequest,
    CDSEvaluationResponse,
    CDSRuleOverrideRequest,
    CDSRuleOverrideResponse,
)
from app.services.cds_pgx_service import CDSPGxService

router = APIRouter(prefix="/cds-pgx", tags=["CDS Rules, Pharmacogenomics & Order Sets"])


@router.get("/rules", response_model=PGxRuleListResponse)
def list_pgx_rules(
    gene: Optional[str] = Query(None, description="Filter by gene symbol (e.g. CYP2D6)"),
    drug: Optional[str] = Query(None, description="Filter by drug name (e.g. Codeine)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Lists evidence-based CPIC / PharmGKB Pharmacogenomics clinical rules.
    """
    rules = CDSPGxService.list_pgx_rules(db=db, gene_symbol=gene, drug_name=drug)
    return PGxRuleListResponse(total=len(rules), rules=[PGxRuleResponse.model_validate(r) for r in rules])


@router.get("/order-sets", response_model=OrderSetListResponse)
def list_order_sets(
    category: Optional[OrderSetCategory] = Query(None, description="Filter by clinical category"),
    facility_id: Optional[str] = Query(None, description="Filter by facility context"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Lists multidisciplinary evidence-based clinical order sets.
    """
    fac = facility_id or getattr(current_user, "default_facility_id", None) or "FAC-METRO-MAIN"
    order_sets = CDSPGxService.list_order_sets(db=db, category=category, facility_id=fac)
    return OrderSetListResponse(
        total=len(order_sets),
        order_sets=[OrderSetResponse.model_validate(os) for os in order_sets],
    )


@router.get("/order-sets/{order_set_id}", response_model=OrderSetResponse)
def get_order_set(
    order_set_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieves a single clinical order set and its item checklist.
    """
    order_set = CDSPGxService.get_order_set_by_id(db=db, order_set_id=order_set_id)
    if not order_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical order set '{order_set_id}' not found.",
        )
    return OrderSetResponse.model_validate(order_set)


@router.post("/order-sets/{order_set_id}/execute", response_model=OrderSetExecuteResponse)
def execute_order_set(
    order_set_id: str,
    payload: OrderSetExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "healthcare_staff"])),
):
    """
    Executes a clinical order set for a patient, creating discrete orders in the CPOE system.
    """
    facility_id = getattr(current_user, "default_facility_id", None) or "FAC-METRO-MAIN"
    try:
        res = CDSPGxService.execute_order_set(
            db=db,
            order_set_id=order_set_id,
            patient_id=payload.patient_id,
            ordering_provider_id=current_user.id,
            facility_id=facility_id,
            selected_item_ids=payload.selected_item_ids,
            notes=payload.notes,
        )
        return OrderSetExecuteResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/evaluate", response_model=CDSEvaluationResponse)
def evaluate_cds(
    payload: CDSEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Real-time CDS and Pharmacogenomics rule evaluation for a proposed medication order.
    """
    facility_id = getattr(current_user, "default_facility_id", None) or "FAC-METRO-MAIN"
    res = CDSPGxService.evaluate_cds_and_pgx(
        db=db,
        patient_id=payload.patient_id,
        trigger_event=payload.trigger_event,
        proposed_drug_code=payload.proposed_drug_code,
        proposed_drug_name=payload.proposed_drug_name,
        facility_id=facility_id,
    )
    return CDSEvaluationResponse(**res)


@router.post("/override", response_model=CDSRuleOverrideResponse)
def record_cds_override(
    payload: CDSRuleOverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "healthcare_staff"])),
):
    """
    Records clinician rationale for overriding a critical or warning CDS/PGx alert.
    """
    if not payload.override_reason or len(payload.override_reason.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid clinical override rationale must be provided (minimum 5 characters).",
        )

    facility_id = getattr(current_user, "default_facility_id", None) or "FAC-METRO-MAIN"
    res = CDSPGxService.record_cds_override(
        db=db,
        patient_id=payload.patient_id,
        rule_type=payload.rule_type,
        trigger_event=payload.trigger_event,
        severity=payload.severity,
        card_summary=payload.card_summary,
        card_detail=payload.card_detail,
        override_reason=payload.override_reason.strip(),
        clinician_id=current_user.id,
        facility_id=facility_id,
    )
    return CDSRuleOverrideResponse(**res)


@router.get("/audits/{patient_id}")
def list_cds_audits(
    patient_id: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Lists historical CDS and Pharmacogenomic rule evaluation and override audit records.
    """
    audits = CDSPGxService.list_evaluation_audits(db=db, patient_id=patient_id, limit=limit)
    return [
        {
            "audit_id": a.audit_id,
            "patient_id": a.patient_id,
            "facility_id": a.facility_id,
            "rule_type": a.rule_type,
            "trigger_event": a.trigger_event.value,
            "severity": a.severity,
            "card_summary": a.card_summary,
            "card_detail": a.card_detail,
            "is_overridden": a.is_overridden,
            "override_reason": a.override_reason,
            "clinician_id": a.clinician_id,
            "created_at": a.created_at,
        }
        for a in audits
    ]
