"""Business logic service for Vital Telemetry Ingestion, CDS Alerting & Simulation.

Phase 9.0.9: Clinical Decision Support Alerting & Real-Time Vital Telemetry Ingestion.
Provides:
- Ingestion of multi-parameter physiological vitals with unit normalization
- Deterministic clinical threshold & rule evaluation
- 30-minute alert debouncing & alarm-fatigue suppression
- Deterministic offline telemetry simulator profiles
- Clinician acknowledgement and dismissal audit trails
- RBAC and cross-patient isolation
"""

from datetime import datetime, timedelta, timezone
import logging
import uuid
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import ClinicalAlert
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.models.vital import VitalTelemetry
from app.schemas.alert import (
    AlertAcknowledgeRequest,
    AlertDismissRequest,
    AlertSeverity,
    AlertStatus,
    ClinicalAlertListResponse,
    ClinicalAlertResponse,
)
from app.schemas.vital import (
    VitalSimulateRequest,
    VitalSimulationProfile,
    VitalTelemetryCreate,
    VitalTelemetryListResponse,
    VitalTelemetryResponse,
)

logger = logging.getLogger("medigen.services.vital_service")

DEBOUNCE_WINDOW_MINUTES = 30


def _validate_patient_vital_access(db: Session, current_user: User, patient: Patient) -> None:
    """Enforce RBAC and strict patient data isolation for vitals and alerts."""
    if current_user.role in (UserRole.ADMIN, UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF):
        return
    if current_user.role == UserRole.PATIENT:
        if current_user.email.lower() != patient.email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You cannot access vitals or alerts belonging to another patient.",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient privileges to access patient telemetry.",
    )


