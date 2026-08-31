"""Service layer for Computerized Physician Order Entry (CPOE) and Diagnostic Results.

Phase 9.0.13: Computerized Physician Order Entry (CPOE), Diagnostic Order Lifecycle & Closed-Loop Critical Result Tracking.
"""

from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.ai.order_provider import get_order_provider
from app.ai.task_worker import get_background_task_provider
from app.database.session import SessionLocal
from app.models.alert import ClinicalAlert
from app.models.encounter import Encounter
from app.models.order import ClinicalOrder, DiagnosticResult
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.schemas.alert import AlertSeverity, AlertStatus
from app.services.outbox_service import record_outbox_event

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
    DiagnosticResultStatus,
    DiagnosticResultUpdate,
    OrderBundleItem,
    OrderBundleSuggestRequest,
    OrderBundleSuggestResponse,
    OrderCategory,
    OrderPriority,
    OrderStatus,
)
from app.schemas.task import BackgroundTask, BackgroundTaskType

logger = logging.getLogger("medigen.services.orders")


def _generate_order_id() -> str:
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:8].upper()
    return f"ORD-{today_str}-{short_uuid}"


def _generate_result_id() -> str:
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:8].upper()
    return f"RES-{today_str}-{short_uuid}"


def _get_patient(db: Session, patient_id_str: str) -> Patient:
    stmt = select(Patient).where(
        (Patient.patient_id == patient_id_str)
        | (Patient.id == (int(patient_id_str) if patient_id_str.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id_str}' not found.",
        )
    return patient


def _validate_patient_access(current_user: User, patient: Patient) -> None:
    if current_user.role == UserRole.PATIENT:
        if not patient.email or patient.email.strip().lower() != current_user.email.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients may only access their own clinical orders and diagnostic results.",
            )


