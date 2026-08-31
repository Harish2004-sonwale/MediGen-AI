"""API endpoints for Computerized Physician Order Entry (CPOE) and Diagnostic Results.

Phase 9.0.13: Computerized Physician Order Entry (CPOE), Diagnostic Order Lifecycle & Closed-Loop Critical Result Tracking.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.idempotency import (
    check_and_get_cached_idempotency_response,
    store_idempotency_response,
)
from app.database import get_db
from app.models.user import User
from app.schemas.order import (
    AbnormalFlag,
    ClinicalOrderCreate,
    ClinicalOrderListResponse,
    ClinicalOrderResponse,
    ClinicalOrderUpdate,
    DiagnosticResultCreate,
    DiagnosticResultListResponse,
    DiagnosticResultResponse,
    DiagnosticResultReviewRequest,
    OrderBundleSuggestRequest,
    OrderBundleSuggestResponse,
    OrderCategory,
    OrderStatus,
)
from app.schemas.task import BackgroundTaskResponse
from app.services import order_service

router = APIRouter(tags=["Clinical Orders (CPOE) & Diagnostic Results"])


# ==============================================================================
# CLINICAL ORDER (CPOE) ENDPOINTS
# ==============================================================================

@router.post(
    "/patients/{patient_id}/orders",
    response_model=ClinicalOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new clinical order (CPOE)",
)
def place_clinical_order(
    patient_id: str,
    payload: ClinicalOrderCreate,
    response: Response,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalOrderResponse:
    """Place a structured laboratory, imaging, medication, nursing, or consult order with optional idempotency."""
    endpoint_path = f"/patients/{patient_id}/orders"
    if x_idempotency_key and x_idempotency_key.strip():
        cached = check_and_get_cached_idempotency_response(
            db=db,
            idempotency_key=x_idempotency_key.strip(),
            endpoint=endpoint_path,
            request_payload=payload.model_dump(mode="json"),
        )
        if cached is not None:
            status_code, body = cached
            response.status_code = status_code
            response.headers["X-Cache-Lookup"] = "IDEMPOTENT-HIT"
            return ClinicalOrderResponse(**body)

    order_resp = order_service.create_clinical_order(db, patient_id, payload, current_user)

    if x_idempotency_key and x_idempotency_key.strip():
        store_idempotency_response(
            db=db,
            idempotency_key=x_idempotency_key.strip(),
            endpoint=endpoint_path,
            request_payload=payload.model_dump(mode="json"),
            response_code=status.HTTP_201_CREATED,
            response_body=order_resp.model_dump(mode="json"),
            user_id=current_user.id,
            facility_id=order_resp.facility_id,
        )

    return order_resp


@router.post(
    "/patients/{patient_id}/orders/suggest-bundle",
    response_model=OrderBundleSuggestResponse,
    status_code=status.HTTP_200_OK,
    summary="AI-assisted clinical order set bundle suggestion",
)
def suggest_order_bundle(
    patient_id: str,
    payload: OrderBundleSuggestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrderBundleSuggestResponse:
    """Suggest standardized diagnostic bundles (e.g. Sepsis, Chest Pain/ACS, DKA protocols)."""
    return order_service.suggest_order_bundle(db, patient_id, payload, current_user)


@router.get(
    "/patients/{patient_id}/orders",
    response_model=ClinicalOrderListResponse,
    status_code=status.HTTP_200_OK,
    summary="List clinical orders for a patient",
)
def list_patient_orders(
    patient_id: str,
    status_filter: Optional[OrderStatus] = Query(default=None, alias="status"),
    category_filter: Optional[OrderCategory] = Query(default=None, alias="category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalOrderListResponse:
    """Retrieve historical and active clinical orders with optional filtering."""
    return order_service.list_patient_orders(db, patient_id, current_user, status_filter, category_filter)


@router.get(
    "/orders/{order_id}",
    response_model=ClinicalOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve clinical order details",
)
def get_clinical_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalOrderResponse:
    """Retrieve full details, safety flags, and execution status of a clinical order."""
    return order_service.get_clinical_order(db, order_id, current_user)


@router.patch(
    "/orders/{order_id}",
    response_model=ClinicalOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Update clinical order status or configuration",
)
def update_clinical_order(
    order_id: str,
    payload: ClinicalOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalOrderResponse:
    """Update priority, clinical indication, or transition order status."""
    return order_service.update_clinical_order(db, order_id, payload, current_user)


# ==============================================================================
# DIAGNOSTIC RESULT ENDPOINTS
# ==============================================================================

@router.post(
    "/orders/{order_id}/results",
    response_model=DiagnosticResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest/record diagnostic result for an order",
)
def record_diagnostic_result(
    order_id: str,
    payload: DiagnosticResultCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DiagnosticResultResponse:
    """Ingest diagnostic laboratory/imaging result, classify panic thresholds, and complete order."""
    return order_service.record_diagnostic_result(db, order_id, payload, current_user)


@router.get(
    "/patients/{patient_id}/diagnostic-results",
    response_model=DiagnosticResultListResponse,
    status_code=status.HTTP_200_OK,
    summary="List diagnostic results for a patient",
)
def list_patient_diagnostic_results(
    patient_id: str,
    flag_filter: Optional[AbnormalFlag] = Query(default=None, alias="abnormal_flag"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DiagnosticResultListResponse:
    """List historical diagnostic lab and imaging results for a patient."""
    return order_service.list_patient_diagnostic_results(db, patient_id, current_user, flag_filter)


@router.get(
    "/diagnostic-results/{result_id}",
    response_model=DiagnosticResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve diagnostic result details",
)
def get_diagnostic_result(
    result_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DiagnosticResultResponse:
    """Retrieve full diagnostic findings and numeric parameters for a specific test result."""
    return order_service.get_diagnostic_result(db, result_id, current_user)


@router.post(
    "/diagnostic-results/{result_id}/review",
    response_model=DiagnosticResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Clinician review and closed-loop result signoff",
)
def review_diagnostic_result(
    result_id: str,
    payload: DiagnosticResultReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DiagnosticResultResponse:
    """Clinician signs off on lab findings and closed-loop notification acknowledgment."""
    return order_service.review_diagnostic_result(db, result_id, payload, current_user)


# ==============================================================================
# ASYNCHRONOUS BACKGROUND TASK DISPATCH ENDPOINTS
# ==============================================================================

@router.post(
    "/tasks/patients/{patient_id}/orders/{order_id}/verify",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue background clinical order safety re-verification",
)
def enqueue_order_verification(
    patient_id: str,
    order_id: str,
    current_user: User = Depends(get_current_active_user),
) -> BackgroundTaskResponse:
    """Enqueue asynchronous background job to re-evaluate duplicate orders and contraindications."""
    task = order_service.enqueue_order_verification(patient_id, order_id, current_user)
    return BackgroundTaskResponse.model_validate(task)


@router.post(
    "/tasks/orders/{order_id}/results/ingest",
    response_model=BackgroundTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue background diagnostic result processing",
)
def enqueue_result_ingestion(
    order_id: str,
    payload: DiagnosticResultCreate,
    current_user: User = Depends(get_current_active_user),
) -> BackgroundTaskResponse:
    """Enqueue asynchronous background job to process and record incoming lab feed."""
    task = order_service.enqueue_result_ingestion(
        order_id=order_id,
        test_name=payload.test_name,
        numeric_value=payload.numeric_value,
        unit_of_measure=payload.unit_of_measure,
        findings_summary=payload.findings_summary,
        current_user=current_user,
    )
    return BackgroundTaskResponse.model_validate(task)
