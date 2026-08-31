"""Service layer for Clinical Transitions of Care, Handoffs (I-PASS/SBAR) & Discharge Protocols.

Phase 9.0.12: Clinical Transitions of Care, Multi-Disciplinary Handoffs (I-PASS/SBAR) & Automated Discharge Protocol Synthesis.
"""

from datetime import date, datetime, timezone
import logging
from typing import Any, Optional
import uuid
from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.ai.handoff_provider import get_handoff_provider
from app.ai.task_worker import get_background_task_provider
from app.core.tenant_context import verify_cross_facility_transfer_authorization
from app.database.session import SessionLocal
from app.models.alert import ClinicalAlert
from app.models.care_plan import CarePlan
from app.models.care_task import CareTask
from app.models.discharge import DischargeProtocol
from app.models.encounter import Encounter
from app.models.handoff import ClinicalHandoff
from app.models.patient import Patient
from app.models.risk_assessment import ClinicalRiskAssessment
from app.models.user import User, UserRole
from app.models.vital import VitalTelemetry
from app.schemas.discharge import (
    DischargeDisposition,
    DischargeProtocolCreate,
    DischargeProtocolListResponse,
    DischargeProtocolResponse,
    DischargeProtocolSynthesizeRequest,
    DischargeProtocolUpdate,
    DischargeSignoffRequest,
    DischargeStatus,
)
from app.schemas.handoff import (
    HandoffAcknowledge,
    HandoffCreate,
    HandoffFramework,
    HandoffListResponse,
    HandoffResponse,
    HandoffStatus,
    HandoffSynthesizeRequest,
    HandoffType,
    HandoffUpdate,
    IllnessSeverity,
)
from app.schemas.task import BackgroundTask, BackgroundTaskType

logger = logging.getLogger("medigen.services.handoff")


def _generate_handoff_id() -> str:
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:8].upper()
    return f"HDF-{today_str}-{short_uuid}"


def _generate_discharge_id() -> str:
    today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:8].upper()
    return f"DIS-{today_str}-{short_uuid}"


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
                detail="Patients may only access their own transition records.",
            )


def _to_handoff_response(h: ClinicalHandoff) -> HandoffResponse:
    p = h.patient
    return HandoffResponse(
        id=h.id,
        handoff_id=h.handoff_id,
        patient_id=h.patient_id,
        patient_identifier=p.patient_id if p else None,
        patient_name=f"{p.first_name} {p.last_name}" if p else None,
        encounter_id=h.encounter_id,
        sender_user_id=h.sender_user_id,
        sender_name=h.sender.name if h.sender else None,
        receiver_user_id=h.receiver_user_id,
        receiver_name=h.receiver.name if h.receiver else None,
        framework=HandoffFramework(h.framework),
        handoff_type=HandoffType(h.handoff_type),
        illness_severity=IllnessSeverity(h.illness_severity),
        status=HandoffStatus(h.status),
        summary=h.summary,
        action_items_json=h.action_items_json,
        situational_awareness_json=h.situational_awareness_json,
        synthesis_notes=h.synthesis_notes,
        is_ai_generated=h.is_ai_generated,
        acknowledged_at=h.acknowledged_at,
        version=getattr(h, "version", 1) or 1,
        created_at=h.created_at,
        updated_at=h.updated_at,
    )


