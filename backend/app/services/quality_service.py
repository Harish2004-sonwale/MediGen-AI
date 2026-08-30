"""Business logic service for Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting.

Phase 9.0.14: Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting Engine.
"""

from datetime import datetime, timedelta, timezone

import hashlib
import json
import logging
from typing import Any, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.quality_provider import MockQualityMeasureProvider
from app.ai.task_worker import get_background_task_provider
from app.database.session import SessionLocal
from app.models.care_plan import CarePlan
from app.models.care_task import CareTask
from app.models.discharge import DischargeProtocol
from app.models.encounter import Encounter
from app.models.order import DiagnosticResult
from app.models.patient import Patient
from app.schemas.patient import PatientStatus
from app.models.quality import (

    QualityMeasure,
    QualityMeasureGap,
    QualityMeasureReport,
    QualityMeasureResult,
)
from app.models.user import User
from app.models.vital import VitalTelemetry
from app.schemas.quality import (
    ComplianceStatus,
    GapSeverity,
    GapStatus,
    QualityMeasureGapResponse,
    QualityMeasureGapUpdate,
    QualityMeasureReportCreate,
    QualityMeasureReportResponse,
    QualityMeasureResponse,
    QualityMeasureResultResponse,
    QualityMeasureSummary,
    ReportScope,
)
from app.schemas.task import BackgroundTask, BackgroundTaskType

logger = logging.getLogger("medigen.services.quality")
_provider = MockQualityMeasureProvider()


def _generate_result_id() -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"QMR-{date_str}-{unique_suffix}"


def _generate_gap_id() -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"QMG-{date_str}-{unique_suffix}"


def _generate_report_id() -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"QRP-{date_str}-{unique_suffix}"


def seed_default_measures(db: Session) -> None:
    """Ensure standard clinical quality measures exist in database."""
    count = db.execute(select(func.count(QualityMeasure.id))).scalar() or 0
    if count == 0:
        logger.info("Seeding default CQM quality measure definitions...")
        for m_data in _provider.get_default_measures():
            m = QualityMeasure(
                measure_id=m_data["measure_id"],
                title=m_data["title"],
                description=m_data["description"],
                version=m_data.get("version", "1.0.0"),
                domain=m_data.get("domain", "chronic_disease_management"),
                hedis_mips_reference=m_data.get("hedis_mips_reference"),
                target_compliance_rate=m_data.get("target_compliance_rate", 80.0),
                denominator_criteria_json=m_data.get("denominator_criteria_json"),
                numerator_criteria_json=m_data.get("numerator_criteria_json"),
                exclusion_criteria_json=m_data.get("exclusion_criteria_json"),
                is_active=True,
            )
            db.add(m)
        db.commit()


def get_quality_measures(
    db: Session, domain: Optional[str] = None, is_active: Optional[bool] = None
) -> list[QualityMeasureResponse]:
    """Retrieve all defined quality measures with optional filtering."""
    seed_default_measures(db)
    stmt = select(QualityMeasure)
    if domain:
        stmt = stmt.where(QualityMeasure.domain == domain)
    if is_active is not None:
        stmt = stmt.where(QualityMeasure.is_active == is_active)
    stmt = stmt.order_by(QualityMeasure.id.asc())

    measures = db.execute(stmt).scalars().all()
    return [QualityMeasureResponse.model_validate(m) for m in measures]


def get_quality_measure_by_id(db: Session, measure_identifier: str | int) -> QualityMeasure:
    """Retrieve a single quality measure by numerical ID or public measure_id."""
    seed_default_measures(db)
    if isinstance(measure_identifier, int) or str(measure_identifier).isdigit():
        stmt = select(QualityMeasure).where(QualityMeasure.id == int(measure_identifier))
    else:
        stmt = select(QualityMeasure).where(QualityMeasure.measure_id == str(measure_identifier))

    m = db.execute(stmt).scalar_one_or_none()
    if not m:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quality measure '{measure_identifier}' not found.",
        )
    return m