def _generate_reading_id() -> str:
    """Generate unique public vital reading identifier (VIT-YYYYMMDD-XXXXXX)."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"VIT-{date_str}-{unique_suffix}"


def _generate_alert_id() -> str:
    """Generate unique public clinical alert identifier (ALT-YYYYMMDD-XXXXXX)."""
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:8].upper()
    return f"ALT-{date_str}-{unique_suffix}"


def evaluate_vital_thresholds(
    reading: VitalTelemetry,
) -> list[dict[str, Any]]:
    """Deterministic clinical rule evaluation for vital signs."""
    alerts: list[dict[str, Any]] = []

    # 1. Hypoxia (SpO2)
    if reading.spo2_percent is not None:
        if reading.spo2_percent < 90.0:
            alerts.append({
                "alert_type": "vital_hypoxia",
                "severity": AlertSeverity.CRITICAL,
                "title": f"Critical Hypoxia Alert (SpO2 {reading.spo2_percent}%)",
                "explanation": (
                    f"SpO2 reading of {reading.spo2_percent}% is below critical threshold (<90%). "
                    f"Immediate airway assessment and oxygen therapy evaluation recommended."
                ),
                "parameters": {"spo2_percent": reading.spo2_percent, "threshold": "<90%"},
            })
        elif reading.spo2_percent < 94.0:
            alerts.append({
                "alert_type": "vital_hypoxia",
                "severity": AlertSeverity.HIGH,
                "title": f"Moderate Hypoxia Warning (SpO2 {reading.spo2_percent}%)",
                "explanation": (
                    f"SpO2 reading of {reading.spo2_percent}% is below normal baseline (<94%). "
                    f"Recommend monitoring and supplemental oxygen consideration."
                ),
                "parameters": {"spo2_percent": reading.spo2_percent, "threshold": "<94%"},
            })

    # 2. Tachycardia & Bradycardia (Heart Rate)
    if reading.heart_rate is not None:
        if reading.heart_rate > 140:
            alerts.append({
                "alert_type": "vital_tachycardia",
                "severity": AlertSeverity.CRITICAL,
                "title": f"Severe Tachycardia Alert (HR {reading.heart_rate} bpm)",
                "explanation": (
                    f"Heart rate of {reading.heart_rate} bpm exceeds critical limit (>140 bpm). "
                    f"Urgent 12-lead ECG and continuous rhythm monitoring advised."
                ),
                "parameters": {"heart_rate": reading.heart_rate, "threshold": ">140 bpm"},
            })
        elif reading.heart_rate > 100:
            alerts.append({
                "alert_type": "vital_tachycardia",
                "severity": AlertSeverity.MODERATE,
                "title": f"Elevated Heart Rate Warning (HR {reading.heart_rate} bpm)",
                "explanation": (
                    f"Heart rate of {reading.heart_rate} bpm exceeds normal resting limits (>100 bpm)."
                ),
                "parameters": {"heart_rate": reading.heart_rate, "threshold": ">100 bpm"},
            })
        elif reading.heart_rate < 40:
            alerts.append({
                "alert_type": "vital_bradycardia",
                "severity": AlertSeverity.CRITICAL,
                "title": f"Severe Bradycardia Alert (HR {reading.heart_rate} bpm)",
                "explanation": (
                    f"Heart rate of {reading.heart_rate} bpm is below critical lower limit (<40 bpm). "
                    f"Assess perfusion, hemodynamics, and cardiac telemetry."
                ),
                "parameters": {"heart_rate": reading.heart_rate, "threshold": "<40 bpm"},
            })
        elif reading.heart_rate < 50:
            alerts.append({
                "alert_type": "vital_bradycardia",
                "severity": AlertSeverity.HIGH,
                "title": f"Bradycardia Warning (HR {reading.heart_rate} bpm)",
                "explanation": (
                    f"Heart rate of {reading.heart_rate} bpm is below normal resting range (<50 bpm)."
                ),
                "parameters": {"heart_rate": reading.heart_rate, "threshold": "<50 bpm"},
            })

    # 3. Blood Pressure (Hypertensive Crisis / Hypotension)
    if reading.systolic_bp is not None or reading.diastolic_bp is not None:
        sbp = reading.systolic_bp or 120
        dbp = reading.diastolic_bp or 80

        if sbp >= 180 or dbp >= 120:
            alerts.append({
                "alert_type": "vital_hypertension",
                "severity": AlertSeverity.CRITICAL,
                "title": f"Hypertensive Crisis Alert (BP {sbp}/{dbp} mmHg)",
                "explanation": (
                    f"Blood pressure of {sbp}/{dbp} mmHg reaches hypertensive crisis threshold (SBP>=180 or DBP>=120 mmHg). "
                    f"Immediate physician evaluation for end-organ compromise required."
                ),
                "parameters": {"systolic_bp": sbp, "diastolic_bp": dbp, "threshold": "SBP>=180 or DBP>=120"},
            })
        elif sbp >= 140 or dbp >= 90:
            alerts.append({
                "alert_type": "vital_hypertension",
                "severity": AlertSeverity.MODERATE,
                "title": f"Stage 2 Hypertension Warning (BP {sbp}/{dbp} mmHg)",
                "explanation": (
                    f"Blood pressure of {sbp}/{dbp} mmHg exceeds normal clinical range (SBP>=140 or DBP>=90 mmHg)."
                ),
                "parameters": {"systolic_bp": sbp, "diastolic_bp": dbp, "threshold": "SBP>=140 or DBP>=90"},
            })
        elif sbp < 85 or dbp < 50:
            alerts.append({
                "alert_type": "vital_hypotension",
                "severity": AlertSeverity.CRITICAL,
                "title": f"Severe Hypotension Alert (BP {sbp}/{dbp} mmHg)",
                "explanation": (
                    f"Blood pressure of {sbp}/{dbp} mmHg indicates severe hypotension (SBP<85 or DBP<50 mmHg). "
                    f"Evaluate intravascular volume, sepsis, or shock."
                ),
                "parameters": {"systolic_bp": sbp, "diastolic_bp": dbp, "threshold": "SBP<85 or DBP<50"},
            })
        elif sbp < 90:
            alerts.append({
                "alert_type": "vital_hypotension",
                "severity": AlertSeverity.HIGH,
                "title": f"Hypotension Warning (BP {sbp}/{dbp} mmHg)",
                "explanation": (
                    f"Systolic blood pressure of {sbp} mmHg is below normal threshold (<90 mmHg)."
                ),
                "parameters": {"systolic_bp": sbp, "threshold": "SBP<90"},
            })

    # 4. Temperature (Pyrexia)
    if reading.temperature_c is not None:
        if reading.temperature_c >= 39.5:
            alerts.append({
                "alert_type": "vital_hyperthermia",
                "severity": AlertSeverity.HIGH,
                "title": f"High Pyrexia Warning ({reading.temperature_c}°C)",
                "explanation": (
                    f"Body temperature of {reading.temperature_c}°C indicates high fever. "
                    f"Evaluate for acute infection or inflammatory etiology."
                ),
                "parameters": {"temperature_c": reading.temperature_c, "threshold": ">=39.5°C"},
            })

    return alerts


def process_vital_alerts(
    db: Session,
    reading: VitalTelemetry,
) -> list[ClinicalAlert]:
    """Evaluate CDS rules and persist non-debounced clinical alerts."""
    alert_specs = evaluate_vital_thresholds(reading)
    persisted_alerts: list[ClinicalAlert] = []
    now = datetime.now(timezone.utc)
    debounce_cutoff = now - timedelta(minutes=DEBOUNCE_WINDOW_MINUTES)

    for spec in alert_specs:
        # Check for existing alert within debounce window
        stmt = (
            select(ClinicalAlert)
            .where(
                ClinicalAlert.patient_id == reading.patient_id,
                ClinicalAlert.alert_type == spec["alert_type"],
                ClinicalAlert.status.in_([AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]),
                ClinicalAlert.last_triggered_at >= debounce_cutoff,
            )
            .order_by(ClinicalAlert.last_triggered_at.desc())
        )
        existing_alert = db.execute(stmt).scalar_one_or_none()

        if existing_alert:
            # Debounce: update recurrence count, latest timestamp, and snapshot
            existing_alert.recurrence_count += 1
            existing_alert.last_triggered_at = now
            existing_alert.parameters_json = spec["parameters"]
            existing_alert.reading_id = reading.id
            db.commit()
            db.refresh(existing_alert)
            logger.info(
                "Debounced alert %s (type=%s, count=%s) for patient_id=%s",
                existing_alert.alert_id,
                existing_alert.alert_type,
                existing_alert.recurrence_count,
                reading.patient_id,
            )
            persisted_alerts.append(existing_alert)
        else:
            # Create fresh active alert
            new_alert = ClinicalAlert(
                alert_id=_generate_alert_id(),
                patient_id=reading.patient_id,
                encounter_id=reading.encounter_id,
                reading_id=reading.id,
                alert_type=spec["alert_type"],
                severity=spec["severity"],
                status=AlertStatus.ACTIVE,
                title=spec["title"],
                explanation=spec["explanation"],
                parameters_json=spec["parameters"],
                recurrence_count=1,
                last_triggered_at=now,
                created_at=now,
            )
            db.add(new_alert)
            db.commit()
            db.refresh(new_alert)
            logger.info(
                "Created new CDS alert %s (severity=%s) for patient_id=%s",
                new_alert.alert_id,
                new_alert.severity.value,
                reading.patient_id,
            )
            persisted_alerts.append(new_alert)

    return persisted_alerts


def ingest_vital_telemetry(
    db: Session,
    patient_id: str,
    vital_in: VitalTelemetryCreate,
    current_user: User,
) -> tuple[VitalTelemetryResponse, list[ClinicalAlertResponse]]:
    """Ingest a vital telemetry reading and synchronously evaluate CDS alerts."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may ingest patient telemetry.",
        )

    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' not found.",
        )

    _validate_patient_vital_access(db, current_user, patient)

    measured_at = vital_in.measured_at or datetime.now(timezone.utc)

    reading = VitalTelemetry(
        reading_id=_generate_reading_id(),
        patient_id=patient.id,
        heart_rate=vital_in.heart_rate,
        systolic_bp=vital_in.systolic_bp,
        diastolic_bp=vital_in.diastolic_bp,
        respiratory_rate=vital_in.respiratory_rate,
        temperature_c=vital_in.temperature,
        spo2_percent=vital_in.spo2_percent,
        weight_kg=vital_in.weight_kg,
        device_id=vital_in.device_id,
        source=vital_in.source,
        measured_at=measured_at,
    )
    db.add(reading)
    db.commit()
    db.refresh(reading)

    # Evaluate alerts
    alerts = process_vital_alerts(db, reading)

    return (
        VitalTelemetryResponse.model_validate(reading),
        [ClinicalAlertResponse.model_validate(a) for a in alerts],
    )