def _to_discharge_response(d: DischargeProtocol) -> DischargeProtocolResponse:
    p = d.patient
    return DischargeProtocolResponse(
        id=d.id,
        discharge_id=d.discharge_id,
        patient_id=d.patient_id,
        patient_identifier=p.patient_id if p else None,
        patient_name=f"{p.first_name} {p.last_name}" if p else None,
        encounter_id=d.encounter_id,
        attending_user_id=d.attending_user_id,
        attending_name=d.attending.name if d.attending else None,
        nurse_user_id=d.nurse_user_id,
        nurse_name=d.nurse.name if d.nurse else None,
        pharmacist_user_id=d.pharmacist_user_id,
        pharmacist_name=d.pharmacist.name if d.pharmacist else None,
        status=DischargeStatus(d.status),
        disposition=DischargeDisposition(d.disposition),
        discharge_date=d.discharge_date,
        hospital_course_summary=d.hospital_course_summary,
        primary_discharge_diagnosis=d.primary_discharge_diagnosis,
        secondary_diagnoses_json=d.secondary_diagnoses_json,
        medication_reconciliation_json=d.medication_reconciliation_json,
        followup_instructions_json=d.followup_instructions_json,
        pending_tests_json=d.pending_tests_json,
        warning_symptoms_json=d.warning_symptoms_json,
        activity_and_diet_instructions=d.activity_and_diet_instructions,
        is_ai_generated=d.is_ai_generated,
        signed_off_at=d.signed_off_at,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


# ==============================================================================
# CLINICAL HANDOFF MANAGEMENT
# ==============================================================================

def create_handoff(
    db: Session,
    patient_id_str: str,
    payload: HandoffCreate,
    current_user: User,
) -> HandoffResponse:
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff may create clinical handoffs.",
        )

    patient = _get_patient(db, patient_id_str)
    handoff_id = _generate_handoff_id()

    # Cross-facility transfer authorization check
    source_fac = payload.source_facility_id or getattr(patient, "facility_id", None) or getattr(current_user, "default_facility_id", None) or "FAC-001"
    dest_fac = payload.destination_facility_id or source_fac
    verify_cross_facility_transfer_authorization(
        db=db,
        user=current_user,
        source_facility_id=source_fac,
        destination_facility_id=dest_fac,
        patient_id=patient.patient_id,
        resource_id=handoff_id,
    )

    actions_dict = [a.model_dump() for a in payload.action_items] if payload.action_items else []
    contingencies_dict = [c.model_dump() for c in payload.situational_awareness] if payload.situational_awareness else []

    handoff = ClinicalHandoff(
        handoff_id=handoff_id,
        patient_id=patient.id,
        encounter_id=payload.encounter_id,
        sender_user_id=current_user.id,
        receiver_user_id=payload.receiver_user_id,
        framework=payload.framework.value,
        handoff_type=payload.handoff_type.value,
        illness_severity=payload.illness_severity.value,
        status="active",
        summary=payload.summary,
        action_items_json=actions_dict,
        situational_awareness_json=contingencies_dict,
        is_ai_generated=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(handoff)
    db.commit()
    db.refresh(handoff)

    logger.info("Created clinical handoff %s for patient %s by user %s", handoff_id, patient.patient_id, current_user.id)
    resp = _to_handoff_response(handoff)
    resp.source_facility_id = source_fac
    resp.destination_facility_id = dest_fac
    return resp


def synthesize_handoff(
    db: Session,
    patient_id_str: str,
    payload: HandoffSynthesizeRequest,
    current_user: User,
) -> HandoffResponse:
    """Synthesizes an assistive clinical handoff (I-PASS or SBAR) in DRAFT state."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff may trigger AI handoff synthesis.",
        )

    patient = _get_patient(db, patient_id_str)

    # Cross-facility transfer authorization check
    source_fac = payload.source_facility_id or getattr(patient, "facility_id", None) or getattr(current_user, "default_facility_id", None) or "FAC-001"
    dest_fac = payload.destination_facility_id or source_fac
    verify_cross_facility_transfer_authorization(
        db=db,
        user=current_user,
        source_facility_id=source_fac,
        destination_facility_id=dest_fac,
        patient_id=patient.patient_id,
    )

    age = 45

    if patient.date_of_birth:
        age = (date.today() - patient.date_of_birth).days // 365

    # Gather patient condition keywords
    encs = db.execute(
        select(Encounter)
        .where(Encounter.patient_id == patient.id)
        .order_by(Encounter.encounter_date.desc())
    ).scalars().all()
    diagnoses = [e.assessment for e in encs if e.assessment] or [e.chief_complaint for e in encs if e.chief_complaint]

    recent_enc_summary = encs[0].assessment if encs else None

    # Latest vitals
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
        "spo2_percent": latest_vital.spo2_percent if latest_vital else None,
    }

    # Active alerts
    alerts = db.execute(
        select(ClinicalAlert).where(ClinicalAlert.patient_id == patient.id, ClinicalAlert.status == "active")
    ).scalars().all()
    alerts_list = [{"title": a.title, "severity": a.severity} for a in alerts]

    # Latest risk assessment
    latest_risk = (
        db.execute(
            select(ClinicalRiskAssessment)
            .where(ClinicalRiskAssessment.patient_id == patient.id)
            .order_by(ClinicalRiskAssessment.assessed_at.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )

    provider = get_handoff_provider()
    synth = provider.synthesize_handoff(
        framework=payload.framework.value,
        handoff_type=payload.handoff_type.value,
        patient_name=f"{patient.first_name} {patient.last_name}",
        patient_age=age,
        gender=getattr(patient.gender, "value", str(patient.gender)),
        diagnoses=diagnoses,
        recent_encounter_summary=recent_enc_summary,
        latest_vitals=vitals_dict,
        active_alerts=alerts_list,
        risk_score=latest_risk.risk_score if latest_risk else None,
        risk_tier=latest_risk.risk_tier if latest_risk else None,
        custom_context=payload.custom_context,
    )

    handoff_id = _generate_handoff_id()
    handoff = ClinicalHandoff(
        handoff_id=handoff_id,
        patient_id=patient.id,
        encounter_id=payload.encounter_id,
        sender_user_id=current_user.id,
        receiver_user_id=payload.receiver_user_id,
        framework=payload.framework.value,
        handoff_type=payload.handoff_type.value,
        illness_severity=synth["illness_severity"],
        status="draft",  # Assistive AI content always starts in draft
        summary=synth["summary"],
        action_items_json=synth["action_items"],
        situational_awareness_json=synth["situational_awareness"],
        is_ai_generated=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(handoff)
    db.commit()
    db.refresh(handoff)

    logger.info("Synthesized AI clinical handoff %s for patient %s", handoff_id, patient.patient_id)
    return _to_handoff_response(handoff)


def get_handoff(db: Session, handoff_id_str: str, current_user: User) -> HandoffResponse:
    stmt = select(ClinicalHandoff).where(
        (ClinicalHandoff.handoff_id == handoff_id_str)
        | (ClinicalHandoff.id == (int(handoff_id_str) if handoff_id_str.isdigit() else -1))
    )
    h = db.execute(stmt).scalar_one_or_none()
    if not h:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical handoff '{handoff_id_str}' not found.",
        )

    _validate_patient_access(current_user, h.patient)
    return _to_handoff_response(h)


def list_patient_handoffs(
    db: Session,
    patient_id_str: str,
    current_user: User,
    status_filter: Optional[HandoffStatus] = None,
) -> HandoffListResponse:
    patient = _get_patient(db, patient_id_str)
    _validate_patient_access(current_user, patient)

    stmt = select(ClinicalHandoff).where(ClinicalHandoff.patient_id == patient.id)
    if status_filter:
        stmt = stmt.where(ClinicalHandoff.status == status_filter.value)
    stmt = stmt.order_by(ClinicalHandoff.created_at.desc())

    items = db.execute(stmt).scalars().all()
    return HandoffListResponse(
        items=[_to_handoff_response(h) for h in items],
        total=len(items),
    )


def update_handoff(
    db: Session,
    handoff_id_str: str,
    payload: HandoffUpdate,
    current_user: User,
) -> HandoffResponse:
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff may update clinical handoffs.",
        )

    stmt = select(ClinicalHandoff).where(
        (ClinicalHandoff.handoff_id == handoff_id_str)
        | (ClinicalHandoff.id == (int(handoff_id_str) if handoff_id_str.isdigit() else -1))
    )
    h = db.execute(stmt).scalar_one_or_none()
    if not h:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical handoff '{handoff_id_str}' not found.",
        )

    # Optimistic locking version check
    if payload.version is not None:
        current_version = getattr(h, "version", 1) or 1
        if current_version != payload.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Conflict: Clinical handoff '{handoff_id_str}' has been modified by another user session. "
                    f"Current version is {current_version}, provided version is {payload.version}."
                ),
            )

    if payload.illness_severity is not None:
        h.illness_severity = payload.illness_severity.value
    if payload.summary is not None:
        h.summary = payload.summary
    if payload.action_items is not None:
        h.action_items_json = [a.model_dump() for a in payload.action_items]
    if payload.situational_awareness is not None:
        h.situational_awareness_json = [c.model_dump() for c in payload.situational_awareness]
    if payload.receiver_user_id is not None:
        h.receiver_user_id = payload.receiver_user_id
    if payload.status is not None:
        h.status = payload.status.value

    # Increment optimistic locking version
    h.version = (getattr(h, "version", 1) or 1) + 1
    h.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(h)
    return _to_handoff_response(h)


def acknowledge_handoff(
    db: Session,
    handoff_id_str: str,
    payload: HandoffAcknowledge,
    current_user: User,
) -> HandoffResponse:
    """Receiver acknowledges handoff with read-back / synthesis notes."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff may acknowledge clinical handoffs.",
        )

    stmt = select(ClinicalHandoff).where(
        (ClinicalHandoff.handoff_id == handoff_id_str)
        | (ClinicalHandoff.id == (int(handoff_id_str) if handoff_id_str.isdigit() else -1))
    )
    h = db.execute(stmt).scalar_one_or_none()
    if not h:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical handoff '{handoff_id_str}' not found.",
        )

    h.receiver_user_id = current_user.id
    h.synthesis_notes = payload.synthesis_notes
    h.status = "acknowledged"
    h.acknowledged_at = datetime.now(timezone.utc)
    h.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(h)
    logger.info("Clinical handoff %s acknowledged by receiver user %s", h.handoff_id, current_user.id)
    return _to_handoff_response(h)