def _to_order_response(o: ClinicalOrder) -> ClinicalOrderResponse:
    p = o.patient
    return ClinicalOrderResponse(
        id=o.id,
        order_id=o.order_id,
        patient_id=o.patient_id,
        patient_identifier=p.patient_id if p else None,
        patient_name=f"{p.first_name} {p.last_name}" if p else None,
        encounter_id=o.encounter_id,
        ordering_user_id=o.ordering_user_id,
        ordering_user_name=o.ordering_user.name if o.ordering_user else None,
        facility_id=o.facility_id,
        version=o.version if hasattr(o, "version") and o.version else 1,
        order_category=OrderCategory(o.order_category),
        order_type=o.order_type,
        priority=OrderPriority(o.priority),
        status=OrderStatus(o.status),
        clinical_indication=o.clinical_indication,
        specimen_source=o.specimen_source,
        order_details_json=o.order_details_json,
        ai_safety_flags_json=o.ai_safety_flags_json,
        is_ai_suggested=o.is_ai_suggested,
        placed_at=o.placed_at,
        completed_at=o.completed_at,
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


def _to_result_response(r: DiagnosticResult) -> DiagnosticResultResponse:
    p = r.patient
    o = r.order
    return DiagnosticResultResponse(
        id=r.id,
        result_id=r.result_id,
        order_id=r.order_id,
        order_identifier=o.order_id if o else None,
        patient_id=r.patient_id,
        patient_identifier=p.patient_id if p else None,
        patient_name=f"{p.first_name} {p.last_name}" if p else None,
        encounter_id=r.encounter_id,
        test_name=r.test_name,
        test_code_loinc=r.test_code_loinc,
        status=DiagnosticResultStatus(r.status),
        abnormal_flag=AbnormalFlag(r.abnormal_flag),
        findings_summary=r.findings_summary,
        numeric_value=r.numeric_value,
        unit_of_measure=r.unit_of_measure,
        reference_range_low=r.reference_range_low,
        reference_range_high=r.reference_range_high,
        critical_threshold_low=r.critical_threshold_low,
        critical_threshold_high=r.critical_threshold_high,
        structured_components_json=r.structured_components_json,
        reviewed_by_user_id=r.reviewed_by_user_id,
        reviewed_by_user_name=r.reviewed_by_user.name if r.reviewed_by_user else None,
        reviewed_at=r.reviewed_at,
        resulted_at=r.resulted_at,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


# ==============================================================================
# CLINICAL ORDER (CPOE) MANAGEMENT
# ==============================================================================

def create_clinical_order(
    db: Session,
    patient_id_str: str,
    payload: ClinicalOrderCreate,
    current_user: User,
) -> ClinicalOrderResponse:
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only licensed clinical staff may place clinical orders.",
        )

    patient = _get_patient(db, patient_id_str)

    # 1. Check recent orders placed in the last 24h
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_orders = db.execute(
        select(ClinicalOrder)
        .where(ClinicalOrder.patient_id == patient.id, ClinicalOrder.created_at >= cutoff)
    ).scalars().all()
    recent_types = [o.order_type for o in recent_orders]

    # 2. Check patient active conditions
    encs = db.execute(
        select(Encounter).where(Encounter.patient_id == patient.id)
    ).scalars().all()
    conditions = [e.assessment for e in encs if e.assessment] or [e.chief_complaint for e in encs if e.chief_complaint]

    provider = get_order_provider()
    safety_flags = provider.verify_order_safety(
        order_type=payload.order_type,
        order_category=payload.order_category.value,
        recent_order_types=recent_types,
        active_conditions=conditions,
    )

    order_id = _generate_order_id()
    now_ts = datetime.now(timezone.utc)

    order = ClinicalOrder(
        order_id=order_id,
        patient_id=patient.id,
        encounter_id=payload.encounter_id,
        ordering_user_id=current_user.id,
        facility_id=patient.facility_id or "FAC-001",
        version=1,
        order_category=payload.order_category.value,
        order_type=payload.order_type,
        priority=payload.priority.value,
        status="placed",
        clinical_indication=payload.clinical_indication,
        specimen_source=payload.specimen_source,
        order_details_json=payload.order_details,
        ai_safety_flags_json=safety_flags,
        is_ai_suggested=False,
        placed_at=now_ts,
        created_at=now_ts,
        updated_at=now_ts,
    )
    db.add(order)
    record_outbox_event(
        db=db,
        event_type="ORDER_CREATED",
        aggregate_type="ORDER",
        aggregate_id=order_id,
        payload={
            "order_id": order_id,
            "patient_id": patient.patient_id,
            "order_type": payload.order_type,
            "priority": payload.priority.value,
            "status": "placed",
        },
        facility_id=order.facility_id,
    )
    db.commit()
    db.refresh(order)

    logger.info("Placed clinical order %s (type=%s) for patient %s by user %s", order_id, payload.order_type, patient.patient_id, current_user.id)
    return _to_order_response(order)


def suggest_order_bundle(
    db: Session,
    patient_id_str: str,
    payload: OrderBundleSuggestRequest,
    current_user: User,
) -> OrderBundleSuggestResponse:
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff may request AI order bundle suggestions.",
        )

    patient = _get_patient(db, patient_id_str)
    encs = db.execute(
        select(Encounter).where(Encounter.patient_id == patient.id)
    ).scalars().all()
    diagnoses = [e.assessment for e in encs if e.assessment] or [e.chief_complaint for e in encs if e.chief_complaint]

    provider = get_order_provider()
    bundle = provider.suggest_order_bundle(
        protocol_name=payload.clinical_protocol,
        indication=payload.custom_indication,
        diagnoses=diagnoses,
    )

    suggested_items = [
        OrderBundleItem(
            order_category=OrderCategory(item["order_category"]),
            order_type=item["order_type"],
            priority=OrderPriority(item["priority"]),
            clinical_indication=item["clinical_indication"],
            specimen_source=item.get("specimen_source"),
            order_details=item.get("order_details"),
        )
        for item in bundle["suggested_orders"]
    ]

    return OrderBundleSuggestResponse(
        protocol_name=bundle["protocol_name"],
        clinical_rationale=bundle["clinical_rationale"],
        suggested_orders=suggested_items,
        pre_order_safety_warnings=bundle["pre_order_safety_warnings"],
    )