def simulate_vital_telemetry(
    db: Session,
    patient_id: str,
    sim_in: VitalSimulateRequest,
    current_user: User,
) -> tuple[VitalTelemetryResponse, list[ClinicalAlertResponse]]:
    """Ingest deterministic simulated telemetry reading for testing and clinical demo."""
    profile = sim_in.profile

    if profile == VitalSimulationProfile.HYPOXIC:
        telemetry = VitalTelemetryCreate(
            heart_rate=108,
            systolic_bp=130,
            diastolic_bp=85,
            respiratory_rate=26,
            temperature=37.2,
            spo2_percent=86.0,
            weight_kg=72.0,
            device_id=sim_in.device_id,
            source="simulator",
        )
    elif profile == VitalSimulationProfile.HYPERTENSIVE_CRISIS:
        telemetry = VitalTelemetryCreate(
            heart_rate=98,
            systolic_bp=195,
            diastolic_bp=128,
            respiratory_rate=20,
            temperature=36.9,
            spo2_percent=96.0,
            weight_kg=78.0,
            device_id=sim_in.device_id,
            source="simulator",
        )
    elif profile == VitalSimulationProfile.TACHYCARDIC:
        telemetry = VitalTelemetryCreate(
            heart_rate=152,
            systolic_bp=124,
            diastolic_bp=80,
            respiratory_rate=22,
            temperature=37.8,
            spo2_percent=97.0,
            weight_kg=68.0,
            device_id=sim_in.device_id,
            source="simulator",
        )
    elif profile == VitalSimulationProfile.BRADYCARDIC:
        telemetry = VitalTelemetryCreate(
            heart_rate=36,
            systolic_bp=92,
            diastolic_bp=56,
            respiratory_rate=12,
            temperature=36.4,
            spo2_percent=95.0,
            weight_kg=70.0,
            device_id=sim_in.device_id,
            source="simulator",
        )
    else:  # NORMAL
        telemetry = VitalTelemetryCreate(
            heart_rate=72,
            systolic_bp=120,
            diastolic_bp=80,
            respiratory_rate=16,
            temperature=37.0,
            spo2_percent=98.5,
            weight_kg=70.0,
            device_id=sim_in.device_id,
            source="simulator",
        )

    return ingest_vital_telemetry(
        db=db,
        patient_id=patient_id,
        vital_in=telemetry,
        current_user=current_user,
    )