# ==============================================================================
# DISCHARGE PROTOCOL & CONTINUITY OF CARE MANAGEMENT
# ==============================================================================

def create_discharge_protocol(
    db: Session,
    patient_id_str: str,
    payload: DischargeProtocolCreate,
    current_user: User,
) -> DischargeProtocolResponse:
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff may author discharge protocols.",
        )

    patient = _get_patient(db, patient_id_str)
    discharge_id = _generate_discharge_id()

    meds_dict = [m.model_dump() for m in payload.medication_reconciliation] if payload.medication_reconciliation else []
    followups_dict = [f.model_dump() for f in payload.followup_appointments] if payload.followup_appointments else []
    pending_dict = [p.model_dump() for p in payload.pending_tests] if payload.pending_tests else []
    warnings_dict = [w.model_dump() for w in payload.warning_symptoms] if payload.warning_symptoms else []

    discharge = DischargeProtocol(
        discharge_id=discharge_id,
        patient_id=patient.id,
        encounter_id=payload.encounter_id,
        attending_user_id=current_user.id if current_user.role in (UserRole.DOCTOR, UserRole.ADMIN) else None,
        status="under_review",
        disposition=payload.disposition.value,
        discharge_date=payload.discharge_date or datetime.now(timezone.utc),
        hospital_course_summary=payload.hospital_course_summary,
        primary_discharge_diagnosis=payload.primary_discharge_diagnosis,
        secondary_diagnoses_json=payload.secondary_diagnoses,
        medication_reconciliation_json=meds_dict,
        followup_instructions_json=followups_dict,
        pending_tests_json=pending_dict,
        warning_symptoms_json=warnings_dict,
        activity_and_diet_instructions=payload.activity_and_diet_instructions,
        is_ai_generated=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(discharge)
    db.commit()
    db.refresh(discharge)

    logger.info("Created discharge protocol %s for patient %s by user %s", discharge_id, patient.patient_id, current_user.id)
    return _to_discharge_response(discharge)


def synthesize_discharge_protocol(
    db: Session,
    patient_id_str: str,
    payload: DischargeProtocolSynthesizeRequest,
    current_user: User,
) -> DischargeProtocolResponse:
    """Synthesizes an assistive discharge protocol package in DRAFT state."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff may trigger AI discharge protocol synthesis.",
        )

    patient = _get_patient(db, patient_id_str)
    age = 45
    if patient.date_of_birth:
        age = (date.today() - patient.date_of_birth).days // 365

    # Gather conditions from encounters
    encs = db.execute(
        select(Encounter)
        .where(Encounter.patient_id == patient.id)
        .order_by(Encounter.encounter_date.desc())
    ).scalars().all()
    diagnoses = [e.assessment for e in encs if e.assessment] or [e.chief_complaint for e in encs if e.chief_complaint]

    recent_enc_summary = encs[0].assessment if encs else None

    # Latest risk assessment
    latest_risk = (
        db.execute(
            select(ClinicalRiskAssessment)
            .where(ClinicalRiskAssessment.patient_id == patient.id)
            .order_by(ClinicalRiskAssessment.assessed_at.desc())
            .limit(1)
        )
        .scalar_one_or_none()
    )

    provider = get_handoff_provider()
    synth = provider.synthesize_discharge(
        patient_name=f"{patient.first_name} {patient.last_name}",
        patient_age=age,
        gender=getattr(patient.gender, "value", str(patient.gender)),
        disposition=payload.disposition.value,
        diagnoses=diagnoses,
        encounter_summary=recent_enc_summary,
        risk_tier=latest_risk.risk_tier if latest_risk else None,
        custom_instructions=payload.custom_instructions,
    )

    discharge_id = _generate_discharge_id()
    discharge = DischargeProtocol(
        discharge_id=discharge_id,
        patient_id=patient.id,
        encounter_id=payload.encounter_id,
        attending_user_id=None,
        status="draft",  # AI generated content always starts as draft
        disposition=payload.disposition.value,
        discharge_date=datetime.now(timezone.utc),
        hospital_course_summary=synth["hospital_course_summary"],
        primary_discharge_diagnosis=synth["primary_discharge_diagnosis"],
        secondary_diagnoses_json=synth["secondary_diagnoses"],
        medication_reconciliation_json=synth["medication_reconciliation"],
        followup_instructions_json=synth["followup_appointments"],
        pending_tests_json=synth["pending_tests"],
        warning_symptoms_json=synth["warning_symptoms"],
        activity_and_diet_instructions=synth["activity_and_diet_instructions"],
        is_ai_generated=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(discharge)
    db.commit()
    db.refresh(discharge)

    logger.info("Synthesized AI discharge protocol %s for patient %s", discharge_id, patient.patient_id)
    return _to_discharge_response(discharge)


def get_discharge_protocol(db: Session, discharge_id_str: str, current_user: User) -> DischargeProtocolResponse:
    stmt = select(DischargeProtocol).where(
        (DischargeProtocol.discharge_id == discharge_id_str)
        | (DischargeProtocol.id == (int(discharge_id_str) if discharge_id_str.isdigit() else -1))
    )
    d = db.execute(stmt).scalar_one_or_none()
    if not d:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discharge protocol '{discharge_id_str}' not found.",
        )

    _validate_patient_access(current_user, d.patient)
    return _to_discharge_response(d)


def list_patient_discharge_protocols(
    db: Session,
    patient_id_str: str,
    current_user: User,
    status_filter: Optional[DischargeStatus] = None,
) -> DischargeProtocolListResponse:
    patient = _get_patient(db, patient_id_str)
    _validate_patient_access(current_user, patient)

    stmt = select(DischargeProtocol).where(DischargeProtocol.patient_id == patient.id)
    if status_filter:
        stmt = stmt.where(DischargeProtocol.status == status_filter.value)
    stmt = stmt.order_by(DischargeProtocol.created_at.desc())

    items = db.execute(stmt).scalars().all()
    return DischargeProtocolListResponse(
        items=[_to_discharge_response(d) for d in items],
        total=len(items),
    )


def update_discharge_protocol(
    db: Session,
    discharge_id_str: str,
    payload: DischargeProtocolUpdate,
    current_user: User,
) -> DischargeProtocolResponse:
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff may modify discharge protocols.",
        )

    stmt = select(DischargeProtocol).where(
        (DischargeProtocol.discharge_id == discharge_id_str)
        | (DischargeProtocol.id == (int(discharge_id_str) if discharge_id_str.isdigit() else -1))
    )
    d = db.execute(stmt).scalar_one_or_none()
    if not d:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discharge protocol '{discharge_id_str}' not found.",
        )

    if payload.disposition is not None:
        d.disposition = payload.disposition.value
    if payload.discharge_date is not None:
        d.discharge_date = payload.discharge_date
    if payload.hospital_course_summary is not None:
        d.hospital_course_summary = payload.hospital_course_summary
    if payload.primary_discharge_diagnosis is not None:
        d.primary_discharge_diagnosis = payload.primary_discharge_diagnosis
    if payload.secondary_diagnoses is not None:
        d.secondary_diagnoses_json = payload.secondary_diagnoses
    if payload.medication_reconciliation is not None:
        d.medication_reconciliation_json = [m.model_dump() for m in payload.medication_reconciliation]
    if payload.followup_appointments is not None:
        d.followup_instructions_json = [f.model_dump() for f in payload.followup_appointments]
    if payload.pending_tests is not None:
        d.pending_tests_json = [p.model_dump() for p in payload.pending_tests]
    if payload.warning_symptoms is not None:
        d.warning_symptoms_json = [w.model_dump() for w in payload.warning_symptoms]
    if payload.activity_and_diet_instructions is not None:
        d.activity_and_diet_instructions = payload.activity_and_diet_instructions
    if payload.status is not None:
        d.status = payload.status.value

    d.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(d)
    return _to_discharge_response(d)


def signoff_discharge_protocol(
    db: Session,
    discharge_id_str: str,
    payload: DischargeSignoffRequest,
    current_user: User,
) -> DischargeProtocolResponse:
    """Multi-disciplinary signoff: Attending Physician, Registered Nurse, or Pharmacist."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff may perform multi-disciplinary signoff.",
        )

    stmt = select(DischargeProtocol).where(
        (DischargeProtocol.discharge_id == discharge_id_str)
        | (DischargeProtocol.id == (int(discharge_id_str) if discharge_id_str.isdigit() else -1))
    )
    d = db.execute(stmt).scalar_one_or_none()
    if not d:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Discharge protocol '{discharge_id_str}' not found.",
        )

    role_key = payload.signoff_role.lower()
    now_ts = datetime.now(timezone.utc)

    if role_key == "attending_physician":
        if current_user.role not in (UserRole.DOCTOR, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only licensed physicians or administrators may perform attending physician signoff.",
            )
        d.attending_user_id = current_user.id
        d.status = "ready_for_discharge"
        d.signed_off_at = now_ts
    elif role_key == "registered_nurse":
        d.nurse_user_id = current_user.id
    elif role_key == "clinical_pharmacist":
        d.pharmacist_user_id = current_user.id
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid signoff role '{payload.signoff_role}'. Allowed: attending_physician, registered_nurse, clinical_pharmacist",
        )

    d.updated_at = now_ts
    db.commit()
    db.refresh(d)
    logger.info("Discharge protocol %s signed off with role %s by user %s", d.discharge_id, role_key, current_user.id)
    return _to_discharge_response(d)