def _gather_patient_clinical_data(db: Session, patient_id: int) -> dict[str, Any]:
    """Extract clinical entities for deterministic measure evaluation."""
    # 1. Diagnoses from encounters
    encounters = db.execute(
        select(Encounter).where(Encounter.patient_id == patient_id)
    ).scalars().all()
    diagnoses: list[str] = []
    for enc in encounters:
        if enc.assessment:
            diagnoses.append(enc.assessment)
        if enc.chief_complaint:
            diagnoses.append(enc.chief_complaint)
        if enc.clinical_notes:
            diagnoses.append(enc.clinical_notes)
        if enc.plan:
            diagnoses.append(enc.plan)


    # 2. Diagnostic results
    results = db.execute(
        select(DiagnosticResult).where(DiagnosticResult.patient_id == patient_id)
    ).scalars().all()
    diagnostic_results = [
        {
            "result_id": r.result_id,
            "test_name": r.test_name,
            "numeric_value": r.numeric_value,
            "unit_of_measure": r.unit_of_measure,
            "abnormal_flag": r.abnormal_flag,
            "reviewed_at": r.reviewed_at,
            "resulted_at": r.resulted_at,
        }
        for r in results
    ]

    # 3. Vitals
    vitals_records = db.execute(
        select(VitalTelemetry).where(VitalTelemetry.patient_id == patient_id).order_by(VitalTelemetry.measured_at.asc())
    ).scalars().all()
    vitals = [
        {
            "blood_pressure_systolic": v.systolic_bp,
            "blood_pressure_diastolic": v.diastolic_bp,
            "heart_rate": v.heart_rate,
            "measured_at": v.measured_at,
        }
        for v in vitals_records
    ]


    # 4. Discharge protocols
    discharges = db.execute(
        select(DischargeProtocol).where(DischargeProtocol.patient_id == patient_id)
    ).scalars().all()
    discharge_protocols = [
        {
            "discharge_id": d.discharge_id,
            "status": d.status,
            "medication_reconciliation_json": d.medication_reconciliation_json,
            "signed_off_at": d.signed_off_at,
        }
        for d in discharges
    ]

    # 5. Care plans & tasks
    plans = db.execute(
        select(CarePlan).where(CarePlan.patient_id == patient_id)
    ).scalars().all()
    care_plans = []
    for cp in plans:
        tasks = db.execute(
            select(CareTask).where(CareTask.care_plan_id == cp.id)
        ).scalars().all()
        care_plans.append(
            {
                "plan_id": cp.plan_id,
                "category": cp.category.value if hasattr(cp.category, 'value') else cp.category,
                "status": cp.status.value if hasattr(cp.status, 'value') else cp.status,
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "priority": t.priority.value if hasattr(t.priority, 'value') else t.priority,
                        "is_completed": (t.status.value if hasattr(t.status, 'value') else t.status) in ["completed", "signed_off"],
                    }
                    for t in tasks
                ],
            }
        )

    return {
        "diagnoses": diagnoses,
        "diagnostic_results": diagnostic_results,
        "vitals": vitals,
        "discharge_protocols": discharge_protocols,
        "care_plans": care_plans,
    }



