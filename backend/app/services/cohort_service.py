"""Business logic service for Patient Cohorts, Registries & Clinical Risk Stratification.

Phase 9.0.11: Clinical Cohort Analytics, Patient Registry Management & Longitudinal Risk Stratification.
"""

from datetime import date, datetime, timezone
import logging
from typing import Any, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.ai.risk_provider import get_risk_provider
from app.ai.task_worker import get_background_task_provider
from app.database.session import SessionLocal
from app.models.alert import ClinicalAlert
from app.models.care_plan import CarePlan
from app.models.care_task import CareTask
from app.models.cohort import CohortMembership, PatientCohort
from app.models.encounter import Encounter
from app.models.patient import Patient

from app.models.risk_assessment import ClinicalRiskAssessment
from app.models.user import User, UserRole
from app.models.vital import VitalTelemetry
from app.schemas.cohort import (
    CohortAnalyticsResponse,
    CohortCreate,
    CohortListResponse,
    CohortMembershipResponse,
    CohortResponse,
    CohortType,
    CohortUpdate,
)
from app.schemas.risk_assessment import (
    RiskAssessmentListResponse,
    RiskAssessmentResponse,
    RiskTier,
    RiskType,
)
from app.schemas.task import BackgroundTask, BackgroundTaskType

logger = logging.getLogger("medigen.services.cohort")


def _generate_cohort_id() -> str:
    """Generate unique public cohort identifier (COHORT-YYYYMMDD-XXXXXX)."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"COHORT-{date_str}-{unique_suffix}"


def _generate_assessment_id() -> str:
    """Generate unique public risk assessment identifier (RISK-YYYYMMDD-XXXXXX)."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"RISK-{date_str}-{unique_suffix}"