# ==============================================================================
# ASYNC BACKGROUND WORKER DISPATCH
# ==============================================================================

def execute_handoff_synthesis_job(
    patient_id: str,
    framework: str = "ipass",
    handoff_type: str = "shift_change",
    receiver_user_id: Optional[int] = None,
    encounter_id: Optional[int] = None,
    custom_context: Optional[str] = None,
) -> dict[str, Any]:
    """Synchronous worker execution target for async handoff synthesis."""
    db = SessionLocal()
    try:
        dummy_user = db.execute(select(User).where(User.role == UserRole.DOCTOR)).scalars().first()
        if not dummy_user:
            dummy_user = db.execute(select(User)).scalars().first()

        req = HandoffSynthesizeRequest(
            framework=HandoffFramework(framework),
            handoff_type=HandoffType(handoff_type),
            receiver_user_id=receiver_user_id,
            encounter_id=encounter_id,
            custom_context=custom_context,
        )
        resp = synthesize_handoff(db, patient_id, req, dummy_user)
        return {"status": "completed", "handoff_id": resp.handoff_id}
    finally:
        db.close()


def execute_discharge_synthesis_job(
    patient_id: str,
    encounter_id: Optional[int] = None,
    disposition: str = "home_self_care",
    custom_instructions: Optional[str] = None,
) -> dict[str, Any]:
    """Synchronous worker execution target for async discharge synthesis."""
    db = SessionLocal()
    try:
        dummy_user = db.execute(select(User).where(User.role == UserRole.DOCTOR)).scalars().first()
        if not dummy_user:
            dummy_user = db.execute(select(User)).scalars().first()

        req = DischargeProtocolSynthesizeRequest(
            encounter_id=encounter_id,
            disposition=DischargeDisposition(disposition),
            custom_instructions=custom_instructions,
        )
        resp = synthesize_discharge_protocol(db, patient_id, req, dummy_user)
        return {"status": "completed", "discharge_id": resp.discharge_id}
    finally:
        db.close()


