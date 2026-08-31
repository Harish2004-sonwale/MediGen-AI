"""Service for FHIR Bulk Data Access ($export) Execution and NDJSON Generation."""

from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bulk_export import BulkExportJob
from app.models.care_plan import CarePlan
from app.models.encounter import Encounter
from app.models.order import DiagnosticResult
from app.models.patient import Patient
from app.models.security import (
    AuditAction,
    AuditOutcome,
    ConsentPolicyRule,
    ConsentScope,
    ConsentStatus,
    PatientConsent,
)
from app.schemas.bulk_export import BulkExportRequest
from app.services.audit_service import audit_service
from app.services.fhir_mapper_service import (
    FHIRCarePlanMapper,
    FHIREncounterMapper,
    FHIRObservationMapper,
    FHIRPatientMapper,
)

logger = logging.getLogger("medigen.fhir.bulk_export")

# Base directory for storing generated bulk export NDJSON files
EXPORT_STORAGE_DIR = Path("app_data/bulk_exports")


def init_bulk_export_job(
    db: Session,
    user_id: int,
    request: BulkExportRequest,
    facility_id: Optional[str] = None,
) -> BulkExportJob:
    """Initialize an asynchronous Bulk Export job."""
    job_id = f"EXP-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=48)

    job = BulkExportJob(
        job_id=job_id,
        facility_id=facility_id or "FAC-001",
        user_id=user_id,
        export_type=request.export_type.upper(),
        status="PENDING",
        expires_at=expires_at,
        created_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    logger.info("Initialized bulk export job %s (type=%s)", job_id, request.export_type)
    return job


def execute_bulk_export_sync(
    db: Session,
    job_id: str,
    base_url: str = "http://localhost:8000",
) -> Optional[BulkExportJob]:
    """Synchronously execute extraction and generate NDJSON files for the job."""
    stmt = select(BulkExportJob).where(BulkExportJob.job_id == job_id)
    job = db.execute(stmt).scalars().first()
    if not job:
        return None

    job.status = "PROCESSING"
    db.commit()

    try:
        EXPORT_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        job_dir = EXPORT_STORAGE_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        clean_base = base_url.rstrip("/")
        output_files: List[Dict[str, Any]] = []

        # 1. Export Patients (Evaluating active consent opt-outs & restrictions)
        patients_stmt = select(Patient)
        if job.facility_id:
            patients_stmt = patients_stmt.where(
                (Patient.facility_id == job.facility_id) | (Patient.facility_id.is_(None))
            )
        all_patients = list(db.execute(patients_stmt).scalars().all())

        now_dt = datetime.now(timezone.utc)
        patient_str_ids = [p.patient_id for p in all_patients if p.patient_id]

        restricted_patient_str_ids = set()
        if patient_str_ids:
            consents_stmt = select(PatientConsent).where(
                PatientConsent.patient_id.in_(patient_str_ids),
                PatientConsent.status == ConsentStatus.ACTIVE,
                (PatientConsent.valid_to.is_(None)) | (PatientConsent.valid_to >= now_dt),
            )
            active_consents = list(db.execute(consents_stmt).scalars().all())
            for c in active_consents:
                if c.policy_rule == ConsentPolicyRule.DENY or c.scope == ConsentScope.RESTRICT_EXPORT:
                    restricted_patient_str_ids.add(c.patient_id)

        if restricted_patient_str_ids:
            logger.info(
                "Bulk export job %s: omitted %d patient(s) due to active consent opt-out/restrictions: %s",
                job_id,
                len(restricted_patient_str_ids),
                list(restricted_patient_str_ids),
            )
            try:
                audit_service.emit_audit_event(
                    db=db,
                    action=AuditAction.EXPORT,
                    resource_type="BulkExportJob",
                    resource_id=job_id,
                    user_id=job.user_id,
                    purpose_of_use="BULK_EXPORT",
                    outcome=AuditOutcome.DENIED_NO_CONSENT,
                    metadata={
                        "job_id": job_id,
                        "omitted_patient_count": len(restricted_patient_str_ids),
                        "omitted_patient_ids": list(restricted_patient_str_ids),
                        "reason": "Omitted due to active patient consent restriction directive (RESTRICT_EXPORT / DENY)",
                    },
                )
            except Exception as audit_err:
                logger.warning("Failed to emit consent filtering audit event: %s", audit_err)

        patients = [p for p in all_patients if p.patient_id not in restricted_patient_str_ids]
        patient_ids = {p.id for p in patients}

        patient_file = job_dir / "Patient.ndjson"
        with open(patient_file, "w", encoding="utf-8") as f:
            for p in patients:
                fhir_res = FHIRPatientMapper.to_fhir(p).model_dump(mode="json")
                f.write(json.dumps(fhir_res) + "\n")

        output_files.append({
            "type": "Patient",
            "url": f"{clean_base}/api/v1/fhir/bulk-export/{job_id}/files/Patient.ndjson",
            "count": len(patients),
        })

        # 2. Export Encounters
        encounters_stmt = select(Encounter)
        if job.facility_id:
            encounters_stmt = encounters_stmt.where(
                (Encounter.facility_id == job.facility_id) | (Encounter.facility_id.is_(None))
            )
        encounters = [e for e in db.execute(encounters_stmt).scalars().all() if e.patient_id in patient_ids]
        encounter_file = job_dir / "Encounter.ndjson"
        with open(encounter_file, "w", encoding="utf-8") as f:
            for e in encounters:
                if e.patient:
                    fhir_res = FHIREncounterMapper.to_fhir(e, e.patient).model_dump(mode="json")
                    f.write(json.dumps(fhir_res) + "\n")

        output_files.append({
            "type": "Encounter",
            "url": f"{clean_base}/api/v1/fhir/bulk-export/{job_id}/files/Encounter.ndjson",
            "count": len(encounters),
        })

        # 3. Export Care Plans
        care_plans_stmt = select(CarePlan)
        if job.facility_id:
            care_plans_stmt = care_plans_stmt.where(
                (CarePlan.facility_id == job.facility_id) | (CarePlan.facility_id.is_(None))
            )
        care_plans = [cp for cp in db.execute(care_plans_stmt).scalars().all() if cp.patient_id in patient_ids]
        care_plan_file = job_dir / "CarePlan.ndjson"
        with open(care_plan_file, "w", encoding="utf-8") as f:
            for cp in care_plans:
                pid_str = cp.patient.patient_id if cp.patient else str(cp.patient_id)
                fhir_res = FHIRCarePlanMapper.to_fhir(cp, pid_str).model_dump(mode="json")
                f.write(json.dumps(fhir_res) + "\n")

        output_files.append({
            "type": "CarePlan",
            "url": f"{clean_base}/api/v1/fhir/bulk-export/{job_id}/files/CarePlan.ndjson",
            "count": len(care_plans),
        })

        # 4. Export Observations (Diagnostic Results)
        obs_stmt = select(DiagnosticResult)
        obs_list = [o for o in db.execute(obs_stmt).scalars().all() if o.patient_id in patient_ids]
        obs_file = job_dir / "Observation.ndjson"
        with open(obs_file, "w", encoding="utf-8") as f:
            for o in obs_list:
                pid_str = o.patient.patient_id if o.patient else str(o.patient_id)
                fhir_res = FHIRObservationMapper.to_fhir(
                    observation_id=o.result_id,
                    test_name=o.test_name,
                    patient_id=pid_str,
                    value_quantity=o.numeric_value,
                    unit=o.unit_of_measure,
                    value_string=o.findings_summary,
                    status=o.status if isinstance(o.status, str) else o.status.value if hasattr(o.status, "value") else "final",
                    effective_date=o.resulted_at,
                ).model_dump(mode="json")
                f.write(json.dumps(fhir_res) + "\n")

        output_files.append({
            "type": "Observation",
            "url": f"{clean_base}/api/v1/fhir/bulk-export/{job_id}/files/Observation.ndjson",
            "count": len(obs_list),
        })

        # 5. Export Diagnostic Reports
        diag_file = job_dir / "DiagnosticReport.ndjson"
        with open(diag_file, "w", encoding="utf-8") as f:
            for o in obs_list:
                pid_str = o.patient.patient_id if o.patient else str(o.patient_id)
                report_dict = {
                    "resourceType": "DiagnosticReport",
                    "id": f"REP-{o.result_id}",
                    "status": "final",
                    "code": {"text": o.test_name},
                    "subject": {"reference": f"Patient/{pid_str}"},
                    "effectiveDateTime": o.resulted_at.isoformat() if o.resulted_at else None,
                    "conclusion": o.findings_summary,
                }
                f.write(json.dumps(report_dict) + "\n")

        output_files.append({
            "type": "DiagnosticReport",
            "url": f"{clean_base}/api/v1/fhir/bulk-export/{job_id}/files/DiagnosticReport.ndjson",
            "count": len(obs_list),
        })

        job.status = "COMPLETED"
        job.output_urls_json = output_files
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
        logger.info("Completed bulk export job %s with %d files", job_id, len(output_files))
        return job

    except Exception as exc:
        logger.error("Bulk export job %s failed: %s", job_id, exc)
        job.status = "FAILED"
        job.error_message = str(exc)
        db.commit()
        db.refresh(job)
        return job


def get_bulk_export_job(db: Session, job_id: str) -> Optional[BulkExportJob]:
    """Retrieve job details by job_id."""
    stmt = select(BulkExportJob).where(BulkExportJob.job_id == job_id)
    return db.execute(stmt).scalars().first()


def delete_bulk_export_job(db: Session, job_id: str) -> bool:
    """Cancel or delete a bulk export job and its associated files."""
    job = get_bulk_export_job(db, job_id)
    if not job:
        return False
    job_dir = EXPORT_STORAGE_DIR / job_id
    if job_dir.exists():
        import shutil
        shutil.rmtree(job_dir, ignore_errors=True)
    db.delete(job)
    db.commit()
    return True