def list_patient_orders(
    db: Session,
    patient_id_str: str,
    current_user: User,
    status_filter: Optional[OrderStatus] = None,
    category_filter: Optional[OrderCategory] = None,
) -> ClinicalOrderListResponse:
    patient = _get_patient(db, patient_id_str)
    _validate_patient_access(current_user, patient)

    stmt = select(ClinicalOrder).where(ClinicalOrder.patient_id == patient.id)
    if status_filter:
        stmt = stmt.where(ClinicalOrder.status == status_filter.value)
    if category_filter:
        stmt = stmt.where(ClinicalOrder.order_category == category_filter.value)
    stmt = stmt.order_by(ClinicalOrder.created_at.desc())

    items = db.execute(stmt).scalars().all()
    return ClinicalOrderListResponse(
        items=[_to_order_response(o) for o in items],
        total=len(items),
    )


def get_clinical_order(db: Session, order_id_str: str, current_user: User) -> ClinicalOrderResponse:
    stmt = select(ClinicalOrder).where(
        (ClinicalOrder.order_id == order_id_str)
        | (ClinicalOrder.id == (int(order_id_str) if order_id_str.isdigit() else -1))
    )
    order = db.execute(stmt).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical order '{order_id_str}' not found.",
        )
    _validate_patient_access(current_user, order.patient)
    return _to_order_response(order)


def update_clinical_order(
    db: Session,
    order_id_str: str,
    payload: ClinicalOrderUpdate,
    current_user: User,
) -> ClinicalOrderResponse:
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff may modify clinical orders.",
        )

    stmt = select(ClinicalOrder).where(
        (ClinicalOrder.order_id == order_id_str)
        | (ClinicalOrder.id == (int(order_id_str) if order_id_str.isdigit() else -1))
    )
    order = db.execute(stmt).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical order '{order_id_str}' not found.",
        )

    # Optimistic locking check
    if payload.version is not None:
        current_version = order.version if hasattr(order, "version") and order.version else 1
        if current_version != payload.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Conflict: Clinical order '{order_id_str}' has been modified by another user session. "
                    f"Current version is {current_version}, provided version is {payload.version}."
                ),
            )

    if payload.priority is not None:
        order.priority = payload.priority.value
    if payload.clinical_indication is not None:
        order.clinical_indication = payload.clinical_indication
    if payload.specimen_source is not None:
        order.specimen_source = payload.specimen_source
    if payload.order_details is not None:
        order.order_details_json = payload.order_details
    if payload.status is not None:
        order.status = payload.status.value
        if payload.status == OrderStatus.COMPLETED and not order.completed_at:
            order.completed_at = datetime.now(timezone.utc)

    order.version = (order.version if hasattr(order, "version") and order.version else 1) + 1
    order.updated_at = datetime.now(timezone.utc)

    record_outbox_event(
        db=db,
        event_type="ORDER_UPDATED",
        aggregate_type="ORDER",
        aggregate_id=order.order_id,
        payload={
            "order_id": order.order_id,
            "status": order.status,
            "priority": order.priority,
            "version": order.version,
        },
        facility_id=order.facility_id,
    )
    db.commit()
    db.refresh(order)
    return _to_order_response(order)


# ==============================================================================
# DIAGNOSTIC RESULT & CLOSED-LOOP NOTIFICATION MANAGEMENT
# ==============================================================================

