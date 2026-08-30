"""Pydantic schemas for Clinical Trials, Genomics & Precision Oncology.

Phase 9.0.16: Clinical Trials Matching, Biomarker Precision Oncology & Genomic Treatment Eligibility.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


# ==============================================================================
# ENUMS
# ==============================================================================

class TrialPhase(str, Enum):
    EARLY_PHASE_1 = "early_phase_1"
    PHASE_1 = "phase_1"
    PHASE_1_2 = "phase_1_2"
    PHASE_2 = "phase_2"
    PHASE_2_3 = "phase_2_3"
    PHASE_3 = "phase_3"
    PHASE_4 = "phase_4"


class TrialStatus(str, Enum):
    RECRUITING = "recruiting"
    ACTIVE_NOT_RECRUITING = "active_not_recruiting"
    ENROLLING_BY_INVITATION = "enrolling_by_invitation"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class CriterionType(str, Enum):
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"


class CriterionCategory(str, Enum):
    BIOMARKER = "biomarker"
    DIAGNOSIS = "diagnosis"
    DISEASE_STAGE = "disease_stage"
    AGE = "age"
    PERFORMANCE_STATUS = "performance_status"
    PRIOR_THERAPY = "prior_therapy"
    LABORATORY_VALUE = "laboratory_value"
    ORGAN_FUNCTION = "organ_function"
    CONTRAINDICATION = "contraindication"


class MatchStatus(str, Enum):
    MATCHED = "MATCHED"
    POTENTIAL_MATCH = "POTENTIAL_MATCH"
    INELIGIBLE = "INELIGIBLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class PrecisionEligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class ClinicianReviewStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    CONFIRMED_ELIGIBLE = "confirmed_eligible"
    DECLINED_BY_CLINICIAN = "declined_by_clinician"
    ENROLLED_IN_TRIAL = "enrolled_in_trial"
    PATIENT_DECLINED = "patient_declined"
    APPROVED_FOR_PROTOCOL = "approved_for_protocol"
    REJECTED_BY_CLINICIAN = "rejected_by_clinician"


# ==============================================================================
# ELIGIBILITY CRITERIA SCHEMAS
# ==============================================================================

class TrialEligibilityCriterionBase(BaseModel):
    category: CriterionCategory
    criterion_type: CriterionType = CriterionType.INCLUSION
    field_name: str
    operator: str = "=="
    expected_value_str: Optional[str] = None
    expected_value_num: Optional[float] = None
    expected_value_json: Optional[Any] = None
    unit_of_measure: Optional[str] = None
    is_required: bool = True
    description: str


class TrialEligibilityCriterionCreate(TrialEligibilityCriterionBase):
    pass


class TrialEligibilityCriterionResponse(TrialEligibilityCriterionBase):
    id: int
    criterion_id: str
    trial_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# CLINICAL TRIAL SCHEMAS
# ==============================================================================

class ClinicalTrialBase(BaseModel):
    trial_id: str
    nct_number: Optional[str] = None
    title: str
    official_title: Optional[str] = None
    sponsor: str
    phase: TrialPhase = TrialPhase.PHASE_2
    status: TrialStatus = TrialStatus.RECRUITING
    disease_condition: str
    intervention_name: str
    intervention_type: str = "targeted_therapy"
    location_sites_json: Optional[list[dict[str, Any]]] = None
    min_age_years: Optional[int] = 18
    max_age_years: Optional[int] = None
    target_gender: str = "all"
    summary: Optional[str] = None
    inclusion_criteria_text: Optional[str] = None
    exclusion_criteria_text: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: bool = True
    version: str = "1.0.0"


class ClinicalTrialCreate(ClinicalTrialBase):
    criteria: Optional[list[TrialEligibilityCriterionCreate]] = None


class ClinicalTrialUpdate(BaseModel):
    title: Optional[str] = None
    official_title: Optional[str] = None
    sponsor: Optional[str] = None
    phase: Optional[TrialPhase] = None
    status: Optional[TrialStatus] = None
    disease_condition: Optional[str] = None
    intervention_name: Optional[str] = None
    intervention_type: Optional[str] = None
    location_sites_json: Optional[list[dict[str, Any]]] = None
    min_age_years: Optional[int] = None
    max_age_years: Optional[int] = None
    target_gender: Optional[str] = None
    summary: Optional[str] = None
    inclusion_criteria_text: Optional[str] = None
    exclusion_criteria_text: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None
    version: Optional[str] = None


class ClinicalTrialResponse(ClinicalTrialBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClinicalTrialDetailResponse(ClinicalTrialResponse):
    criteria: list[TrialEligibilityCriterionResponse] = Field(default_factory=list)


class ClinicalTrialListResponse(BaseModel):
    items: list[ClinicalTrialResponse]
    total: int


# ==============================================================================
# BIOMARKER & GENOMIC SCHEMAS
# ==============================================================================

class BiomarkerObservationBase(BaseModel):
    gene_symbol: str
    variant_name: str
    alteration_type: str = "missense_mutation"
    hgvs_notation: Optional[str] = None
    chromosome: Optional[str] = None
    genomic_position: Optional[str] = None
    reference_allele: Optional[str] = None
    alternate_allele: Optional[str] = None
    zygosity: Optional[str] = None
    variant_allele_fraction: Optional[float] = None
    pathogenicity: str = "tier_1_strong_clinical"
    evidence_level: str = "FDA_Level_A"
    clinical_significance: Optional[str] = None
    numeric_expression_value: Optional[float] = None
    expression_unit: Optional[str] = None
    detected_at: Optional[datetime] = None


class BiomarkerObservationCreate(BiomarkerObservationBase):
    pass


class BiomarkerObservationResponse(BiomarkerObservationBase):
    id: int
    observation_id: str
    profile_id: int
    patient_id: int
    detected_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenomicProfileBase(BaseModel):
    specimen_type: str = "tumor_tissue_biopsy"
    specimen_collected_at: Optional[datetime] = None
    test_name: str
    sequencing_platform: str = "Illumina NGS"
    performing_lab: str = "MediGen Genomics Core"
    accession_number: Optional[str] = None
    tumor_mutation_burden: Optional[float] = None
    microsatellite_instability_status: Optional[str] = None
    overall_interpretation: Optional[str] = None
    status: str = "final"


class GenomicProfileCreate(GenomicProfileBase):
    biomarkers: Optional[list[BiomarkerObservationCreate]] = None


class GenomicProfileResponse(GenomicProfileBase):
    id: int
    profile_id: str
    patient_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GenomicProfileDetailResponse(GenomicProfileResponse):
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    biomarkers: list[BiomarkerObservationResponse] = Field(default_factory=list)


class GenomicProfileListResponse(BaseModel):
    items: list[GenomicProfileDetailResponse]
    total: int


# ==============================================================================
# TRIAL MATCH & PRECISION ELIGIBILITY SCHEMAS
# ==============================================================================

class TrialMatchResponse(BaseModel):
    id: int
    match_id: str
    trial_id: int
    trial_identifier: Optional[str] = None
    trial_title: Optional[str] = None
    trial_phase: Optional[str] = None
    trial_sponsor: Optional[str] = None
    disease_condition: Optional[str] = None
    intervention_name: Optional[str] = None
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    match_status: MatchStatus
    match_score: float
    matched_criteria_json: list[dict[str, Any]] = Field(default_factory=list)
    failed_criteria_json: list[dict[str, Any]] = Field(default_factory=list)
    unknown_criteria_json: list[dict[str, Any]] = Field(default_factory=list)
    overall_explanation: str
    provenance_hash: str
    algorithm_version: str
    clinician_review_status: ClinicianReviewStatus
    reviewed_by_user_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrialMatchListResponse(BaseModel):
    items: list[TrialMatchResponse]
    total: int


class TrialMatchReviewRequest(BaseModel):
    clinician_review_status: ClinicianReviewStatus
    review_notes: Optional[str] = None


class PrecisionTreatmentEligibilityResponse(BaseModel):
    id: int
    eligibility_id: str
    patient_id: int
    patient_identifier: Optional[str] = None
    patient_name: Optional[str] = None
    gene_symbol: str
    variant_name: str
    recommended_intervention: str
    drug_class: str
    indication: str
    eligibility_status: PrecisionEligibilityStatus
    evidence_source: str
    supporting_observations_json: list[str] = Field(default_factory=list)
    contraindicating_observations_json: list[str] = Field(default_factory=list)
    unknown_factors_json: list[str] = Field(default_factory=list)
    provenance_hash: str
    clinician_review_status: ClinicianReviewStatus
    reviewed_by_user_id: Optional[int] = None
    reviewed_by_name: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrecisionTreatmentEligibilityListResponse(BaseModel):
    items: list[PrecisionTreatmentEligibilityResponse]
    total: int


class PrecisionEligibilityReviewRequest(BaseModel):
    clinician_review_status: ClinicianReviewStatus
    review_notes: Optional[str] = None


class BatchMatchRequest(BaseModel):
    trial_ids: Optional[list[str]] = None


class BatchMatchResponse(BaseModel):
    patient_id: str
    total_evaluated_trials: int
    matched_trials_count: int
    potential_trials_count: int
    ineligible_trials_count: int
    matches: list[TrialMatchResponse]