def _validate_clinical_staff_access(current_user: User) -> None:
    """Ensure current user is clinical staff or administrator."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Population analytics and disease registries require clinical staff or administrator privileges.",
        )


def _validate_patient_risk_access(db: Session, current_user: User, patient: Patient) -> None:
    """Ensure patient only views their own risk records."""
    if current_user.role in (UserRole.ADMIN, UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF):
        return
    if current_user.role == UserRole.PATIENT:
        if current_user.email.lower() != patient.email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot access risk assessments belonging to another patient.",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient privileges to access patient risk assessments.",
    )


# ==============================================================================
# COHORT & REGISTRY CRUD
# ==============================================================================

def create_cohort(
    db: Session,
    cohort_in: CohortCreate,
    current_user: User,
) -> CohortResponse:
    """Create a new patient cohort or disease registry."""
    _validate_clinical_staff_access(current_user)

    now = datetime.now(timezone.utc)
    cohort = PatientCohort(
        cohort_id=_generate_cohort_id(),
        name=cohort_in.name.strip(),
        description=cohort_in.description.strip(),
        cohort_type=cohort_in.cohort_type.value,
        criteria_json=cohort_in.criteria.model_dump(mode="json") if cohort_in.criteria else None,
        is_dynamic=cohort_in.is_dynamic,
        created_by_user_id=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(cohort)
    db.commit()
    db.refresh(cohort)

    # Initial population evaluation if dynamic
    if cohort.is_dynamic and cohort.criteria_json:
        _sync_cohort_membership_criteria(db, cohort)

    logger.info("Created cohort %s ('%s') by user_id=%s", cohort.cohort_id, cohort.name, current_user.id)
    return get_cohort(db, cohort.cohort_id, current_user)


def list_cohorts(
    db: Session,
    current_user: User,
    cohort_type: Optional[str] = None,
) -> CohortListResponse:
    """List all cohorts and disease registries with current membership counts."""
    _validate_clinical_staff_access(current_user)

    stmt = select(PatientCohort).order_by(PatientCohort.created_at.desc())
    if cohort_type:
        stmt = stmt.where(PatientCohort.cohort_type == cohort_type)

    cohorts = db.execute(stmt).scalars().all()
    results: list[CohortResponse] = []

    for c in cohorts:
        member_cnt = db.execute(
            select(func.count(CohortMembership.id)).where(
                CohortMembership.cohort_id == c.id,
                CohortMembership.status == "active",
            )
        ).scalar() or 0

        res = CohortResponse.model_validate(c)
        res.member_count = member_cnt
        results.append(res)

    return CohortListResponse(items=results, total=len(results))


def get_cohort(
    db: Session,
    cohort_id: str,
    current_user: User,
) -> CohortResponse:
    """Retrieve details of a specific cohort."""
    _validate_clinical_staff_access(current_user)

    stmt = select(PatientCohort).where(
        (PatientCohort.cohort_id == cohort_id)
        | (PatientCohort.id == (int(cohort_id) if cohort_id.isdigit() else -1))
    )
    cohort = db.execute(stmt).scalar_one_or_none()
    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient cohort '{cohort_id}' not found.",
        )

    member_cnt = db.execute(
        select(func.count(CohortMembership.id)).where(
            CohortMembership.cohort_id == cohort.id,
            CohortMembership.status == "active",
        )
    ).scalar() or 0

    res = CohortResponse.model_validate(cohort)
    res.member_count = member_cnt
    return res


def update_cohort(
    db: Session,
    cohort_id: str,
    cohort_in: CohortUpdate,
    current_user: User,
) -> CohortResponse:
    """Update details and criteria of a cohort."""
    _validate_clinical_staff_access(current_user)

    stmt = select(PatientCohort).where(
        (PatientCohort.cohort_id == cohort_id)
        | (PatientCohort.id == (int(cohort_id) if cohort_id.isdigit() else -1))
    )
    cohort = db.execute(stmt).scalar_one_or_none()
    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient cohort '{cohort_id}' not found.",
        )

    if cohort_in.name is not None:
        cohort.name = cohort_in.name.strip()
    if cohort_in.description is not None:
        cohort.description = cohort_in.description.strip()
    if cohort_in.cohort_type is not None:
        cohort.cohort_type = cohort_in.cohort_type.value
    if cohort_in.criteria is not None:
        cohort.criteria_json = cohort_in.criteria.model_dump(mode="json")
    if cohort_in.is_dynamic is not None:
        cohort.is_dynamic = cohort_in.is_dynamic

    cohort.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cohort)

    if cohort.is_dynamic and cohort.criteria_json:
        _sync_cohort_membership_criteria(db, cohort)

    logger.info("Updated cohort %s", cohort.cohort_id)
    return get_cohort(db, cohort.cohort_id, current_user)


def delete_cohort(
    db: Session,
    cohort_id: str,
    current_user: User,
) -> dict[str, Any]:
    """Delete a cohort and its memberships (Admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators may delete patient cohorts.",
        )

    stmt = select(PatientCohort).where(
        (PatientCohort.cohort_id == cohort_id)
        | (PatientCohort.id == (int(cohort_id) if cohort_id.isdigit() else -1))
    )
    cohort = db.execute(stmt).scalar_one_or_none()
    if not cohort:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient cohort '{cohort_id}' not found.",
        )

    cid = cohort.cohort_id
    db.delete(cohort)
    db.commit()

    logger.info("Deleted cohort %s by admin user_id=%s", cid, current_user.id)
    return {"message": f"Patient cohort '{cid}' was successfully deleted.", "deleted": True}


# ==============================================================================
# COHORT MEMBERSHIP
# ==============================================================================