def record_diagnostic_result(
    db: Session,
    order_id_str: str,
    payload: DiagnosticResultCreate,
    current_user: User,
) -> DiagnosticResultResponse:
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff may record diagnostic results.",
        )

    stmt = select(ClinicalOrder).where(
        (ClinicalOrder.order_id == order_id_str)
        | (ClinicalOrder.id == (int(order_id_str) if order_id_str.isdigit() else -1))
    )
    order = db.execute(stmt).scalar_one_or_none()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical order '{order_id_str}' not found.",
        )

    provider = get_order_provider()
    evaluated_flag = provider.evaluate_panic_threshold(
        test_name=payload.test_name,
        numeric_value=payload.numeric_value,
        ref_low=payload.reference_range_low,
        ref_high=payload.reference_range_high,
        crit_low=payload.critical_threshold_low,
        crit_high=payload.critical_threshold_high,
    )

    # Use explicitly provided abnormal flag if non-normal, otherwise use evaluated flag
    final_abnormal_flag = payload.abnormal_flag.value if payload.abnormal_flag != AbnormalFlag.NORMAL else evaluated_flag

    result_id = _generate_result_id()
    now_ts = datetime.now(timezone.utc)

    res = DiagnosticResult(
        result_id=result_id,
        order_id=order.id,
        patient_id=order.patient_id,
        encounter_id=payload.encounter_id or order.encounter_id,
        test_name=payload.test_name,
        test_code_loinc=payload.test_code_loinc,
        status=payload.status.value,
        abnormal_flag=final_abnormal_flag,
        findings_summary=payload.findings_summary,
        numeric_value=payload.numeric_value,
        unit_of_measure=payload.unit_of_measure,
        reference_range_low=payload.reference_range_low,
        reference_range_high=payload.reference_range_high,
        critical_threshold_low=payload.critical_threshold_low,
        critical_threshold_high=payload.critical_threshold_high,
        structured_components_json=payload.structured_components,
        resulted_at=now_ts,
        created_at=now_ts,
        updated_at=now_ts,
    )
    db.add(res)

    # If panic critical, trigger an immediate ClinicalAlert
    if final_abnormal_flag == "panic_critical":
        alert_id = f"ALT-{now_ts.strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        crit_alert = ClinicalAlert(
            alert_id=alert_id,
            patient_id=order.patient_id,
            encounter_id=order.encounter_id,
            alert_type="CRITICAL_LAB",
            severity=AlertSeverity.CRITICAL,
            title=f"PANIC CRITICAL LAB: {payload.test_name} = {payload.numeric_value} {payload.unit_of_measure or ''}",
            explanation=f"Critical threshold exceeded for test '{payload.test_name}'. Immediate clinician evaluation and closed-loop signoff required.",
            status=AlertStatus.ACTIVE,
            parameters_json={
                "test_name": payload.test_name,
                "numeric_value": payload.numeric_value,
                "unit_of_measure": payload.unit_of_measure,
                "result_id": result_id,
                "order_id": order.order_id,
            },
            created_at=now_ts,
            last_triggered_at=now_ts,
        )
        db.add(crit_alert)

        logger.warning("Triggered critical panic lab alert %s for patient %s (test=%s)", alert_id, order.patient.patient_id, payload.test_name)

    # Update order status to completed

    order.status = "completed"
    order.completed_at = now_ts
    order.updated_at = now_ts

    db.commit()
    db.refresh(res)
    logger.info("Recorded diagnostic result %s for order %s (flag=%s)", result_id, order.order_id, final_abnormal_flag)
    return _to_result_response(res)


def list_patient_diagnostic_results(
    db: Session,
    patient_id_str: str,
    current_user: User,
    flag_filter: Optional[AbnormalFlag] = None,
) -> DiagnosticResultListResponse:
    patient = _get_patient(db, patient_id_str)
    _validate_patient_access(current_user, patient)

    stmt = select(DiagnosticResult).where(DiagnosticResult.patient_id == patient.id)
    if flag_filter:
        stmt = stmt.where(DiagnosticResult.abnormal_flag == flag_filter.value)
    stmt = stmt.order_by(DiagnosticResult.resulted_at.desc())

    items = db.execute(stmt).scalars().all()
    return DiagnosticResultListResponse(
        items=[_to_result_response(r) for r in items],
        total=len(items),
    )


def get_diagnostic_result(db: Session, result_id_str: str, current_user: User) -> DiagnosticResultResponse:
    stmt = select(DiagnosticResult).where(
        (DiagnosticResult.result_id == result_id_str)
        | (DiagnosticResult.id == (int(result_id_str) if result_id_str.isdigit() else -1))
    )
    res = db.execute(stmt).scalar_one_or_none()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic result '{result_id_str}' not found.",
        )
    _validate_patient_access(current_user, res.patient)
    return _to_result_response(res)


