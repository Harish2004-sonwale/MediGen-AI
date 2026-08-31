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
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.schemas.bulk_export import BulkExportRequest
from app.services.fhir_mapper_service import FHIRPatientMapper

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

        output_files: List[Dict[str, Any]] = []

        # 1. Export Patients
        patients_stmt = select(Patient)
        if job.facility_id:
            patients_stmt = patients_stmt.where(
                (Patient.facility_id == job.facility_id) | (Patient.facility_id.is_(None))
            )
        patients = list(db.execute(patients_stmt).scalars().all())

        patient_file = job_dir / "Patient.ndjson"
        with open(patient_file, "w", encoding="utf-8") as f:
            for p in patients:
                fhir_res = FHIRPatientMapper.to_fhir(p).model_dump(mode="json")
                f.write(json.dumps(fhir_res) + "\n")

        clean_base = base_url.rstrip("/")
        output_files.append({
            "type": "Patient",
            "url": f"{clean_base}/api/v1/fhir/bulk-export/{job_id}/files/Patient.ndjson",
            "count": len(patients),
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