def list_patient_vitals(
    db: Session,
    patient_id: str,
    current_user: User,
    skip: int = 0,
    limit: int = 50,
) -> VitalTelemetryListResponse:
    """List historical vital telemetry readings for a patient."""
    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' not found.",
        )

    _validate_patient_vital_access(db, current_user, patient)

    vital_stmt = (
        select(VitalTelemetry)
        .where(VitalTelemetry.patient_id == patient.id)
        .order_by(VitalTelemetry.measured_at.desc())
        .offset(skip)
        .limit(limit)
    )
    readings = db.execute(vital_stmt).scalars().all()

    return VitalTelemetryListResponse(
        items=[VitalTelemetryResponse.model_validate(r) for r in readings],
        total=len(readings),
    )


def get_latest_patient_vital(
    db: Session,
    patient_id: str,
    current_user: User,
) -> Optional[VitalTelemetryResponse]:
    """Retrieve the most recent vital telemetry reading for a patient."""
    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' not found.",
        )

    _validate_patient_vital_access(db, current_user, patient)

    vital_stmt = (
        select(VitalTelemetry)
        .where(VitalTelemetry.patient_id == patient.id)
        .order_by(VitalTelemetry.measured_at.desc())
        .limit(1)
    )
    reading = db.execute(vital_stmt).scalar_one_or_none()
    if not reading:
        return None

    return VitalTelemetryResponse.model_validate(reading)