def add_cohort_member(
    db: Session,
    cohort_id: str,
    patient_id_str: str,
    notes: Optional[str],
    current_user: User,
) -> CohortMembershipResponse:
    """Manually enroll a patient in a cohort/registry."""
    _validate_clinical_staff_access(current_user)

    cohort = db.execute(
        select(PatientCohort).where(
            (PatientCohort.cohort_id == cohort_id)
            | (PatientCohort.id == (int(cohort_id) if cohort_id.isdigit() else -1))
        )
    ).scalar_one_or_none()
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cohort '{cohort_id}' not found.")

    patient = db.execute(
        select(Patient).where(
            (Patient.patient_id == patient_id_str)
            | (Patient.id == (int(patient_id_str) if patient_id_str.isdigit() else -1))
        )
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id_str}' not found.")

    membership = db.execute(
        select(CohortMembership).where(
            CohortMembership.cohort_id == cohort.id,
            CohortMembership.patient_id == patient.id,
        )
    ).scalar_one_or_none()

    if membership:
        membership.status = "active"
        if notes:
            membership.notes = notes
    else:
        membership = CohortMembership(
            cohort_id=cohort.id,
            patient_id=patient.id,
            status="active",
            notes=notes,
            enrolled_at=datetime.now(timezone.utc),
        )
        db.add(membership)

    db.commit()
    db.refresh(membership)

    return _to_membership_response(db, membership)


def remove_cohort_member(
    db: Session,
    cohort_id: str,
    patient_id_str: str,
    current_user: User,
) -> dict[str, Any]:
    """Remove a patient from a cohort/registry."""
    _validate_clinical_staff_access(current_user)

    cohort = db.execute(
        select(PatientCohort).where(
            (PatientCohort.cohort_id == cohort_id)
            | (PatientCohort.id == (int(cohort_id) if cohort_id.isdigit() else -1))
        )
    ).scalar_one_or_none()
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cohort '{cohort_id}' not found.")

    patient = db.execute(
        select(Patient).where(
            (Patient.patient_id == patient_id_str)
            | (Patient.id == (int(patient_id_str) if patient_id_str.isdigit() else -1))
        )
    ).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id_str}' not found.")

    stmt = delete(CohortMembership).where(
        CohortMembership.cohort_id == cohort.id,
        CohortMembership.patient_id == patient.id,
    )
    db.execute(stmt)
    db.commit()

    return {"message": f"Patient '{patient.patient_id}' removed from cohort '{cohort.cohort_id}'."}


def list_cohort_members(
    db: Session,
    cohort_id: str,
    current_user: User,
) -> list[CohortMembershipResponse]:
    """List all enrolled members in a cohort."""
    _validate_clinical_staff_access(current_user)

    cohort = db.execute(
        select(PatientCohort).where(
            (PatientCohort.cohort_id == cohort_id)
            | (PatientCohort.id == (int(cohort_id) if cohort_id.isdigit() else -1))
        )
    ).scalar_one_or_none()
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cohort '{cohort_id}' not found.")

    memberships = (
        db.execute(
            select(CohortMembership)
            .where(CohortMembership.cohort_id == cohort.id, CohortMembership.status == "active")
            .order_by(CohortMembership.enrolled_at.desc())
        )
        .scalars()
        .all()
    )

    return [_to_membership_response(db, m) for m in memberships]


