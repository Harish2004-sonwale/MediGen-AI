"""API Endpoints for FHIR Bulk Data Access ($export)."""

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, require_role
from app.database import get_db
from app.models.user import User
from app.schemas.bulk_export import (
    BulkExportJobResponse,
    BulkExportRequest,
    BulkExportStatusResponse,
)
from app.schemas.user import UserRole
from app.services import bulk_export_service

router = APIRouter(prefix="/fhir", tags=["FHIR Bulk Data Export ($export)"])


@router.post("/Patient/$export", status_code=status.HTTP_202_ACCEPTED, summary="Initiate Patient-level Bulk Data Export")
def initiate_patient_bulk_export(
    request: Request,
    response: Response,
    _since: Optional[datetime] = Query(None, alias="_since"),
    _type: Optional[str] = Query(None, alias="_type"),
    prefer: Optional[str] = Header("respond-async", alias="Prefer"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> dict[str, str]:
    """Kick off an asynchronous Bulk FHIR export job."""
    types_list = [t.strip() for t in _type.split(",")] if _type else None
    export_req = BulkExportRequest(
        export_type="PATIENT",
        since=_since,
        types=types_list,
    )
    job = bulk_export_service.init_bulk_export_job(
        db=db,
        user_id=current_user.id,
        request=export_req,
        facility_id=current_user.default_facility_id or "FAC-001",
    )

    # Trigger synchronous or async execution
    base_url = str(request.base_url).rstrip("/")
    bulk_export_service.execute_bulk_export_sync(db, job.job_id, base_url=base_url)

    status_url = f"{base_url}/api/v1/fhir/bulk-export/{job.job_id}/status"
    response.headers["Content-Location"] = status_url
    return {
        "status": "Accepted",
        "job_id": job.job_id,
        "content_location": status_url,
    }


@router.get("/bulk-export/{job_id}/status", summary="Poll Bulk Export Status")
def poll_bulk_export_status(
    job_id: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> BulkExportStatusResponse:
    """Poll status of an asynchronous bulk export job."""
    job = bulk_export_service.get_bulk_export_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bulk export job not found")

    if job.status in ("PENDING", "PROCESSING"):
        response.status_code = status.HTTP_202_ACCEPTED
        response.headers["X-Progress"] = "50%"
        return BulkExportStatusResponse(
            transaction_time=job.created_at,
            request_url=str(request.url),
            progress="In progress",
        )

    if job.status == "FAILED":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk export failed: {job.error_message}",
        )

    # Completed status (HTTP 200 OK)
    output_files = [
        {"type": f["type"], "url": f["url"], "count": f.get("count")}
        for f in (job.output_urls_json or [])
    ]
    return BulkExportStatusResponse(
        transaction_time=job.completed_at or datetime.now(timezone.utc),
        request_url=str(request.url),
        output=output_files,
        error=[],
    )


@router.get("/bulk-export/{job_id}/files/{filename}", summary="Download Bulk Export NDJSON File")
def download_bulk_export_file(
    job_id: str,
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FileResponse:
    """Download the generated NDJSON export file."""
    file_path = bulk_export_service.EXPORT_STORAGE_DIR / job_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export file not found")
    return FileResponse(
        path=str(file_path),
        media_type="application/fhir+ndjson",
        filename=filename,
    )


@router.delete("/bulk-export/{job_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Cancel/Delete Bulk Export Job")
def delete_bulk_export(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> None:
    """Cancel or delete an export job."""
    deleted = bulk_export_service.delete_bulk_export_job(db, job_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