def evaluate_patient_quality_measures(
    db: Session, patient_id: int, calculated_by_user_id: Optional[int] = None
) -> list[QualityMeasureResultResponse]:
    """Evaluate all active quality measures for a single patient and update gaps."""
    seed_default_measures(db)

    # Verify patient exists
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found.",
        )

    measures = db.execute(select(QualityMeasure).where(QualityMeasure.is_active == True)).scalars().all()
    clinical_data = _gather_patient_clinical_data(db, patient_id)
    now = datetime.now(timezone.utc)
    evaluated_responses: list[QualityMeasureResultResponse] = []

    for m in measures:
        eval_result = _provider.evaluate_patient_measure(m.measure_id, clinical_data)

        # Check existing result record
        existing_res = db.execute(
            select(QualityMeasureResult).where(
                QualityMeasureResult.patient_id == patient_id,
                QualityMeasureResult.measure_id == m.id,
            )
        ).scalar_one_or_none()

        if existing_res:
            existing_res.is_eligible = eval_result["is_eligible"]
            existing_res.is_excluded = eval_result["is_excluded"]
            existing_res.exclusion_reason = eval_result.get("exclusion_reason")
            existing_res.is_numerator_compliant = eval_result["is_numerator_compliant"]
            existing_res.compliance_status = eval_result["compliance_status"]
            existing_res.evidence_json = eval_result.get("evidence_json")
            existing_res.gap_reason = eval_result.get("gap_reason")
            existing_res.remediation_action = eval_result.get("remediation_action")
            existing_res.calculated_by_user_id = calculated_by_user_id
            existing_res.calculated_at = now
            res_record = existing_res
        else:
            res_record = QualityMeasureResult(
                result_id=_generate_result_id(),
                measure_id=m.id,
                patient_id=patient_id,
                is_eligible=eval_result["is_eligible"],
                is_excluded=eval_result["is_excluded"],
                exclusion_reason=eval_result.get("exclusion_reason"),
                is_numerator_compliant=eval_result["is_numerator_compliant"],
                compliance_status=eval_result["compliance_status"],
                evidence_json=eval_result.get("evidence_json"),
                gap_reason=eval_result.get("gap_reason"),
                remediation_action=eval_result.get("remediation_action"),
                calculated_by_user_id=calculated_by_user_id,
                calculated_at=now,
            )
            db.add(res_record)
        db.flush()

        # Handle care gap synchronization
        if eval_result["is_eligible"] and not eval_result["is_numerator_compliant"]:
            # Needs open gap
            existing_gap = db.execute(
                select(QualityMeasureGap).where(
                    QualityMeasureGap.patient_id == patient_id,
                    QualityMeasureGap.measure_id == m.id,
                    QualityMeasureGap.status.in_(["open", "in_remediation"]),
                )
            ).scalar_one_or_none()

            if not existing_gap:
                new_gap = QualityMeasureGap(
                    gap_id=_generate_gap_id(),
                    result_id=res_record.id,
                    patient_id=patient_id,
                    measure_id=m.id,
                    gap_type="clinical_measure_gap",
                    severity=eval_result.get("gap_severity", "MODERATE"),
                    status="open",
                    gap_description=eval_result.get("gap_reason") or f"Gap in compliance for {m.title}",
                    missing_data_elements="Diagnostic result / telemetry reading" if eval_result["compliance_status"] == "missing_data" else None,
                    recommended_action=eval_result.get("remediation_action") or "Review clinical history and order required assessments.",
                )
                db.add(new_gap)
        elif eval_result["is_numerator_compliant"]:
            # Resolve existing open gaps
            open_gaps = db.execute(
                select(QualityMeasureGap).where(
                    QualityMeasureGap.patient_id == patient_id,
                    QualityMeasureGap.measure_id == m.id,
                    QualityMeasureGap.status.in_(["open", "in_remediation"]),
                )
            ).scalars().all()
            for og in open_gaps:
                og.status = "resolved"
                og.resolved_at = now

        db.commit()
        db.refresh(res_record)

        resp = QualityMeasureResultResponse.model_validate(res_record)
        resp.measure_code = m.measure_id
        resp.measure_title = m.title
        resp.patient_identifier = patient.patient_id
        resp.patient_name = f"{patient.first_name} {patient.last_name}"
        evaluated_responses.append(resp)

    return evaluated_responses


