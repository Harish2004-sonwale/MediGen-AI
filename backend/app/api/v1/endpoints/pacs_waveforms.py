"""API endpoints for Phase 9.0.29: DICOM PACS Medical Imaging & Real-Time Multi-Lead ICU Waveforms.

Standards Supported: DICOM QIDO-RS, WADO-RS, 12-Lead ECG Telemetry, Debounced Arrhythmia Alerts.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db, require_roles
from app.models.pacs_waveforms import (
    AlertLifecycleStatus,
    ArrhythmiaAlertEvent,
    DICOMModality,
)
from app.models.user import User
from app.schemas.pacs_waveforms import (
    AILesionFindingResponse,
    AcknowledgeAlertRequest,
    ArrhythmiaAlertResponse,
    ClinicianReviewFindingRequest,
    DICOMStudyCreate,
    DICOMStudyListResponse,
    DICOMStudyResponse,
    ECGSessionCreate,
    ECGSessionListResponse,
    ECGSessionResponse,
)
from app.services.pacs_waveform_service import PACSWaveformService

router = APIRouter()


# ==============================================================================
# DICOM PACS Endpoints (QIDO-RS / WADO-RS)
# ==============================================================================

@router.get("/studies", response_model=DICOMStudyListResponse)
def query_dicom_studies_qido(
    patient_id: Optional[str] = Query(None, description="Patient Identifier filter"),
    modality: Optional[DICOMModality] = Query(None, description="Modality filter (CT, MR, CR, DX, US)"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Executes standards-compliant DICOM QIDO-RS search for imaging studies.
    """
    PACSWaveformService.seed_default_pacs_and_waveforms_if_needed(db)
    studies = PACSWaveformService.query_studies_qido(
        db=db, patient_id=patient_id, modality=modality, limit=limit
    )
    return DICOMStudyListResponse(
        total=len(studies),
        studies=[
            DICOMStudyResponse(
                id=s.id,
                study_instance_uid=s.study_instance_uid,
                study_id=s.study_id,
                patient_id=s.patient_id,
                patient_identifier=s.patient.patient_id if s.patient else None,
                facility_id=s.facility_id,
                accession_number=s.accession_number,
                study_description=s.study_description,
                modality=s.modality,
                body_site=s.body_site,
                study_datetime=s.study_datetime,
                referring_physician=s.referring_physician,
                performing_institution=s.performing_institution,
                number_of_series=s.number_of_series,
                number_of_instances=s.number_of_instances,
                dicom_attributes_json=s.dicom_attributes_json,
                series_list=[
                    {
                        "id": ser.id,
                        "series_instance_uid": ser.series_instance_uid,
                        "study_id": ser.study_id,
                        "series_number": ser.series_number,
                        "series_description": ser.series_description,
                        "modality": ser.modality,
                        "body_part_examined": ser.body_part_examined,
                        "patient_position": ser.patient_position,
                        "slice_thickness_mm": ser.slice_thickness_mm,
                        "pixel_spacing_row_mm": ser.pixel_spacing_row_mm,
                        "pixel_spacing_col_mm": ser.pixel_spacing_col_mm,
                        "window_center_default": ser.window_center_default,
                        "window_width_default": ser.window_width_default,
                        "rescale_intercept": ser.rescale_intercept,
                        "rescale_slope": ser.rescale_slope,
                        "number_of_instances": ser.number_of_instances,
                        "instances": [
                            {
                                "id": inst.id,
                                "sop_instance_uid": inst.sop_instance_uid,
                                "series_id": inst.series_id,
                                "sop_class_uid": inst.sop_class_uid,
                                "instance_number": inst.instance_number,
                                "rows": inst.rows,
                                "columns": inst.columns,
                                "bits_allocated": inst.bits_allocated,
                                "bits_stored": inst.bits_stored,
                                "high_bit": inst.high_bit,
                                "pixel_representation": inst.pixel_representation,
                                "photometric_interpretation": inst.photometric_interpretation,
                                "storage_path": inst.storage_path,
                                "thumbnail_path": inst.thumbnail_path,
                                "pixel_data_preview_url": inst.pixel_data_preview_url,
                                "ai_findings": inst.ai_findings,
                                "created_at": inst.created_at,
                            }
                            for inst in ser.instances
                        ],
                        "created_at": ser.created_at,
                    }
                    for ser in s.series_list
                ],
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in studies
        ],
    )


@router.post("/studies", response_model=DICOMStudyResponse, status_code=status.HTTP_201_CREATED)
def create_dicom_study_stow(
    payload: DICOMStudyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "radiologist"])),
):
    """
    Ingests and registers a new DICOM Study with initial Series and SOP Instance metadata.
    """
    try:
        study = PACSWaveformService.create_dicom_study(
            db=db,
            patient_id=payload.patient_id,
            study_description=payload.study_description,
            modality=payload.modality,
            body_site=payload.body_site,
            facility_id=payload.facility_id or getattr(current_user, "default_facility_id", None),
            accession_number=payload.accession_number,
            study_datetime=payload.study_datetime,
            referring_physician=payload.referring_physician,
            performing_institution=payload.performing_institution,
            series_description=payload.series_description,
        )
        return DICOMStudyResponse.model_validate(study)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/studies/{study_instance_uid}", response_model=DICOMStudyResponse)
