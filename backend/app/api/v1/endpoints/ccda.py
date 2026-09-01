"""FastAPI Endpoints for HL7 C-CDA R2.1 Document Generation, Export, and Ingestion."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_roles
from app.models.user import User, UserRole
from app.schemas.ccda import (
    CCDADocumentListResponse,
    CCDAExportRequest,
    CCDAExportResponse,
    CCDAImportRequest,
    CCDAImportResponse,
)
from app.services.ccda_service import ccda_service

router = APIRouter(prefix="/ccda", tags=["C-CDA Interoperability"])


@router.post(
    "/export",
    response_model=CCDAExportResponse,
    summary="Export a patient clinical summary as HL7 C-CDA R2.1 XML",
)
def export_ccda(
    req: CCDAExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN, UserRole.HEALTHCARE_STAFF])),
) -> CCDAExportResponse:
    """Generate a schema-compliant C-CDA XML document (CCD, Referral Note, or Discharge Summary)."""
    try:
        return ccda_service.export_ccda_document(
            db=db,
            patient_id=req.patient_id,
            document_type=req.document_type,
            destination_facility=req.destination_facility_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/export/{patient_id}/xml",
    summary="Download raw C-CDA XML document directly",
)
def download_ccda_xml(
    patient_id: str,
    document_type: str = Query("continuity_of_care_document"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """Generate and return raw XML content with application/xml MIME type."""
    try:
        res = ccda_service.export_ccda_document(
            db=db,
            patient_id=patient_id,
            document_type=document_type,
            user_id=current_user.id,
        )
        return Response(
            content=res.xml_content,
            media_type="application/xml",
            headers={"Content-Disposition": f'attachment; filename="ccda_{patient_id}.xml"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/import",
    response_model=CCDAImportResponse,
    summary="Ingest and parse external C-CDA R2.1 XML safely",
)
def import_ccda(
    req: CCDAImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.DOCTOR, UserRole.ADMIN, UserRole.HEALTHCARE_STAFF])),
) -> CCDAImportResponse:
    """Parse inbound external C-CDA XML with XXE-safe parsing and extract structured sections."""
    try:
        return ccda_service.import_ccda_document(
            db=db,
            patient_id=req.patient_id,
            xml_content=req.xml_content,
            source_facility=req.source_facility,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/documents",
    response_model=CCDADocumentListResponse,
    summary="List exchanged C-CDA documents",
)
def list_ccda_documents(
    patient_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CCDADocumentListResponse:
    """List document exchange audit records for a patient or health system."""
    items = ccda_service.list_documents(db=db, patient_id=patient_id)
    return CCDADocumentListResponse(total=len(items), items=items)