def list_patient_quality_results(db: Session, patient_id: int) -> list[QualityMeasureResultResponse]:
    """List quality results for a patient, auto-evaluating if not evaluated yet."""
    seed_default_measures(db)
    results = db.execute(
        select(QualityMeasureResult).where(QualityMeasureResult.patient_id == patient_id).order_by(QualityMeasureResult.measure_id.asc())
    ).scalars().all()

    if not results:
        return evaluate_patient_quality_measures(db, patient_id)

    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    responses = []
    for r in results:
        resp = QualityMeasureResultResponse.model_validate(r)
        if r.measure:
            resp.measure_code = r.measure.measure_id
            resp.measure_title = r.measure.title
        if patient:
            resp.patient_identifier = patient.patient_id
            resp.patient_name = f"{patient.first_name} {patient.last_name}"
        responses.append(resp)
    return responses


def list_quality_gaps(
    db: Session,
    status_filter: Optional[str] = None,
    severity: Optional[str] = None,
    patient_id: Optional[int] = None,
) -> list[QualityMeasureGapResponse]:
    """List gaps in care across population with filtering."""
    seed_default_measures(db)
    stmt = select(QualityMeasureGap)
    if status_filter:
        stmt = stmt.where(QualityMeasureGap.status == status_filter)
    if severity:
        stmt = stmt.where(QualityMeasureGap.severity == severity)
    if patient_id:
        stmt = stmt.where(QualityMeasureGap.patient_id == patient_id)
    stmt = stmt.order_by(QualityMeasureGap.created_at.desc())

    gaps = db.execute(stmt).scalars().all()
    responses = []
    for g in gaps:
        resp = QualityMeasureGapResponse.model_validate(g)
        if g.patient:
            resp.patient_identifier = g.patient.patient_id
            resp.patient_name = f"{g.patient.first_name} {g.patient.last_name}"
        if g.measure:
            resp.measure_code = g.measure.measure_id
            resp.measure_title = g.measure.title
        responses.append(resp)
    return responses


def update_quality_gap(
    db: Session, gap_id: str, payload: QualityMeasureGapUpdate
) -> QualityMeasureGapResponse:
    """Update gap status or remediation details."""
    gap = db.execute(select(QualityMeasureGap).where(QualityMeasureGap.gap_id == gap_id)).scalar_one_or_none()
    if not gap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quality gap '{gap_id}' not found.",
        )

    if payload.status is not None:
        gap.status = payload.status.value
        if payload.status.value == "resolved":
            gap.resolved_at = datetime.now(timezone.utc)
    if payload.recommended_action is not None:
        gap.recommended_action = payload.recommended_action
    if payload.due_date is not None:
        gap.due_date = payload.due_date

    db.commit()
    db.refresh(gap)

    resp = QualityMeasureGapResponse.model_validate(gap)
    if gap.patient:
        resp.patient_identifier = gap.patient.patient_id
        resp.patient_name = f"{gap.patient.first_name} {gap.patient.last_name}"
    if gap.measure:
        resp.measure_code = gap.measure.measure_id
        resp.measure_title = gap.measure.title
    return resp