def review_diagnostic_result(
    db: Session,
    result_id_str: str,
    payload: DiagnosticResultReviewRequest,
    current_user: User,
) -> DiagnosticResultResponse:
    """Clinician closed-loop review and signoff of diagnostic findings."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff may sign off diagnostic results.",
        )

    stmt = select(DiagnosticResult).where(
        (DiagnosticResult.result_id == result_id_str)
        | (DiagnosticResult.id == (int(result_id_str) if result_id_str.isdigit() else -1))
    )
    res = db.execute(stmt).scalar_one_or_none()
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic result '{result_id_str}' not found.",
        )

    now_ts = datetime.now(timezone.utc)
    res.reviewed_by_user_id = current_user.id
    res.reviewed_at = now_ts
    if payload.review_notes:
        res.findings_summary += f"\n\nClinician Review Signoff: {payload.review_notes}"
    res.updated_at = now_ts

    db.commit()
    db.refresh(res)
    logger.info("Diagnostic result %s reviewed and signed off by user %s", res.result_id, current_user.id)
    return _to_result_response(res)


# ==============================================================================
# ASYNCHRONOUS WORKER JOBS & ENQUEUE HELPERS
# ==============================================================================

def execute_order_verification_job(patient_id: str, order_id: str) -> dict[str, Any]:
    """Background task target to re-verify safety and redundancy of clinical orders."""
    db = SessionLocal()
    try:
        stmt = select(ClinicalOrder).where(ClinicalOrder.order_id == order_id)
        order = db.execute(stmt).scalar_one_or_none()
        if not order:
            return {"status": "failed", "detail": f"Order {order_id} not found."}

        patient = order.patient
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent_orders = db.execute(
            select(ClinicalOrder)
            .where(ClinicalOrder.patient_id == patient.id, ClinicalOrder.created_at >= cutoff, ClinicalOrder.id != order.id)
        ).scalars().all()
        recent_types = [o.order_type for o in recent_orders]

        encs = db.execute(select(Encounter).where(Encounter.patient_id == patient.id)).scalars().all()
        conditions = [e.assessment for e in encs if e.assessment] or [e.chief_complaint for e in encs if e.chief_complaint]

        provider = get_order_provider()
        flags = provider.verify_order_safety(order.order_type, order.order_category, recent_types, conditions)

        order.ai_safety_flags_json = flags
        order.updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": "completed", "order_id": order_id, "flags_count": len(flags)}
    finally:
        db.close()


def execute_result_ingestion_job(
    order_id: str,
    test_name: str,
    numeric_value: Optional[float],
    unit_of_measure: Optional[str] = None,
    findings_summary: Optional[str] = None,
) -> dict[str, Any]:
    """Background task target to ingest structured diagnostic results."""
    db = SessionLocal()
    try:
        dummy_user = db.execute(select(User).where(User.role == UserRole.DOCTOR)).scalars().first()
        if not dummy_user:
            dummy_user = db.execute(select(User)).scalars().first()

        create_req = DiagnosticResultCreate(
            test_name=test_name,
            numeric_value=numeric_value,
            unit_of_measure=unit_of_measure,
            findings_summary=findings_summary or f"Laboratory finding for {test_name}.",
        )
        resp = record_diagnostic_result(db, order_id, create_req, dummy_user)
        return {"status": "completed", "result_id": resp.result_id, "abnormal_flag": resp.abnormal_flag.value}
    finally:
        db.close()


def enqueue_order_verification(patient_id: str, order_id: str, current_user: User) -> BackgroundTask:
    task_provider = get_background_task_provider()
    task = task_provider.submit_task(
        task_type=BackgroundTaskType.ORDER_VERIFICATION,
        fn=execute_order_verification_job,
        fn_kwargs={"patient_id": patient_id, "order_id": order_id},
        created_by_user_id=current_user.id,
        payload={"patient_id": patient_id, "order_id": order_id},
    )
    return task


def enqueue_result_ingestion(
    order_id: str,
    test_name: str,
    numeric_value: Optional[float],
    unit_of_measure: Optional[str],
    findings_summary: Optional[str],
    current_user: User,
) -> BackgroundTask:
    task_provider = get_background_task_provider()
    task = task_provider.submit_task(
        task_type=BackgroundTaskType.RESULT_INGESTION,
        fn=execute_result_ingestion_job,
        fn_kwargs={
            "order_id": order_id,
            "test_name": test_name,
            "numeric_value": numeric_value,
            "unit_of_measure": unit_of_measure,
            "findings_summary": findings_summary,
        },
        created_by_user_id=current_user.id,
        payload={"order_id": order_id, "test_name": test_name},
    )
    return task
