from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.task_worker import get_background_task_provider
from app.api.deps import (
    get_current_active_user,
    require_role,
)
from app.database import get_db
from app.models.user import User, UserRole

from app.schemas.task import BackgroundTask, BackgroundTaskType
from app.schemas.trials import (
    BatchMatchRequest,
    BatchMatchResponse,
    BiomarkerObservationCreate,
    BiomarkerObservationResponse,
    ClinicalTrialCreate,
    ClinicalTrialDetailResponse,
    ClinicalTrialListResponse,
    ClinicalTrialResponse,
    ClinicalTrialUpdate,
    GenomicProfileCreate,
    GenomicProfileDetailResponse,
    GenomicProfileListResponse,
    GenomicProfileResponse,
    PrecisionEligibilityReviewRequest,
    PrecisionTreatmentEligibilityListResponse,
    PrecisionTreatmentEligibilityResponse,
    TrialEligibilityCriterionCreate,
    TrialEligibilityCriterionResponse,
    TrialMatchListResponse,
    TrialMatchResponse,
    TrialMatchReviewRequest,
)
from app.services.trial_matching_service import TrialMatchingService


router = APIRouter(tags=["trials"])
trial_service = TrialMatchingService()


# ==============================================================================
# 1. CLINICAL TRIALS & ELIGIBILITY CRITERIA
# ==============================================================================