def create_care_task_for_gap(
    db: Session, gap_id: str, current_user_id: Optional[int] = None
) -> QualityMeasureGapResponse:
    """Create a linked CareTask for gap remediation and update gap status."""
    gap = db.execute(select(QualityMeasureGap).where(QualityMeasureGap.gap_id == gap_id)).scalar_one_or_none()
    if not gap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Quality gap '{gap_id}' not found.",
        )

    from app.schemas.care_plan import CarePlanCategory, CarePlanStatus
    from app.schemas.care_task import CareTaskStatus, CareTaskType, TaskPriority

    # Find or create active CarePlan for patient
    care_plan = db.execute(
        select(CarePlan).where(CarePlan.patient_id == gap.patient_id, CarePlan.status == CarePlanStatus.ACTIVE)
    ).scalars().first()

    if not care_plan:
        care_plan = CarePlan(
            plan_id=f"CP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
            patient_id=gap.patient_id,
            author_user_id=current_user_id,
            category=CarePlanCategory.CHRONIC_DISEASE_MANAGEMENT,
            title=f"Quality Remediation Plan ({gap.measure.title if gap.measure else 'CQM'})",
            description="Targeted clinical care plan for quality measure remediation and compliance.",
            status=CarePlanStatus.ACTIVE,
            goals_json=[{"goal_id": "G-01", "description": "Close clinical quality gaps and achieve HEDIS compliance", "target_date": None}],
        )

        db.add(care_plan)
        db.flush()

    task_priority = TaskPriority.URGENT if gap.severity in ["HIGH", "CRITICAL"] else TaskPriority.ROUTINE
    due_dt = gap.due_date or (datetime.now(timezone.utc) + timedelta(days=14))
    care_task = CareTask(
        task_id=f"TASK-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
        care_plan_id=care_plan.id,
        patient_id=gap.patient_id,
        title=f"CQM Remediation: {gap.recommended_action[:200]}",
        instructions=gap.recommended_action,
        task_type=CareTaskType.GENERAL_TASK,
        priority=task_priority,
        status=CareTaskStatus.PENDING,
        due_date=due_dt,
    )
    db.add(care_task)
    db.flush()



    gap.linked_care_task_id = care_task.id
    gap.status = "in_remediation"
    db.commit()
    db.refresh(gap)

    resp = QualityMeasureGapResponse.model_validate(gap)
    if gap.patient:
        resp.patient_identifier = gap.patient.patient_id
        resp.patient_name = f"{gap.patient.first_name} {gap.patient.last_name}"
    if gap.measure:
        resp.measure_code = gap.measure.measure_id
        resp.measure_title = gap.measure.title
    return resp


def generate_compliance_report(
    db: Session, payload: QualityMeasureReportCreate, current_user_id: Optional[int] = None
) -> QualityMeasureReportResponse:
    """Evaluate population-level compliance and generate an immutable audit report."""
    seed_default_measures(db)

    patients = db.execute(select(Patient).where(Patient.status == PatientStatus.ACTIVE)).scalars().all()


    measures = db.execute(select(QualityMeasure).where(QualityMeasure.is_active == True)).scalars().all()

    # Re-evaluate all active patients
    for p in patients:
        evaluate_patient_quality_measures(db, p.id, calculated_by_user_id=current_user_id)

    now = datetime.now(timezone.utc)
    p_start = payload.measurement_period_start or datetime(now.year, 1, 1, tzinfo=timezone.utc)
    p_end = payload.measurement_period_end or now

    total_eligible = 0
    total_compliant = 0
    measure_summaries: list[dict[str, Any]] = []

    for m in measures:
        all_m_results = db.execute(
            select(QualityMeasureResult).where(QualityMeasureResult.measure_id == m.id)
        ).scalars().all()

        m_eligible = sum(1 for r in all_m_results if r.is_eligible and not r.is_excluded)
        m_compliant = sum(1 for r in all_m_results if r.is_eligible and not r.is_excluded and r.is_numerator_compliant)
        m_excluded = sum(1 for r in all_m_results if r.is_excluded)

        rate = round((m_compliant / m_eligible * 100.0), 1) if m_eligible > 0 else 100.0
        benchmark_met = rate >= m.target_compliance_rate

        total_eligible += m_eligible
        total_compliant += m_compliant

        measure_summaries.append(
            {
                "measure_code": m.measure_id,
                "measure_title": m.title,
                "domain": m.domain,
                "eligible_count": m_eligible,
                "numerator_count": m_compliant,
                "excluded_count": m_excluded,
                "compliance_rate": rate,
                "target_rate": m.target_compliance_rate,
                "benchmark_met": benchmark_met,
            }
        )

    overall_rate = round((total_compliant / total_eligible * 100.0), 1) if total_eligible > 0 else 100.0

    audit_metadata = {
        "calculated_by_user_id": current_user_id,
        "calculation_timestamp": now.isoformat(),
        "total_active_patients_audited": len(patients),
        "total_measures_evaluated": len(measures),
        "provenance_hash": hashlib.sha256(json.dumps(measure_summaries, sort_keys=True).encode()).hexdigest(),
    }

    report = QualityMeasureReport(
        report_id=_generate_report_id(),
        title=payload.title or f"Clinical Quality & HEDIS/MIPS Compliance Report ({now.strftime('%B %Y')})",
        reporting_period_start=p_start,
        reporting_period_end=p_end,
        report_scope=payload.report_scope.value,
        total_eligible_population=total_eligible,
        total_numerator_compliant=total_compliant,
        overall_performance_rate=overall_rate,
        measure_summaries_json=measure_summaries,
        audit_metadata_json=audit_metadata,
        generated_by_user_id=current_user_id,
        generated_at=now,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    resp = QualityMeasureReportResponse.model_validate(report)
    if report.generated_by_user:
        resp.generated_by_user_name = report.generated_by_user.name
    return resp


def list_compliance_reports(db: Session, limit: int = 50) -> list[QualityMeasureReportResponse]:
    """Retrieve historical compliance audit reports."""
    reports = db.execute(
        select(QualityMeasureReport).order_by(QualityMeasureReport.generated_at.desc()).limit(limit)
    ).scalars().all()

    responses = []
    for r in reports:
        resp = QualityMeasureReportResponse.model_validate(r)
        if r.generated_by_user:
            resp.generated_by_user_name = r.generated_by_user.name
        responses.append(resp)
    return responses


def get_compliance_report_by_id(db: Session, report_identifier: str | int) -> QualityMeasureReport:
    """Retrieve compliance audit report by numeric ID or public report_id."""
    if isinstance(report_identifier, int) or str(report_identifier).isdigit():
        stmt = select(QualityMeasureReport).where(QualityMeasureReport.id == int(report_identifier))
    else:
        stmt = select(QualityMeasureReport).where(QualityMeasureReport.report_id == str(report_identifier))

    r = db.execute(stmt).scalar_one_or_none()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance report '{report_identifier}' not found.",
        )
    return r