def _to_membership_response(db: Session, m: CohortMembership) -> CohortMembershipResponse:
    patient = m.patient
    latest_risk = (
        db.execute(
            select(ClinicalRiskAssessment)
            .where(ClinicalRiskAssessment.patient_id == patient.id)
            .order_by(ClinicalRiskAssessment.assessed_at.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )

    return CohortMembershipResponse(
        id=m.id,
        cohort_id=m.cohort_id,
        patient_id=m.patient_id,
        patient_identifier=patient.patient_id if patient else None,
        patient_name=f"{patient.first_name} {patient.last_name}" if patient else None,
        enrolled_at=m.enrolled_at,
        status=m.status,
        notes=m.notes,
        latest_risk_score=latest_risk.risk_score if latest_risk else None,
        latest_risk_tier=latest_risk.risk_tier if latest_risk else None,
    )


def _sync_cohort_membership_criteria(db: Session, cohort: PatientCohort) -> int:
    """Internal rule evaluation matching patients against cohort criteria."""
    if not cohort.criteria_json:
        return 0

    criteria = cohort.criteria_json
    patients = db.execute(select(Patient)).scalars().all()
    now_date = date.today()
    enrolled_count = 0

    for p in patients:
        matches = True

        # Age filter
        if p.date_of_birth:
            age = (now_date - p.date_of_birth).days // 365
            if criteria.get("min_age") is not None and age < criteria["min_age"]:
                matches = False
            if criteria.get("max_age") is not None and age > criteria["max_age"]:
                matches = False

        # Gender filter
        if criteria.get("gender") and getattr(p, "gender", None):
            gen_val = p.gender.value if hasattr(p.gender, "value") else str(p.gender)
            if gen_val.lower() != criteria["gender"].lower():
                matches = False

        # Condition keywords across encounters and care plans
        conditions = criteria.get("conditions", [])
        if conditions:
            enc_texts = [
                f"{e.chief_complaint or ''} {e.assessment or ''} {e.plan or ''} {e.clinical_notes or ''}"
                for e in db.execute(select(Encounter).where(Encounter.patient_id == p.id)).scalars().all()
            ]
            plan_texts = [
                f"{cp.title} {cp.description} {cp.category}"
                for cp in db.execute(select(CarePlan).where(CarePlan.patient_id == p.id)).scalars().all()
            ]
            combined_history = " ".join(enc_texts + plan_texts).lower()
            if not any(c.lower() in combined_history for c in conditions):
                matches = False

        # Vitals thresholds
        if matches and (criteria.get("min_systolic_bp") or criteria.get("min_spo2")):
            latest_v = db.execute(
                select(VitalTelemetry)
                .where(VitalTelemetry.patient_id == p.id)
                .order_by(VitalTelemetry.measured_at.desc())
                .limit(1)
            ).scalar_one_or_none()

            if criteria.get("min_systolic_bp"):
                if not latest_v or not latest_v.systolic_bp or latest_v.systolic_bp < criteria["min_systolic_bp"]:
                    matches = False
            if criteria.get("min_spo2"):
                if not latest_v or not latest_v.spo2_percent or latest_v.spo2_percent < criteria["min_spo2"]:
                    matches = False

        # Active Alerts check
        if matches and criteria.get("active_alerts_only"):
            alert_count = db.execute(
                select(func.count(ClinicalAlert.id)).where(
                    ClinicalAlert.patient_id == p.id,
                    ClinicalAlert.status == "active",
                )
            ).scalar() or 0
            if alert_count == 0:
                matches = False

        # Apply enrollment if matches
        existing = db.execute(
            select(CohortMembership).where(
                CohortMembership.cohort_id == cohort.id,
                CohortMembership.patient_id == p.id,
            )
        ).scalar_one_or_none()

        if matches:
            if not existing:
                db.add(CohortMembership(
                    cohort_id=cohort.id,
                    patient_id=p.id,
                    status="active",
                    notes="Auto-enrolled via dynamic criteria match",
                    enrolled_at=datetime.now(timezone.utc),
                ))
                enrolled_count += 1
            elif existing.status != "active":
                existing.status = "active"
                enrolled_count += 1
        elif existing and existing.notes == "Auto-enrolled via dynamic criteria match":
            # Auto-graduate if no longer matching dynamic rule
            existing.status = "graduated"

    db.commit()
    logger.info("Dynamic criteria sync for cohort %s updated %d patients", cohort.cohort_id, enrolled_count)
    return enrolled_count


# ==============================================================================
# CLINICAL RISK STRATIFICATION
# ==============================================================================

def assess_patient_risk(
    db: Session,
    patient_id_str: str,
    risk_type: RiskType,
    current_user: User,
    encounter_id: Optional[int] = None,
    custom_context: Optional[str] = None,
) -> RiskAssessmentResponse:
    """Calculate and persist multi-factorial clinical risk assessment."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may trigger clinical risk assessments.",
        )

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

    # Gather patient risk features
    age = 45
    if patient.date_of_birth:
        age = (date.today() - patient.date_of_birth).days // 365

    # Gather condition keywords from encounters & care plans
    encs = db.execute(select(Encounter).where(Encounter.patient_id == patient.id)).scalars().all()
    cps = db.execute(select(CarePlan).where(CarePlan.patient_id == patient.id)).scalars().all()
    conditions = [
        f"{e.chief_complaint or ''} {e.assessment or ''} {e.plan or ''}"
        for e in encs
    ] + [f"{cp.title} {cp.description}" for cp in cps]
    if custom_context:
        conditions.append(custom_context)

    latest_vital = (

        db.execute(
            select(VitalTelemetry)
            .where(VitalTelemetry.patient_id == patient.id)
            .order_by(VitalTelemetry.measured_at.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )
    vitals_dict = {
        "heart_rate": latest_vital.heart_rate if latest_vital else None,
        "systolic_bp": latest_vital.systolic_bp if latest_vital else None,
        "diastolic_bp": latest_vital.diastolic_bp if latest_vital else None,
        "spo2_percent": latest_vital.spo2_percent if latest_vital else None,
    }

    active_alerts = (
        db.execute(
            select(ClinicalAlert)
            .where(ClinicalAlert.patient_id == patient.id, ClinicalAlert.status == "active")
        )
        .scalars()
        .all()
    )
    alerts_list = [{"title": a.title, "severity": a.severity} for a in active_alerts]

    overdue_tasks = (
        db.execute(
            select(func.count(CareTask.id)).where(
                CareTask.patient_id == patient.id,
                CareTask.status != "completed",
                CareTask.due_date < datetime.now(timezone.utc),
            )
        ).scalar() or 0
    )

    active_plans = (
        db.execute(
            select(func.count(CarePlan.id)).where(
                CarePlan.patient_id == patient.id,
                CarePlan.status == "active",
            )
        ).scalar() or 0
    )

    provider = get_risk_provider()
    calculated = provider.calculate_risk(
        patient_data={
            "age": age,
            "conditions": conditions,
            "vitals": vitals_dict,
            "alerts": alerts_list,
            "overdue_tasks_count": overdue_tasks,
            "active_care_plans_count": active_plans,
        },
        risk_type=risk_type,
        custom_context=custom_context,
    )

    now = datetime.now(timezone.utc)
    assessment = ClinicalRiskAssessment(
        assessment_id=_generate_assessment_id(),
        patient_id=patient.id,
        encounter_id=encounter_id,
        risk_type=risk_type.value,
        risk_score=calculated["risk_score"],
        risk_tier=calculated["risk_tier"].value if hasattr(calculated["risk_tier"], "value") else str(calculated["risk_tier"]),
        predicted_outcome=calculated["predicted_outcome"],
        contributing_factors_json=calculated["contributing_factors"],
        mitigation_recommendations_json=calculated["mitigation_recommendations"],
        assessed_by_user_id=current_user.id,
        is_ai_generated=True,
        assessed_at=now,
        created_at=now,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    logger.info(
        "Assessed %s for patient=%s -> score=%.1f (%s) by user_id=%s",
        risk_type.value,
        patient.patient_id,
        assessment.risk_score,
        assessment.risk_tier,
        current_user.id,
    )
    return RiskAssessmentResponse.model_validate(assessment)


def list_patient_risk_assessments(
    db: Session,
    patient_id_str: str,
    current_user: User,
    risk_type: Optional[str] = None,
) -> RiskAssessmentListResponse:
    """List historical risk assessments for a patient."""
    stmt = select(Patient).where(
        (Patient.patient_id == patient_id_str)
        | (Patient.id == (int(patient_id_str) if patient_id_str.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id_str}' not found.")

    _validate_patient_risk_access(db, current_user, patient)

    query = (
        select(ClinicalRiskAssessment)
        .where(ClinicalRiskAssessment.patient_id == patient.id)
        .order_by(ClinicalRiskAssessment.assessed_at.desc())
    )
    if risk_type:
        query = query.where(ClinicalRiskAssessment.risk_type == risk_type)

    items = db.execute(query).scalars().all()
    results = [RiskAssessmentResponse.model_validate(i) for i in items]
    return RiskAssessmentListResponse(items=results, total=len(results))


def get_risk_assessment(
    db: Session,
    assessment_id: str,
    current_user: User,
) -> RiskAssessmentResponse:
    """Retrieve details of a specific risk assessment."""
    stmt = select(ClinicalRiskAssessment).where(ClinicalRiskAssessment.assessment_id == assessment_id)
    assessment = db.execute(stmt).scalar_one_or_none()
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical risk assessment '{assessment_id}' not found.",
        )

    _validate_patient_risk_access(db, current_user, assessment.patient)
    return RiskAssessmentResponse.model_validate(assessment)


# ==============================================================================
# COHORT POPULATION ANALYTICS
# ==============================================================================

def get_cohort_analytics(
    db: Session,
    cohort_id: str,
    current_user: User,
) -> CohortAnalyticsResponse:
    """Calculate aggregate population health and risk indicators for a cohort."""
    _validate_clinical_staff_access(current_user)

    cohort = db.execute(
        select(PatientCohort).where(
            (PatientCohort.cohort_id == cohort_id)
            | (PatientCohort.id == (int(cohort_id) if cohort_id.isdigit() else -1))
        )
    ).scalar_one_or_none()
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cohort '{cohort_id}' not found.")

    member_patient_ids = [
        m.patient_id
        for m in db.execute(
            select(CohortMembership).where(
                CohortMembership.cohort_id == cohort.id,
                CohortMembership.status == "active",
            )
        ).scalars().all()
    ]

    total_members = len(member_patient_ids)
    if total_members == 0:
        return CohortAnalyticsResponse(
            cohort_id=cohort.cohort_id,
            name=cohort.name,
            cohort_type=cohort.cohort_type,
            total_members=0,
            risk_tier_distribution={"LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0},
            mean_risk_score=0.0,
            high_risk_patient_count=0,
            active_alerts_count=0,
            active_care_plans_count=0,
            overdue_tasks_count=0,
            generated_at=datetime.now(timezone.utc),
        )

    # Risk calculations across members
    tier_counts = {"LOW": 0, "MODERATE": 0, "HIGH": 0, "CRITICAL": 0}
    scores: list[float] = []

    for pid in member_patient_ids:
        latest_risk = db.execute(
            select(ClinicalRiskAssessment)
            .where(ClinicalRiskAssessment.patient_id == pid)
            .order_by(ClinicalRiskAssessment.assessed_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if latest_risk:
            tier = latest_risk.risk_tier if latest_risk.risk_tier in tier_counts else "MODERATE"
            tier_counts[tier] += 1
            scores.append(latest_risk.risk_score)
        else:
            tier_counts["MODERATE"] += 1
            scores.append(25.0)

    mean_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    high_risk_count = tier_counts["HIGH"] + tier_counts["CRITICAL"]

    # Active alerts in cohort
    alerts_cnt = db.execute(
        select(func.count(ClinicalAlert.id)).where(
            ClinicalAlert.patient_id.in_(member_patient_ids),
            ClinicalAlert.status == "active",
        )
    ).scalar() or 0

    # Active care plans
    plans_cnt = db.execute(
        select(func.count(CarePlan.id)).where(
            CarePlan.patient_id.in_(member_patient_ids),
            CarePlan.status == "active",
        )
    ).scalar() or 0

    # Overdue tasks
    overdue_cnt = db.execute(
        select(func.count(CareTask.id)).where(
            CareTask.patient_id.in_(member_patient_ids),
            CareTask.status != "completed",
            CareTask.due_date < datetime.now(timezone.utc),
        )
    ).scalar() or 0

    return CohortAnalyticsResponse(
        cohort_id=cohort.cohort_id,
        name=cohort.name,
        cohort_type=cohort.cohort_type,
        total_members=total_members,
        risk_tier_distribution=tier_counts,
        mean_risk_score=mean_score,
        high_risk_patient_count=high_risk_count,
        active_alerts_count=alerts_cnt,
        active_care_plans_count=plans_cnt,
        overdue_tasks_count=overdue_cnt,
        generated_at=datetime.now(timezone.utc),
    )


# ==============================================================================
# ASYNC WORKER TASK JOBS
# ==============================================================================

def execute_cohort_evaluation_job(cohort_id: str, user_id: Optional[int] = None) -> dict:
    """Background worker job evaluating dynamic cohort rules across patient records."""
    db = SessionLocal()
    try:
        cohort = db.execute(
            select(PatientCohort).where(
                (PatientCohort.cohort_id == cohort_id)
                | (PatientCohort.id == (int(cohort_id) if cohort_id.isdigit() else -1))
            )
        ).scalar_one_or_none()
        if not cohort:
            return {"error": f"Cohort {cohort_id} not found"}

        synced = _sync_cohort_membership_criteria(db, cohort)
        return {"cohort_id": cohort.cohort_id, "synced_members": synced, "status": "completed"}
    finally:
        db.close()


def execute_patient_risk_stratification_job(
    patient_id: str,
    risk_type: str,
    user_id: Optional[int] = None,
) -> dict:
    """Background worker job calculating clinical risk score."""
    db = SessionLocal()
    try:
        user = db.get(User, user_id) if user_id else None
        if not user:
            user = User(id=1, email="system@medigen.internal", role=UserRole.ADMIN, name="System Worker")

        res = assess_patient_risk(
            db=db,
            patient_id_str=patient_id,
            risk_type=RiskType(risk_type),
            current_user=user,
        )
        return {
            "assessment_id": res.assessment_id,
            "patient_id": str(res.patient_id),
            "risk_type": res.risk_type.value if hasattr(res.risk_type, "value") else str(res.risk_type),
            "risk_score": res.risk_score,
            "risk_tier": res.risk_tier.value if hasattr(res.risk_tier, "value") else str(res.risk_tier),
        }
    finally:
        db.close()


def enqueue_cohort_evaluation(
    db: Session,
    cohort_id: str,
    current_user: User,
) -> BackgroundTask:
    """Enqueue asynchronous dynamic cohort membership recalculation."""
    _validate_clinical_staff_access(current_user)

    cohort = db.execute(
        select(PatientCohort).where(
            (PatientCohort.cohort_id == cohort_id)
            | (PatientCohort.id == (int(cohort_id) if cohort_id.isdigit() else -1))
        )
    ).scalar_one_or_none()
    if not cohort:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cohort '{cohort_id}' not found.")

    provider = get_background_task_provider()
    task = provider.submit_task(
        task_type=BackgroundTaskType.COHORT_ANALYSIS,
        fn=execute_cohort_evaluation_job,
        fn_kwargs={"cohort_id": cohort.cohort_id, "user_id": current_user.id},
        created_by_user_id=current_user.id,
        payload={"cohort_id": cohort.cohort_id},
    )
    return task


def enqueue_patient_risk_stratification(
    db: Session,
    patient_id: str,
    risk_type: RiskType,
    current_user: User,
) -> BackgroundTask:
    """Enqueue asynchronous clinical risk calculation."""
    _validate_clinical_staff_access(current_user)

    stmt = select(Patient).where(
        (Patient.patient_id == patient_id)
        | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id}' not found.")

    provider = get_background_task_provider()
    task = provider.submit_task(
        task_type=BackgroundTaskType.RISK_STRATIFICATION,
        fn=execute_patient_risk_stratification_job,
        fn_kwargs={"patient_id": patient.patient_id, "risk_type": risk_type.value, "user_id": current_user.id},
        patient_id=patient.patient_id,
        created_by_user_id=current_user.id,
        payload={"patient_id": patient.patient_id, "risk_type": risk_type.value},
    )
    return task