@router.post(
    "/trials",
    response_model=ClinicalTrialResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new clinical trial definition",
)
def create_clinical_trial(
    trial_in: ClinicalTrialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> ClinicalTrialResponse:
    """Create a structured clinical trial registry record with optional criteria."""
    try:
        trial = trial_service.create_trial(db, trial_in)
        return trial
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get(
    "/trials",
    response_model=ClinicalTrialListResponse,
    status_code=status.HTTP_200_OK,
    summary="List active clinical trials with query filters",
)
def list_clinical_trials(
    phase: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    condition: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalTrialListResponse:
    """List clinical trials with optional filtering."""
    trial_service.seed_standard_clinical_trials(db)
    items = trial_service.list_trials(
        db,
        phase=phase,
        status=status_filter,
        condition=condition,
        search=search,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )
    return ClinicalTrialListResponse(items=items, total=len(items))


@router.get(
    "/trials/{trial_id}",
    response_model=ClinicalTrialDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get clinical trial detail with eligibility criteria",
)
def get_clinical_trial(
    trial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ClinicalTrialDetailResponse:
    """Retrieve detailed clinical trial record with structured eligibility criteria."""
    trial_service.seed_standard_clinical_trials(db)
    trial = trial_service.get_trial(db, trial_id)
    if not trial:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Trial '{trial_id}' was not found.")
    return trial


@router.patch(
    "/trials/{trial_id}",
    response_model=ClinicalTrialResponse,
    status_code=status.HTTP_200_OK,
    summary="Update clinical trial metadata",
)
def update_clinical_trial(
    trial_id: str,
    trial_update: ClinicalTrialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> ClinicalTrialResponse:
    """Update clinical trial attributes."""
    try:
        return trial_service.update_trial(db, trial_id, trial_update)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/trials/{trial_id}/criteria",
    response_model=TrialEligibilityCriterionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an eligibility criterion to a clinical trial",
)
def add_trial_criterion(
    trial_id: str,
    crit_in: TrialEligibilityCriterionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> TrialEligibilityCriterionResponse:
    """Add a structured inclusion or exclusion criterion to a trial."""
    try:
        return trial_service.add_trial_criterion(db, trial_id, crit_in)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/trials/{trial_id}/criteria",
    response_model=list[TrialEligibilityCriterionResponse],
    status_code=status.HTTP_200_OK,
    summary="List all eligibility criteria for a clinical trial",
)
def list_trial_criteria(
    trial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[TrialEligibilityCriterionResponse]:
    """Retrieve structured criteria for a trial."""
    try:
        return trial_service.list_trial_criteria(db, trial_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ==============================================================================
# 2. PATIENT GENOMIC PROFILES & BIOMARKER OBSERVATIONS
# ==============================================================================

@router.post(
    "/patients/{patient_id}/genomic-profiles",
    response_model=GenomicProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a patient genomic sequencing panel",
)
def create_patient_genomic_profile(
    patient_id: str,
    profile_in: GenomicProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> GenomicProfileResponse:
    """Register a NGS panel report for a patient."""
    try:
        return trial_service.create_genomic_profile(db, patient_id, profile_in)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/patients/{patient_id}/genomic-profiles",
    response_model=GenomicProfileListResponse,
    status_code=status.HTTP_200_OK,
    summary="List genomic profiles for a patient",
)
def list_patient_genomic_profiles(
    patient_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> GenomicProfileListResponse:
    """List genomic sequencing profiles for a patient with RBAC isolation."""
    try:
        patient = trial_service._resolve_patient(db, patient_id)
        if current_user.role == UserRole.PATIENT and patient.email != current_user.email:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to patient profile.")

        profiles = trial_service.list_genomic_profiles(db, patient_id_or_str=patient.id, skip=skip, limit=limit)


        items = []
        for p in profiles:
            p_dict = GenomicProfileDetailResponse.model_validate(p)
            p_dict.patient_identifier = p.patient.patient_id if p.patient else None
            p_dict.patient_name = f"{p.patient.first_name} {p.patient.last_name}" if p.patient else None
            items.append(p_dict)
        return GenomicProfileListResponse(items=items, total=len(items))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/genomic-profiles/{profile_id}",
    response_model=GenomicProfileDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single genomic profile with biomarkers",
)
def get_genomic_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> GenomicProfileDetailResponse:
    """Retrieve detailed genomic profile."""
    profile = trial_service.get_genomic_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Genomic profile '{profile_id}' was not found.")

    if current_user.role == UserRole.PATIENT and profile.patient and profile.patient.email != current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to requested profile.")

    res = GenomicProfileDetailResponse.model_validate(profile)
    res.patient_identifier = profile.patient.patient_id if profile.patient else None
    res.patient_name = f"{profile.patient.first_name} {profile.patient.last_name}" if profile.patient else None
    return res


@router.post(
    "/genomic-profiles/{profile_id}/biomarkers",
    response_model=BiomarkerObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a biomarker alteration observation to a profile",
)
def add_biomarker_observation(
    profile_id: str,
    bm_in: BiomarkerObservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> BiomarkerObservationResponse:
    """Add a structured molecular alteration finding."""
    try:
        return trial_service.add_biomarker_observation(db, profile_id, bm_in)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/genomic-profiles/{profile_id}/biomarkers",
    response_model=list[BiomarkerObservationResponse],
    status_code=status.HTTP_200_OK,
    summary="List biomarker observations in profile",
)
def list_biomarkers_in_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[BiomarkerObservationResponse]:
    """Retrieve biomarker observations for a genomic profile."""
    profile = trial_service.get_genomic_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Profile '{profile_id}' was not found.")

    if current_user.role == UserRole.PATIENT and profile.patient and profile.patient.email != current_user.email:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to biomarkers.")

    return trial_service.list_biomarkers(db, profile_id_or_int=profile.id)


# ==============================================================================
# 3. CLINICAL TRIAL MATCHING & DECISION SUPPORT
# ==============================================================================

@router.post(
    "/trials/{trial_id}/match/{patient_id}",
    response_model=TrialMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Match a specific trial for a patient",
)
def match_patient_to_trial_endpoint(
    trial_id: str,
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> TrialMatchResponse:
    """Run deterministic matching for a patient against a single clinical trial."""
    trial_service.seed_standard_clinical_trials(db)
    try:
        match = trial_service.match_patient_to_trial(db, trial_id, patient_id, current_user.id)
        res = TrialMatchResponse.model_validate(match)
        res.trial_identifier = match.trial.trial_id if match.trial else None
        res.trial_title = match.trial.title if match.trial else None
        res.trial_phase = match.trial.phase if match.trial else None
        res.trial_sponsor = match.trial.sponsor if match.trial else None
        res.disease_condition = match.trial.disease_condition if match.trial else None
        res.intervention_name = match.trial.intervention_name if match.trial else None
        res.patient_identifier = match.patient.patient_id if match.patient else None
        res.patient_name = f"{match.patient.first_name} {match.patient.last_name}" if match.patient else None
        return res
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/patients/{patient_id}/trial-matches",
    response_model=BatchMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Run batch clinical trial matching for patient",
)
def batch_match_patient_endpoint(
    patient_id: str,
    batch_req: Optional[BatchMatchRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> BatchMatchResponse:
    """Run batch matching across all active trials or specified trial IDs."""
    trial_service.seed_standard_clinical_trials(db)
    try:
        trial_ids = batch_req.trial_ids if batch_req else None
        matches = trial_service.batch_match_patient(db, patient_id, trial_ids, current_user.id)

        match_responses: list[TrialMatchResponse] = []
        matched_count = 0
        potential_count = 0
        ineligible_count = 0

        for m in matches:
            mr = TrialMatchResponse.model_validate(m)
            mr.trial_identifier = m.trial.trial_id if m.trial else None
            mr.trial_title = m.trial.title if m.trial else None
            mr.trial_phase = m.trial.phase if m.trial else None
            mr.trial_sponsor = m.trial.sponsor if m.trial else None
            mr.disease_condition = m.trial.disease_condition if m.trial else None
            mr.intervention_name = m.trial.intervention_name if m.trial else None
            mr.patient_identifier = m.patient.patient_id if m.patient else None
            mr.patient_name = f"{m.patient.first_name} {m.patient.last_name}" if m.patient else None
            match_responses.append(mr)

            if m.match_status == "MATCHED":
                matched_count += 1
            elif m.match_status in ("POTENTIAL_MATCH", "MANUAL_REVIEW"):
                potential_count += 1
            elif m.match_status == "INELIGIBLE":
                ineligible_count += 1

        return BatchMatchResponse(
            patient_id=patient_id,
            total_evaluated_trials=len(matches),
            matched_trials_count=matched_count,
            potential_trials_count=potential_count,
            ineligible_trials_count=ineligible_count,
            matches=match_responses,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/patients/{patient_id}/trial-matches",
    response_model=TrialMatchListResponse,
    status_code=status.HTTP_200_OK,
    summary="List clinical trial match scorecards for a patient",
)
def list_patient_trial_matches(
    patient_id: str,
    match_status: Optional[str] = None,
    review_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> TrialMatchListResponse:
    """List evaluated trial match records for a patient with RBAC isolation."""
    try:
        patient = trial_service._resolve_patient(db, patient_id)
        if current_user.role == UserRole.PATIENT and patient.email != current_user.email:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to trial matches.")

        matches = trial_service.list_trial_matches(
            db,
            patient_id_or_str=patient.id,
            match_status=match_status,
            review_status=review_status,
            skip=skip,
            limit=limit,
        )
        items = []
        for m in matches:
            mr = TrialMatchResponse.model_validate(m)
            mr.trial_identifier = m.trial.trial_id if m.trial else None
            mr.trial_title = m.trial.title if m.trial else None
            mr.trial_phase = m.trial.phase if m.trial else None
            mr.trial_sponsor = m.trial.sponsor if m.trial else None
            mr.disease_condition = m.trial.disease_condition if m.trial else None
            mr.intervention_name = m.trial.intervention_name if m.trial else None
            mr.patient_identifier = m.patient.patient_id if m.patient else None
            mr.patient_name = f"{m.patient.first_name} {m.patient.last_name}" if m.patient else None
            mr.reviewed_by_name = m.reviewed_by.name if m.reviewed_by else None
            items.append(mr)

        return TrialMatchListResponse(items=items, total=len(items))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/trial-matches/{match_id}/review",
    response_model=TrialMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Clinician review and sign-off on trial match eligibility",
)
def review_trial_match_endpoint(
    match_id: str,
    review_req: TrialMatchReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> TrialMatchResponse:
    """Document clinician review on trial match eligibility."""
    try:
        match = trial_service.review_trial_match(
            db,
            match_id_or_str=match_id,
            review_status=review_req.clinician_review_status,
            review_notes=review_req.review_notes,
            current_user=current_user,
        )
        mr = TrialMatchResponse.model_validate(match)
        mr.trial_identifier = match.trial.trial_id if match.trial else None
        mr.trial_title = match.trial.title if match.trial else None
        mr.trial_phase = match.trial.phase if match.trial else None
        mr.trial_sponsor = match.trial.sponsor if match.trial else None
        mr.disease_condition = match.trial.disease_condition if match.trial else None
        mr.intervention_name = match.trial.intervention_name if match.trial else None
        mr.patient_identifier = match.patient.patient_id if match.patient else None
        mr.patient_name = f"{match.patient.first_name} {match.patient.last_name}" if match.patient else None
        mr.reviewed_by_name = current_user.name
        return mr
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ==============================================================================
# 4. PRECISION TREATMENT ELIGIBILITY
# ==============================================================================

@router.post(
    "/patients/{patient_id}/precision-eligibility/evaluate",
    response_model=PrecisionTreatmentEligibilityListResponse,
    status_code=status.HTTP_200_OK,
    summary="Synthesize precision oncology treatment eligibility assessments",
)
def evaluate_precision_eligibility_endpoint(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> PrecisionTreatmentEligibilityListResponse:
    """Synthesize assistive precision oncology therapy recommendations based on detected biomarkers."""
    try:
        records = trial_service.evaluate_precision_treatment_eligibility(db, patient_id)
        items = []
        for r in records:
            pr = PrecisionTreatmentEligibilityResponse.model_validate(r)
            pr.patient_identifier = r.patient.patient_id if r.patient else None
            pr.patient_name = f"{r.patient.first_name} {r.patient.last_name}" if r.patient else None
            items.append(pr)
        return PrecisionTreatmentEligibilityListResponse(items=items, total=len(items))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/patients/{patient_id}/precision-eligibility",
    response_model=PrecisionTreatmentEligibilityListResponse,
    status_code=status.HTTP_200_OK,
    summary="List precision oncology treatment eligibility records for a patient",
)
def list_precision_eligibility_endpoint(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PrecisionTreatmentEligibilityListResponse:
    """List precision treatment eligibility records with patient isolation."""
    try:
        patient = trial_service._resolve_patient(db, patient_id)
        if current_user.role == UserRole.PATIENT and patient.email != current_user.email:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to precision eligibility.")

        records = trial_service.list_precision_treatment_eligibilities(db, patient.id)
        items = []
        for r in records:
            pr = PrecisionTreatmentEligibilityResponse.model_validate(r)
            pr.patient_identifier = r.patient.patient_id if r.patient else None
            pr.patient_name = f"{r.patient.first_name} {r.patient.last_name}" if r.patient else None
            pr.reviewed_by_name = r.reviewed_by.name if r.reviewed_by else None
            items.append(pr)
        return PrecisionTreatmentEligibilityListResponse(items=items, total=len(items))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/precision-eligibility/{eligibility_id}/review",
    response_model=PrecisionTreatmentEligibilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Clinician review and signoff on precision oncology recommendation",
)
def review_precision_eligibility_endpoint(
    eligibility_id: str,
    review_req: PrecisionEligibilityReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> PrecisionTreatmentEligibilityResponse:
    """Document clinician review on precision treatment recommendation."""
    try:
        rec = trial_service.review_precision_eligibility(
            db,
            eligibility_id_or_str=eligibility_id,
            review_status=review_req.clinician_review_status,
            review_notes=review_req.review_notes,
            current_user=current_user,
        )
        pr = PrecisionTreatmentEligibilityResponse.model_validate(rec)
        pr.patient_identifier = rec.patient.patient_id if rec.patient else None
        pr.patient_name = f"{rec.patient.first_name} {rec.patient.last_name}" if rec.patient else None
        pr.reviewed_by_name = current_user.name
        return pr
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ==============================================================================
# 5. ASYNCHRONOUS BACKGROUND TASKS
# ==============================================================================

@router.post(
    "/tasks/patients/{patient_id}/trial-matching",
    response_model=BackgroundTask,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Dispatch asynchronous trial matching background task",
)
def enqueue_trial_matching_task(
    patient_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.DOCTOR, UserRole.ADMIN)),
) -> BackgroundTask:

    """Dispatch background task to evaluate clinical trial matching asynchronously."""
    patient = trial_service._resolve_patient(db, patient_id)
    task_provider = get_background_task_provider()
    task = task_provider.submit_task(
        task_type=BackgroundTaskType.TRIAL_MATCHING,
        fn=lambda p_id=patient.patient_id: {"status": "completed", "patient_id": p_id},
        patient_id=patient.patient_id,
        created_by_user_id=current_user.id,
    )
    return task