def enqueue_handoff_synthesis(
    patient_id: str,
    payload: HandoffSynthesizeRequest,
    current_user: User,
) -> BackgroundTask:
    task_provider = get_background_task_provider()
    task = task_provider.submit_task(
        task_type=BackgroundTaskType.HANDOFF_SYNTHESIS,
        fn=execute_handoff_synthesis_job,
        fn_kwargs={
            "patient_id": patient_id,
            "framework": payload.framework.value,
            "handoff_type": payload.handoff_type.value,
            "receiver_user_id": payload.receiver_user_id,
            "encounter_id": payload.encounter_id,
            "custom_context": payload.custom_context,
        },
        created_by_user_id=current_user.id,
        payload={
            "patient_id": patient_id,
            "framework": payload.framework.value,
            "handoff_type": payload.handoff_type.value,
        },
    )
    return task


def enqueue_discharge_synthesis(
    patient_id: str,
    payload: DischargeProtocolSynthesizeRequest,
    current_user: User,
) -> BackgroundTask:
    task_provider = get_background_task_provider()
    task = task_provider.submit_task(
        task_type=BackgroundTaskType.DISCHARGE_SYNTHESIS,
        fn=execute_discharge_synthesis_job,
        fn_kwargs={
            "patient_id": patient_id,
            "encounter_id": payload.encounter_id,
            "disposition": payload.disposition.value,
            "custom_instructions": payload.custom_instructions,
        },
        created_by_user_id=current_user.id,
        payload={
            "patient_id": patient_id,
            "disposition": payload.disposition.value,
        },
    )
    return task