def get_dicom_study(
    study_instance_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieves full DICOM Study metadata including Series and Instances for viewer rendering.
    """
    study = PACSWaveformService.get_study_by_uid(db=db, study_instance_uid=study_instance_uid)
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Study '{study_instance_uid}' not found.")
    return DICOMStudyResponse.model_validate(study)


@router.get("/studies/{study_instance_uid}/metadata")
def get_dicom_study_metadata_wado(
    study_instance_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, Any]:
    """
    Returns full DICOM PS3.18 WADO-RS JSON metadata hierarchy for client-side viewers.
    """
    study = PACSWaveformService.get_study_by_uid(db=db, study_instance_uid=study_instance_uid)
    if not study:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DICOM Study not found.")

    return {
        "0020000D": {"vr": "UI", "Value": [study.study_instance_uid]},
        "00080020": {"vr": "DA", "Value": [study.study_datetime.strftime("%Y%m%d")]},
        "00080030": {"vr": "TM", "Value": [study.study_datetime.strftime("%H%M%S")]},
        "00080050": {"vr": "SH", "Value": [study.accession_number]},
        "00080060": {"vr": "CS", "Value": [study.modality.value]},
        "00081030": {"vr": "LO", "Value": [study.study_description]},
        "00100020": {"vr": "LO", "Value": [study.patient.patient_id if study.patient else "ANON"]},
        "Series": [
            {
                "0020000E": {"vr": "UI", "Value": [ser.series_instance_uid]},
                "00200011": {"vr": "IS", "Value": [ser.series_number]},
                "0008103E": {"vr": "LO", "Value": [ser.series_description]},
                "00281050": {"vr": "DS", "Value": [ser.window_center_default]},
                "00281051": {"vr": "DS", "Value": [ser.window_width_default]},
                "00280030": {"vr": "DS", "Value": [f"{ser.pixel_spacing_row_mm}\\{ser.pixel_spacing_col_mm}"]},
                "Instances": [
                    {
                        "00080018": {"vr": "UI", "Value": [inst.sop_instance_uid]},
                        "00200013": {"vr": "IS", "Value": [inst.instance_number]},
                        "00280010": {"vr": "US", "Value": [inst.rows]},
                        "00280011": {"vr": "US", "Value": [inst.columns]},
                        "00280100": {"vr": "US", "Value": [inst.bits_allocated]},
                        "00280101": {"vr": "US", "Value": [inst.bits_stored]},
                    }
                    for inst in ser.instances
                ],
            }
            for ser in study.series_list
        ],
    }


@router.post("/findings/{finding_id}/review", response_model=AILesionFindingResponse)
def review_ai_finding(
    finding_id: str,
    payload: ClinicianReviewFindingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "radiologist"])),
):
    """
    Records clinician confirmation or rejection of an AI vision finding / lesion overlay.
    """
    try:
        finding = PACSWaveformService.review_ai_finding(
            db=db,
            finding_id=finding_id,
            user_id=current_user.id,
            status=payload.status,
            review_notes=payload.review_notes,
        )
        return AILesionFindingResponse.model_validate(finding)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ==============================================================================
# Multi-Lead ICU Waveform Endpoints
# ==============================================================================

@router.get("/waveforms/sessions/{patient_id}", response_model=ECGSessionListResponse)
def get_patient_ecg_sessions(
    patient_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieves multi-lead physiological waveform telemetry sessions for the patient.
    """
    PACSWaveformService.seed_default_pacs_and_waveforms_if_needed(db)
    try:
        sessions = PACSWaveformService.list_ecg_sessions(db=db, patient_id=patient_id, limit=limit)
        return ECGSessionListResponse(
            total=len(sessions),
            sessions=[
                ECGSessionResponse(
                    id=s.id,
                    session_id=s.session_id,
                    patient_id=s.patient_id,
                    patient_identifier=s.patient.patient_id if s.patient else None,
                    facility_id=s.facility_id,
                    encounter_id=s.encounter_id,
                    device_id=s.device_id,
                    lead_configuration=s.lead_configuration,
                    sample_rate_hz=s.sample_rate_hz,
                    amplitude_unit=s.amplitude_unit,
                    start_time=s.start_time,
                    duration_seconds=s.duration_seconds,
                    current_rhythm_state=s.current_rhythm_state,
                    heart_rate_bpm=s.heart_rate_bpm,
                    multi_lead_samples_json=s.multi_lead_samples_json,
                    is_active_streaming=s.is_active_streaming,
                    alerts=[ArrhythmiaAlertResponse.model_validate(a) for a in s.alerts],
                    created_at=s.created_at,
                )
                for s in sessions
            ],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/waveforms/sessions", response_model=ECGSessionResponse, status_code=status.HTTP_201_CREATED)
def ingest_ecg_waveform_session(
    payload: ECGSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "healthcare_staff"])),
):
    """
    Ingests an ICU multi-lead waveform telemetry session and runs debounced arrhythmia detection.
    """
    try:
        session = PACSWaveformService.ingest_ecg_session(
            db=db,
            patient_id=payload.patient_id,
            rhythm_state=payload.rhythm_state,
            heart_rate_bpm=payload.heart_rate_bpm,
            lead_configuration=payload.lead_configuration,
            sample_rate_hz=payload.sample_rate_hz,
            duration_seconds=payload.duration_seconds,
            facility_id=payload.facility_id or getattr(current_user, "default_facility_id", None),
            encounter_id=payload.encounter_id,
            device_id=payload.device_id,
        )
        return ECGSessionResponse(
            id=session.id,
            session_id=session.session_id,
            patient_id=session.patient_id,
            patient_identifier=session.patient.patient_id if session.patient else None,
            facility_id=session.facility_id,
            encounter_id=session.encounter_id,
            device_id=session.device_id,
            lead_configuration=session.lead_configuration,
            sample_rate_hz=session.sample_rate_hz,
            amplitude_unit=session.amplitude_unit,
            start_time=session.start_time,
            duration_seconds=session.duration_seconds,
            current_rhythm_state=session.current_rhythm_state,
            heart_rate_bpm=session.heart_rate_bpm,
            multi_lead_samples_json=session.multi_lead_samples_json,
            is_active_streaming=session.is_active_streaming,
            alerts=[ArrhythmiaAlertResponse.model_validate(a) for a in session.alerts],
            created_at=session.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/waveforms/alerts", response_model=List[ArrhythmiaAlertResponse])
def list_active_arrhythmia_alerts(
    status_filter: Optional[AlertLifecycleStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Lists active or unacknowledged clinical arrhythmia alerts across monitored beds.
    """
    query = db.query(ArrhythmiaAlertEvent)
    if status_filter:
        query = query.filter(ArrhythmiaAlertEvent.status == status_filter)
    alerts = query.order_by(desc(ArrhythmiaAlertEvent.triggered_at)).limit(50).all()
    return [ArrhythmiaAlertResponse.model_validate(a) for a in alerts]


@router.post("/waveforms/alerts/{alert_id}/acknowledge", response_model=ArrhythmiaAlertResponse)
def acknowledge_arrhythmia_alert(
    alert_id: str,
    payload: AcknowledgeAlertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["doctor", "admin", "healthcare_staff"])),
):
    """
    Records clinician acknowledgment and interventions for an ICU arrhythmia alarm.
    """
    try:
        alert = PACSWaveformService.acknowledge_alert(
            db=db,
            alert_id=alert_id,
            user_id=current_user.id,
            clinician_action=payload.clinician_action_taken,
            status=payload.status,
        )
        return ArrhythmiaAlertResponse.model_validate(alert)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