def list_patient_alerts(
    db: Session,
    patient_id: str,
    current_user: User,
    status_filter: Optional[str] = None,
) -> ClinicalAlertListResponse:
    """List clinical decision support alerts for a patient."""
    stmt = select(Patient).where(
        (Patient.patient_id == patient_id) | (Patient.id == (int(patient_id) if patient_id.isdigit() else -1))
    )
    patient = db.execute(stmt).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' not found.",
        )

    _validate_patient_vital_access(db, current_user, patient)

    alert_stmt = (
        select(ClinicalAlert)
        .where(ClinicalAlert.patient_id == patient.id)
        .order_by(ClinicalAlert.last_triggered_at.desc())
    )
    if status_filter:
        alert_stmt = alert_stmt.where(ClinicalAlert.status == status_filter)

    alerts = db.execute(alert_stmt).scalars().all()
    return ClinicalAlertListResponse(
        items=[ClinicalAlertResponse.model_validate(a) for a in alerts],
        total=len(alerts),
    )


def get_clinical_alert(
    db: Session,
    alert_id: str,
    current_user: User,
) -> ClinicalAlertResponse:
    """Retrieve details of a specific clinical alert."""
    stmt = select(ClinicalAlert).where(ClinicalAlert.alert_id == alert_id)
    alert = db.execute(stmt).scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical alert '{alert_id}' not found.",
        )

    _validate_patient_vital_access(db, current_user, alert.patient)
    return ClinicalAlertResponse.model_validate(alert)


def acknowledge_clinical_alert(
    db: Session,
    alert_id: str,
    ack_in: AlertAcknowledgeRequest,
    current_user: User,
) -> ClinicalAlertResponse:
    """Clinician acknowledgement of an active CDS alert."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may acknowledge clinical alerts.",
        )

    stmt = select(ClinicalAlert).where(ClinicalAlert.alert_id == alert_id)
    alert = db.execute(stmt).scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical alert '{alert_id}' not found.",
        )

    _validate_patient_vital_access(db, current_user, alert.patient)

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_by_user_id = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)

    if ack_in.notes:
        alert.explanation += f"\n\n[CLINICIAN ACKNOWLEDGEMENT NOTE]: {ack_in.notes.strip()}"

    db.commit()
    db.refresh(alert)

    logger.info("Clinician user_id=%s acknowledged alert %s", current_user.id, alert.alert_id)
    return ClinicalAlertResponse.model_validate(alert)


def dismiss_clinical_alert(
    db: Session,
    alert_id: str,
    dismiss_in: AlertDismissRequest,
    current_user: User,
) -> ClinicalAlertResponse:
    """Clinician dismissal of an alert with mandatory clinical justification."""
    if current_user.role not in (UserRole.DOCTOR, UserRole.HEALTHCARE_STAFF, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clinical staff or administrators may dismiss clinical alerts.",
        )

    if not dismiss_in.reason or len(dismiss_in.reason.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A meaningful clinical dismissal reason (minimum 3 characters) is required.",
        )

    stmt = select(ClinicalAlert).where(ClinicalAlert.alert_id == alert_id)
    alert = db.execute(stmt).scalar_one_or_none()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clinical alert '{alert_id}' not found.",
        )

    _validate_patient_vital_access(db, current_user, alert.patient)

    alert.status = AlertStatus.DISMISSED
    alert.acknowledged_by_user_id = current_user.id
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.dismissal_reason = dismiss_in.reason.strip()

    db.commit()
    db.refresh(alert)

    logger.info("Clinician user_id=%s dismissed alert %s with reason: %s", current_user.id, alert.alert_id, alert.dismissal_reason)
    return ClinicalAlertResponse.model_validate(alert)
