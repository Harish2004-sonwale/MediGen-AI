"""API endpoints for Closed-Loop Medication Administration (eMAR) & Barcode Medication Administration (BCMA).

Phase 9.0.28: Closed-Loop eMAR & Barcode Verification (BCMA), 5-Rights Safety Engine, Dual-Clinician High-Alert Signoff.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_roles
from app.models.emar import MARStatus, MedicationBarcodeDirectory
from app.models.user import User
from app.schemas.emar import (
    BCMAVerify5RightsRequest,
    BCMAVerify5RightsResponse,
    DualSignoffRequest,
    MARAdministerRequest,
    MARHoldRefuseRequest,
    MARRecordResponse,
    MARScheduleDosesRequest,
    MARScheduleListResponse,
    MedicationBarcodeCreate,
    MedicationBarcodeListResponse,
    MedicationBarcodeResponse,
)
from app.services.emar_service import EMARService

router = APIRouter()


@router.get("/schedule/{patient_id}", response_model=MARScheduleListResponse)
def get_patient_mar_schedule(
    patient_id: str,
    status_filter: Optional[MARStatus] = Query(None, alias="status", description="Filter by administration status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieves the patient's active Medication Administration Record (eMAR) schedule.
    """
    try:
        records = EMARService.list_patient_mar_schedule(
            db=db, patient_id=patient_id, status=status_filter
        )
        return MARScheduleListResponse(
            total=len(records),
            records=[MARRecordResponse.model_validate(r) for r in records],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/schedule", response_model=List[MARRecordResponse], status_code=status.HTTP_201_CREATED)
def schedule_medication_doses(
    payload: MARScheduleDosesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "healthcare_staff"])),
):
    """
    Schedules future administration time slots on the patient's eMAR.
    """
    try:
        records = EMARService.schedule_medication_doses(
            db=db,
            patient_id=payload.patient_id,
            medication_name=payload.medication_name,
            medication_code=payload.medication_code,
            prescribed_dose=payload.prescribed_dose,
            prescribed_route=payload.prescribed_route,
            frequency_code=payload.frequency_code,
            order_id=payload.order_id,
            facility_id=payload.facility_id or getattr(current_user, "default_facility_id", None),
            start_time=payload.start_time,
            total_doses=payload.total_doses,
            is_high_alert=payload.is_high_alert,
            requires_dual_witness=payload.requires_dual_witness,
        )
        return [MARRecordResponse.model_validate(r) for r in records]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verify-5-rights", response_model=BCMAVerify5RightsResponse)
def verify_5_rights(
    payload: BCMAVerify5RightsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "healthcare_staff"])),
):
    """
    Executes real-time Bedside Barcode Medication Administration (BCMA) 5-Rights Verification.
    """
    try:
        res = EMARService.verify_5_rights(
            db=db,
            patient_id=payload.patient_id,
            scanned_patient_barcode=payload.scanned_patient_barcode,
            scanned_med_barcode=payload.scanned_med_barcode,
            mar_id=payload.mar_id,
            intended_dose=payload.intended_dose,
            intended_route=payload.intended_route,
            user_id=current_user.id,
        )
        return BCMAVerify5RightsResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/records/{mar_id}/administer", response_model=MARRecordResponse)
def administer_medication_dose(
    mar_id: str,
    payload: MARAdministerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "healthcare_staff"])),
):
    """
    Records completed administration of a medication dose on eMAR.
    """
    try:
        record = EMARService.administer_medication(
            db=db,
            mar_id=mar_id,
            administering_nurse_id=current_user.id,
            administered_dose=payload.administered_dose,
            administered_route=payload.administered_route,
            site_of_administration=payload.site_of_administration,
            scanned_patient_barcode=payload.scanned_patient_barcode,
            scanned_med_barcode=payload.scanned_med_barcode,
            vital_signs_pre_admin=payload.vital_signs_pre_admin,
            variance_reason=payload.variance_reason,
            patient_response_notes=payload.patient_response_notes,
        )
        return MARRecordResponse.model_validate(record)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/records/{mar_id}/hold-refuse", response_model=MARRecordResponse)
def hold_or_refuse_dose(
    mar_id: str,
    payload: MARHoldRefuseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "healthcare_staff"])),
):
    """
    Marks a scheduled medication dose as Held or Refused with mandatory clinical justification.
    """
    try:
        record = EMARService.hold_or_refuse_medication(
            db=db,
            mar_id=mar_id,
            nurse_id=current_user.id,
            status=payload.status,
            clinical_reason=payload.clinical_reason,
            patient_response_notes=payload.patient_response_notes,
        )
        return MARRecordResponse.model_validate(record)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/records/{mar_id}/dual-signoff", response_model=MARRecordResponse)
def dual_witness_signoff(
    mar_id: str,
    payload: DualSignoffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "healthcare_staff"])),
):
    """
    Authenticates a second independent clinician witness for High-Alert medication administration.
    """
    try:
        record = EMARService.dual_clinician_witness_signoff(
            db=db,
            mar_id=mar_id,
            witness_user_email=payload.witness_user_email,
            witness_password=payload.witness_password,
            administering_nurse_id=current_user.id,
            witness_notes=payload.witness_notes,
        )
        return MARRecordResponse.model_validate(record)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/barcodes", response_model=MedicationBarcodeListResponse)
def list_barcodes(
    search: Optional[str] = Query(None, description="Search by medication name or barcode"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Lists registered medication package barcodes in the pharmacy directory.
    """
    query = db.query(MedicationBarcodeDirectory).filter(MedicationBarcodeDirectory.is_active.is_(True))
    if search:
        query = query.filter(
            or_(
                MedicationBarcodeDirectory.medication_name.ilike(f"%{search}%"),
                MedicationBarcodeDirectory.barcode.ilike(f"%{search}%"),
                MedicationBarcodeDirectory.rxnorm_code.ilike(f"%{search}%"),
            )
        )
    items = query.all()
    return MedicationBarcodeListResponse(
        total=len(items),
        items=[MedicationBarcodeResponse.model_validate(i) for i in items],
    )


@router.post("/barcodes", response_model=MedicationBarcodeResponse, status_code=status.HTTP_201_CREATED)
def register_barcode(
    payload: MedicationBarcodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin"])),
):
    """
    Registers a new medication package barcode in the pharmacy catalog.
    """
    existing = db.query(MedicationBarcodeDirectory).filter(
        MedicationBarcodeDirectory.barcode == payload.barcode
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Barcode already registered.")

    entry = MedicationBarcodeDirectory(
        barcode=payload.barcode,
        medication_name=payload.medication_name,
        rxnorm_code=payload.rxnorm_code,
        ndc_code=payload.ndc_code,
        standard_dose=payload.standard_dose,
        dosage_form=payload.dosage_form,
        route=payload.route,
        is_high_alert=payload.is_high_alert,
        high_alert_category=payload.high_alert_category,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return MedicationBarcodeResponse.model_validate(entry)