# ==============================================================================
# ASYNCHRONOUS BACKGROUND WORKER HANDLERS
# ==============================================================================

def execute_quality_calculation_job(patient_id: Optional[int] = None, user_id: Optional[int] = None) -> dict[str, Any]:
    """Background worker job for patient or population quality calculation."""
    db = SessionLocal()
    try:
        if patient_id:
            results = evaluate_patient_quality_measures(db, patient_id, calculated_by_user_id=user_id)
            return {
                "status": "completed",
                "patient_id": patient_id,
                "evaluated_measures": len(results),
                "compliant_measures": sum(1 for r in results if r.is_numerator_compliant),
            }
        else:
            rep = generate_compliance_report(
                db, QualityMeasureReportCreate(title="Async Background Audit Report"), current_user_id=user_id
            )
            return {
                "status": "completed",
                "report_id": rep.report_id,
                "overall_rate": rep.overall_performance_rate,
                "total_eligible": rep.total_eligible_population,
            }
    except Exception as e:
        logger.exception("Error executing quality measure calculation job: %s", e)
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


def enqueue_quality_calculation_task(
    db: Session, patient_id: Optional[int] = None, user_id: Optional[int] = None
) -> BackgroundTask:
    """Enqueue asynchronous background task for quality calculation."""
    task_provider = get_background_task_provider()
    task = task_provider.submit_task(
        task_type=BackgroundTaskType.QUALITY_MEASURE_CALCULATION,
        fn=execute_quality_calculation_job,
        fn_kwargs={"patient_id": patient_id, "user_id": user_id},
        patient_id=str(patient_id) if patient_id else None,
        created_by_user_id=user_id,
        payload={"patient_id": patient_id, "user_id": user_id},
    )
    return task
