"""Service layer for Clinical Trials Matching, Biomarker Precision Oncology & Genomics.

Phase 9.0.16: Clinical Trials Matching, Biomarker Precision Oncology & Genomic Treatment Eligibility.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.ai.trial_matching_provider import MockTrialMatchingProvider
from app.models.encounter import Encounter
from app.models.order import ClinicalOrder, DiagnosticResult
from app.models.patient import Patient
from app.models.trials import (
    BiomarkerObservation,
    ClinicalTrial,
    GenomicProfile,
    PrecisionTreatmentEligibility,
    TrialEligibilityCriterion,
    TrialMatch,
)
from app.models.user import User, UserRole
from app.schemas.trials import (
    BiomarkerObservationCreate,
    ClinicalTrialCreate,
    ClinicalTrialUpdate,
    ClinicianReviewStatus,
    GenomicProfileCreate,
    TrialEligibilityCriterionCreate,
)

logger = logging.getLogger(__name__)


class TrialMatchingService:
    """Orchestrates trials catalog, genomic profiles, deterministic matching, and precision CDS."""

    def __init__(self, matching_provider: Optional[MockTrialMatchingProvider] = None):
        self.provider = matching_provider or MockTrialMatchingProvider()

    # =========================================================================
    # 1. CLINICAL TRIALS & CRITERIA
    # =========================================================================

    def create_trial(self, db: Session, trial_in: ClinicalTrialCreate) -> ClinicalTrial:
        """Create a new clinical trial entity with optional structured criteria."""
        trial = ClinicalTrial(
            trial_id=trial_in.trial_id,
            nct_number=trial_in.nct_number,
            title=trial_in.title,
            official_title=trial_in.official_title,
            sponsor=trial_in.sponsor,
            phase=trial_in.phase.value if hasattr(trial_in.phase, "value") else str(trial_in.phase),
            status=trial_in.status.value if hasattr(trial_in.status, "value") else str(trial_in.status),
            disease_condition=trial_in.disease_condition,
            intervention_name=trial_in.intervention_name,
            intervention_type=trial_in.intervention_type,
            location_sites_json=trial_in.location_sites_json,
            min_age_years=trial_in.min_age_years,
            max_age_years=trial_in.max_age_years,
            target_gender=trial_in.target_gender,
            summary=trial_in.summary,
            inclusion_criteria_text=trial_in.inclusion_criteria_text,
            exclusion_criteria_text=trial_in.exclusion_criteria_text,
            contact_email=trial_in.contact_email,
            contact_phone=trial_in.contact_phone,
            is_active=trial_in.is_active,
            version=trial_in.version,
        )
        db.add(trial)
        db.flush()

        if trial_in.criteria:
            for idx, c_in in enumerate(trial_in.criteria):
                crit_id = f"CRIT-{trial.trial_id}-{idx + 1:02d}"
                criterion = TrialEligibilityCriterion(
                    criterion_id=crit_id,
                    trial_id=trial.id,
                    category=c_in.category.value if hasattr(c_in.category, "value") else str(c_in.category),
                    criterion_type=c_in.criterion_type.value if hasattr(c_in.criterion_type, "value") else str(c_in.criterion_type),
                    field_name=c_in.field_name,
                    operator=c_in.operator,
                    expected_value_str=c_in.expected_value_str,
                    expected_value_num=c_in.expected_value_num,
                    expected_value_json=c_in.expected_value_json,
                    unit_of_measure=c_in.unit_of_measure,
                    is_required=c_in.is_required,
                    description=c_in.description,
                )
                db.add(criterion)

        db.commit()
        db.refresh(trial)
        return trial

    def get_trial(self, db: Session, trial_id_or_int: Any) -> Optional[ClinicalTrial]:
        """Retrieve clinical trial by integer ID or string trial_id."""
        stmt = select(ClinicalTrial).options(selectinload(ClinicalTrial.criteria))
        if isinstance(trial_id_or_int, int) or str(trial_id_or_int).isdigit():
            stmt = stmt.where(ClinicalTrial.id == int(trial_id_or_int))
        else:
            stmt = stmt.where(ClinicalTrial.trial_id == str(trial_id_or_int))
        return db.execute(stmt).scalar_one_or_none()

    def list_trials(
        self,
        db: Session,
        phase: Optional[str] = None,
        status: Optional[str] = None,
        condition: Optional[str] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ClinicalTrial]:
        """List clinical trials with optional filtering."""
        stmt = select(ClinicalTrial).options(selectinload(ClinicalTrial.criteria))
        if phase:
            stmt = stmt.where(ClinicalTrial.phase == phase)
        if status:
            stmt = stmt.where(ClinicalTrial.status == status)
        if condition:
            stmt = stmt.where(ClinicalTrial.disease_condition.ilike(f"%{condition}%"))
        if search:
            stmt = stmt.where(
                ClinicalTrial.title.ilike(f"%{search}%")
                | ClinicalTrial.trial_id.ilike(f"%{search}%")
                | ClinicalTrial.intervention_name.ilike(f"%{search}%")
            )
        if is_active is not None:
            stmt = stmt.where(ClinicalTrial.is_active == is_active)

        stmt = stmt.order_by(desc(ClinicalTrial.created_at)).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def update_trial(self, db: Session, trial_id_or_int: Any, trial_update: ClinicalTrialUpdate) -> ClinicalTrial:
        """Update clinical trial metadata."""
        trial = self.get_trial(db, trial_id_or_int)
        if not trial:
            raise ValueError(f"Clinical trial '{trial_id_or_int}' was not found.")

        for k, v in trial_update.model_dump(exclude_unset=True).items():
            if hasattr(v, "value"):
                v = v.value
            setattr(trial, k, v)

        db.commit()
        db.refresh(trial)
        return trial

    def add_trial_criterion(
        self, db: Session, trial_id_or_int: Any, crit_in: TrialEligibilityCriterionCreate
    ) -> TrialEligibilityCriterion:
        """Add a structured criterion to a clinical trial."""
        trial = self.get_trial(db, trial_id_or_int)
        if not trial:
            raise ValueError(f"Clinical trial '{trial_id_or_int}' was not found.")

        count_stmt = select(TrialEligibilityCriterion).where(TrialEligibilityCriterion.trial_id == trial.id)
        current_count = len(db.execute(count_stmt).scalars().all())
        crit_id = f"CRIT-{trial.trial_id}-{current_count + 1:02d}"

        criterion = TrialEligibilityCriterion(
            criterion_id=crit_id,
            trial_id=trial.id,
            category=crit_in.category.value if hasattr(crit_in.category, "value") else str(crit_in.category),
            criterion_type=crit_in.criterion_type.value if hasattr(crit_in.criterion_type, "value") else str(crit_in.criterion_type),
            field_name=crit_in.field_name,
            operator=crit_in.operator,
            expected_value_str=crit_in.expected_value_str,
            expected_value_num=crit_in.expected_value_num,
            expected_value_json=crit_in.expected_value_json,
            unit_of_measure=crit_in.unit_of_measure,
            is_required=crit_in.is_required,
            description=crit_in.description,
        )
        db.add(criterion)
        db.commit()
        db.refresh(criterion)
        return criterion

    def list_trial_criteria(self, db: Session, trial_id_or_int: Any) -> list[TrialEligibilityCriterion]:
        """List eligibility criteria for a clinical trial."""
        trial = self.get_trial(db, trial_id_or_int)
        if not trial:
            raise ValueError(f"Clinical trial '{trial_id_or_int}' was not found.")
        stmt = select(TrialEligibilityCriterion).where(TrialEligibilityCriterion.trial_id == trial.id)
        return list(db.execute(stmt).scalars().all())

    # =========================================================================
    # 2. GENOMIC PROFILES & BIOMARKER OBSERVATIONS
    # =========================================================================

    def _resolve_patient(self, db: Session, patient_id_or_str: Any) -> Patient:
        """Resolve Patient entity by integer ID or string patient_id identifier."""
        if isinstance(patient_id_or_str, int) or str(patient_id_or_str).isdigit():
            stmt = select(Patient).where(Patient.id == int(patient_id_or_str))
        else:
            stmt = select(Patient).where(Patient.patient_id == str(patient_id_or_str))
        patient = db.execute(stmt).scalar_one_or_none()
        if not patient:
            raise ValueError(f"Patient '{patient_id_or_str}' was not found.")
        return patient

    def create_genomic_profile(
        self, db: Session, patient_id_or_str: Any, profile_in: GenomicProfileCreate
    ) -> GenomicProfile:
        """Register a patient genomic profile NGS report."""
        patient = self._resolve_patient(db, patient_id_or_str)
        count_stmt = select(GenomicProfile).where(GenomicProfile.patient_id == patient.id)
        profile_count = len(db.execute(count_stmt).scalars().all())
        profile_id = f"GEN-PROF-{patient.patient_id}-{profile_count + 1:02d}"

        profile = GenomicProfile(
            profile_id=profile_id,
            patient_id=patient.id,
            specimen_type=profile_in.specimen_type,
            specimen_collected_at=profile_in.specimen_collected_at,
            test_name=profile_in.test_name,
            sequencing_platform=profile_in.sequencing_platform,
            performing_lab=profile_in.performing_lab,
            accession_number=profile_in.accession_number,
            tumor_mutation_burden=profile_in.tumor_mutation_burden,
            microsatellite_instability_status=profile_in.microsatellite_instability_status,
            overall_interpretation=profile_in.overall_interpretation,
            status=profile_in.status,
        )
        db.add(profile)
        db.flush()

        if profile_in.biomarkers:
            for idx, bm_in in enumerate(profile_in.biomarkers):
                obs_id = f"BM-{profile.profile_id}-{idx + 1:02d}"
                bm = BiomarkerObservation(
                    observation_id=obs_id,
                    profile_id=profile.id,
                    patient_id=patient.id,
                    gene_symbol=bm_in.gene_symbol,
                    variant_name=bm_in.variant_name,
                    alteration_type=bm_in.alteration_type,
                    hgvs_notation=bm_in.hgvs_notation,
                    chromosome=bm_in.chromosome,
                    genomic_position=bm_in.genomic_position,
                    reference_allele=bm_in.reference_allele,
                    alternate_allele=bm_in.alternate_allele,
                    zygosity=bm_in.zygosity,
                    variant_allele_fraction=bm_in.variant_allele_fraction,
                    pathogenicity=bm_in.pathogenicity,
                    evidence_level=bm_in.evidence_level,
                    clinical_significance=bm_in.clinical_significance,
                    numeric_expression_value=bm_in.numeric_expression_value,
                    expression_unit=bm_in.expression_unit,
                    detected_at=bm_in.detected_at or datetime.now(timezone.utc),
                )
                db.add(bm)

        db.commit()
        db.refresh(profile)
        return profile

    def get_genomic_profile(self, db: Session, profile_id_or_int: Any) -> Optional[GenomicProfile]:
        """Retrieve genomic profile by ID with associated biomarkers."""
        stmt = (
            select(GenomicProfile)
            .options(selectinload(GenomicProfile.biomarkers), selectinload(GenomicProfile.patient))
        )
        if isinstance(profile_id_or_int, int) or str(profile_id_or_int).isdigit():
            stmt = stmt.where(GenomicProfile.id == int(profile_id_or_int))
        else:
            stmt = stmt.where(GenomicProfile.profile_id == str(profile_id_or_int))
        return db.execute(stmt).scalar_one_or_none()

    def list_genomic_profiles(
        self, db: Session, patient_id_or_str: Optional[Any] = None, skip: int = 0, limit: int = 50
    ) -> list[GenomicProfile]:
        """List genomic profiles with patient filtering."""
        stmt = (
            select(GenomicProfile)
            .options(selectinload(GenomicProfile.biomarkers), selectinload(GenomicProfile.patient))
            .order_by(desc(GenomicProfile.created_at))
        )
        if patient_id_or_str:
            patient = self._resolve_patient(db, patient_id_or_str)
            stmt = stmt.where(GenomicProfile.patient_id == patient.id)
        return list(db.execute(stmt.offset(skip).limit(limit)).scalars().all())

    def add_biomarker_observation(
        self, db: Session, profile_id_or_int: Any, bm_in: BiomarkerObservationCreate
    ) -> BiomarkerObservation:
        """Add a biomarker alteration observation to an existing genomic profile."""
        profile = self.get_genomic_profile(db, profile_id_or_int)
        if not profile:
            raise ValueError(f"Genomic profile '{profile_id_or_int}' was not found.")

        count_stmt = select(BiomarkerObservation).where(BiomarkerObservation.profile_id == profile.id)
        current_count = len(db.execute(count_stmt).scalars().all())
        obs_id = f"BM-{profile.profile_id}-{current_count + 1:02d}"

        bm = BiomarkerObservation(
            observation_id=obs_id,
            profile_id=profile.id,
            patient_id=profile.patient_id,
            gene_symbol=bm_in.gene_symbol,
            variant_name=bm_in.variant_name,
            alteration_type=bm_in.alteration_type,
            hgvs_notation=bm_in.hgvs_notation,
            chromosome=bm_in.chromosome,
            genomic_position=bm_in.genomic_position,
            reference_allele=bm_in.reference_allele,
            alternate_allele=bm_in.alternate_allele,
            zygosity=bm_in.zygosity,
            variant_allele_fraction=bm_in.variant_allele_fraction,
            pathogenicity=bm_in.pathogenicity,
            evidence_level=bm_in.evidence_level,
            clinical_significance=bm_in.clinical_significance,
            numeric_expression_value=bm_in.numeric_expression_value,
            expression_unit=bm_in.expression_unit,
            detected_at=bm_in.detected_at or datetime.now(timezone.utc),
        )
        db.add(bm)
        db.commit()
        db.refresh(bm)
        return bm

    def list_biomarkers(
        self, db: Session, profile_id_or_int: Optional[Any] = None, patient_id_or_str: Optional[Any] = None
    ) -> list[BiomarkerObservation]:
        """List biomarker observations by profile or patient."""
        stmt = select(BiomarkerObservation).order_by(desc(BiomarkerObservation.detected_at))
        if profile_id_or_int:
            profile = self.get_genomic_profile(db, profile_id_or_int)
            if profile:
                stmt = stmt.where(BiomarkerObservation.profile_id == profile.id)
        if patient_id_or_str:
            patient = self._resolve_patient(db, patient_id_or_str)
            stmt = stmt.where(BiomarkerObservation.patient_id == patient.id)
        return list(db.execute(stmt).scalars().all())

    # =========================================================================
    # 3. CLINICAL TRIAL MATCHING & DECISION SUPPORT
    # =========================================================================

    def _extract_patient_clinical_context(self, db: Session, patient: Patient) -> dict[str, Any]:
        """Aggregate patient diagnoses, age, gender, lab values, staging, and biomarkers."""
        # 1. Demographics & Age
        age = None
        if patient.date_of_birth:
            today = datetime.now(timezone.utc).date()
            dob = patient.date_of_birth.date() if hasattr(patient.date_of_birth, "date") else patient.date_of_birth
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        gender = patient.gender.value if hasattr(patient.gender, "value") else str(patient.gender)

        # 2. Diagnoses & Encounters
        enc_stmt = select(Encounter).where(Encounter.patient_id == patient.id)
        encounters = db.execute(enc_stmt).scalars().all()
        diagnoses: set[str] = set()
        cancer_stage: Optional[str] = None
        prior_therapies: set[str] = set()

        for enc in encounters:
            for text_source in (enc.assessment, enc.chief_complaint, enc.clinical_notes):
                if text_source:
                    diagnoses.add(text_source)
                    # Check for stage in diagnosis string
                    for st in ("Stage IV", "Stage III", "Stage II", "Stage I", "Stage IIIB", "Stage IIIA", "Metastatic"):
                        if st.lower() in text_source.lower():
                            cancer_stage = st
            if enc.plan:
                prior_therapies.add(enc.plan)


        # 3. Biomarkers
        bm_stmt = select(BiomarkerObservation).where(BiomarkerObservation.patient_id == patient.id)
        biomarker_records = db.execute(bm_stmt).scalars().all()
        biomarkers = [
            {
                "gene_symbol": bm.gene_symbol,
                "variant_name": bm.variant_name,
                "alteration_type": bm.alteration_type,
                "pathogenicity": bm.pathogenicity,
                "evidence_level": bm.evidence_level,
                "numeric_expression_value": bm.numeric_expression_value,
                "expression_unit": bm.expression_unit,
            }
            for bm in biomarker_records
        ]

        # 4. Lab Results
        lab_stmt = select(DiagnosticResult).where(DiagnosticResult.patient_id == patient.id)
        lab_records = db.execute(lab_stmt).scalars().all()
        labs: dict[str, float] = {}
        for lr in lab_records:
            if lr.numeric_value is not None:
                labs[lr.test_name.lower().replace(" ", "_")] = lr.numeric_value
                if lr.loinc_code:
                    labs[lr.loinc_code] = lr.numeric_value

        return {
            "patient_id": patient.patient_id,
            "age": age,
            "gender": gender,
            "diagnoses": list(diagnoses),
            "cancer_stage": cancer_stage or "Stage IV",
            "biomarkers": biomarkers,
            "lab_results": labs,
            "prior_therapies": list(prior_therapies),
            "ecog_score": 1,
        }

    def match_patient_to_trial(
        self, db: Session, trial_id_or_int: Any, patient_id_or_str: Any, current_user_id: Optional[int] = None
    ) -> TrialMatch:
        """Deterministically match a single trial for a patient."""
        trial = self.get_trial(db, trial_id_or_int)
        if not trial:
            raise ValueError(f"Clinical trial '{trial_id_or_int}' was not found.")
        patient = self._resolve_patient(db, patient_id_or_str)

        patient_ctx = self._extract_patient_clinical_context(db, patient)

        trial_dict = {
            "trial_id": trial.trial_id,
            "title": trial.title,
            "disease_condition": trial.disease_condition,
            "min_age_years": trial.min_age_years,
            "max_age_years": trial.max_age_years,
            "target_gender": trial.target_gender,
        }

        criteria_list = [
            {
                "criterion_id": c.criterion_id,
                "category": c.category,
                "criterion_type": c.criterion_type,
                "field_name": c.field_name,
                "operator": c.operator,
                "expected_value_str": c.expected_value_str,
                "expected_value_num": c.expected_value_num,
                "expected_value_json": c.expected_value_json,
                "unit_of_measure": c.unit_of_measure,
                "description": c.description,
            }
            for c in trial.criteria
        ]

        eval_result = self.provider.evaluate_trial_match(trial_dict, criteria_list, patient_ctx)

        # Check existing match to update or create
        match_stmt = select(TrialMatch).where(
            TrialMatch.trial_id == trial.id, TrialMatch.patient_id == patient.id
        )
        match = db.execute(match_stmt).scalar_one_or_none()

        if not match:
            match_id = f"TMATCH-{trial.trial_id}-{patient.patient_id}"
            match = TrialMatch(
                match_id=match_id,
                trial_id=trial.id,
                patient_id=patient.id,
                match_status=eval_result["match_status"],
                match_score=eval_result["match_score"],
                matched_criteria_json=eval_result["matched_criteria"],
                failed_criteria_json=eval_result["failed_criteria"],
                unknown_criteria_json=eval_result["unknown_criteria"],
                overall_explanation=eval_result["overall_explanation"],
                provenance_hash=eval_result["provenance_hash"],
                algorithm_version=eval_result["algorithm_version"],
                clinician_review_status="pending_review",
            )
            db.add(match)
        else:
            match.match_status = eval_result["match_status"]
            match.match_score = eval_result["match_score"]
            match.matched_criteria_json = eval_result["matched_criteria"]
            match.failed_criteria_json = eval_result["failed_criteria"]
            match.unknown_criteria_json = eval_result["unknown_criteria"]
            match.overall_explanation = eval_result["overall_explanation"]
            match.provenance_hash = eval_result["provenance_hash"]
            match.algorithm_version = eval_result["algorithm_version"]

        db.commit()
        db.refresh(match)
        return match

    def batch_match_patient(
        self,
        db: Session,
        patient_id_or_str: Any,
        trial_ids: Optional[list[str]] = None,
        current_user_id: Optional[int] = None,
    ) -> list[TrialMatch]:
        """Run batch trial matching across all active trials or specified trial IDs."""
        patient = self._resolve_patient(db, patient_id_or_str)
        stmt = select(ClinicalTrial).where(ClinicalTrial.is_active == True)
        if trial_ids:
            stmt = stmt.where(ClinicalTrial.trial_id.in_(trial_ids))
        trials = db.execute(stmt).scalars().all()

        results: list[TrialMatch] = []
        for tr in trials:
            res = self.match_patient_to_trial(db, tr.id, patient.id, current_user_id)
            results.append(res)
        return results

    def list_trial_matches(
        self,
        db: Session,
        patient_id_or_str: Optional[Any] = None,
        trial_id_or_int: Optional[Any] = None,
        match_status: Optional[str] = None,
        review_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TrialMatch]:
        """List trial matches with relational eager loading."""
        stmt = (
            select(TrialMatch)
            .options(
                selectinload(TrialMatch.trial),
                selectinload(TrialMatch.patient),
                selectinload(TrialMatch.reviewed_by),
            )
            .order_by(desc(TrialMatch.match_score), desc(TrialMatch.created_at))
        )
        if patient_id_or_str:
            patient = self._resolve_patient(db, patient_id_or_str)
            stmt = stmt.where(TrialMatch.patient_id == patient.id)
        if trial_id_or_int:
            trial = self.get_trial(db, trial_id_or_int)
            if trial:
                stmt = stmt.where(TrialMatch.trial_id == trial.id)
        if match_status:
            stmt = stmt.where(TrialMatch.match_status == match_status)
        if review_status:
            stmt = stmt.where(TrialMatch.clinician_review_status == review_status)

        return list(db.execute(stmt.offset(skip).limit(limit)).scalars().all())

    def review_trial_match(
        self,
        db: Session,
        match_id_or_str: Any,
        review_status: ClinicianReviewStatus,
        review_notes: Optional[str],
        current_user: User,
    ) -> TrialMatch:
        """Clinician review and sign-off on trial match eligibility."""
        stmt = (
            select(TrialMatch)
            .options(selectinload(TrialMatch.trial), selectinload(TrialMatch.patient))
            .where(
                TrialMatch.id == int(match_id_or_str)
                if str(match_id_or_str).isdigit()
                else TrialMatch.match_id == str(match_id_or_str)
            )
        )
        match = db.execute(stmt).scalar_one_or_none()
        if not match:
            raise ValueError(f"Trial match '{match_id_or_str}' was not found.")

        match.clinician_review_status = (
            review_status.value if hasattr(review_status, "value") else str(review_status)
        )
        match.review_notes = review_notes
        match.reviewed_by_user_id = current_user.id
        match.reviewed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(match)
        return match

    # =========================================================================
    # 4. PRECISION ONCOLOGY TREATMENT ELIGIBILITY
    # =========================================================================

    def evaluate_precision_treatment_eligibility(
        self, db: Session, patient_id_or_str: Any
    ) -> list[PrecisionTreatmentEligibility]:
        """Synthesize biomarker-driven targeted therapy eligibility assessments."""
        patient = self._resolve_patient(db, patient_id_or_str)
        patient_ctx = self._extract_patient_clinical_context(db, patient)
        evaluations = self.provider.evaluate_precision_treatment_eligibility(
            patient_ctx, patient_ctx.get("biomarkers", [])
        )

        results: list[PrecisionTreatmentEligibility] = []
        for ev in evaluations:
            # Check if existing record exists
            stmt = select(PrecisionTreatmentEligibility).where(
                PrecisionTreatmentEligibility.patient_id == patient.id,
                PrecisionTreatmentEligibility.gene_symbol == ev["gene_symbol"],
                PrecisionTreatmentEligibility.variant_name == ev["variant_name"],
            )
            rec = db.execute(stmt).scalar_one_or_none()
            if not rec:
                elig_id = f"PREC-{patient.patient_id}-{ev['gene_symbol']}-{ev['variant_name']}".replace(" ", "_")
                rec = PrecisionTreatmentEligibility(
                    eligibility_id=elig_id,
                    patient_id=patient.id,
                    gene_symbol=ev["gene_symbol"],
                    variant_name=ev["variant_name"],
                    recommended_intervention=ev["recommended_intervention"],
                    drug_class=ev["drug_class"],
                    indication=ev["indication"],
                    eligibility_status=ev["eligibility_status"],
                    evidence_source=ev["evidence_source"],
                    supporting_observations_json=ev["supporting_observations_json"],
                    contraindicating_observations_json=ev["contraindicating_observations_json"],
                    unknown_factors_json=ev["unknown_factors_json"],
                    provenance_hash=ev["provenance_hash"],
                    clinician_review_status="pending_review",
                )
                db.add(rec)
            else:
                rec.recommended_intervention = ev["recommended_intervention"]
                rec.drug_class = ev["drug_class"]
                rec.indication = ev["indication"]
                rec.eligibility_status = ev["eligibility_status"]
                rec.evidence_source = ev["evidence_source"]
                rec.supporting_observations_json = ev["supporting_observations_json"]
                rec.contraindicating_observations_json = ev["contraindicating_observations_json"]
                rec.unknown_factors_json = ev["unknown_factors_json"]
                rec.provenance_hash = ev["provenance_hash"]

            results.append(rec)

        db.commit()
        for r in results:
            db.refresh(r)
        return results

    def list_precision_treatment_eligibilities(
        self, db: Session, patient_id_or_str: Any
    ) -> list[PrecisionTreatmentEligibility]:
        """List precision treatment eligibility records for a patient."""
        patient = self._resolve_patient(db, patient_id_or_str)
        stmt = (
            select(PrecisionTreatmentEligibility)
            .options(
                selectinload(PrecisionTreatmentEligibility.patient),
                selectinload(PrecisionTreatmentEligibility.reviewed_by),
            )
            .where(PrecisionTreatmentEligibility.patient_id == patient.id)
            .order_by(desc(PrecisionTreatmentEligibility.created_at))
        )
        return list(db.execute(stmt).scalars().all())

    def review_precision_eligibility(
        self,
        db: Session,
        eligibility_id_or_str: Any,
        review_status: ClinicianReviewStatus,
        review_notes: Optional[str],
        current_user: User,
    ) -> PrecisionTreatmentEligibility:
        """Clinician review and signoff on precision therapy eligibility."""
        stmt = (
            select(PrecisionTreatmentEligibility)
            .options(selectinload(PrecisionTreatmentEligibility.patient))
            .where(
                PrecisionTreatmentEligibility.id == int(eligibility_id_or_str)
                if str(eligibility_id_or_str).isdigit()
                else PrecisionTreatmentEligibility.eligibility_id == str(eligibility_id_or_str)
            )
        )
        rec = db.execute(stmt).scalar_one_or_none()
        if not rec:
            raise ValueError(f"Precision eligibility record '{eligibility_id_or_str}' was not found.")

        rec.clinician_review_status = (
            review_status.value if hasattr(review_status, "value") else str(review_status)
        )
        rec.review_notes = review_notes
        rec.reviewed_by_user_id = current_user.id
        rec.reviewed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(rec)
        return rec

    # =========================================================================
    # 5. SEEDING STANDARD ONCOLOGY CLINICAL TRIALS
    # =========================================================================

    def seed_standard_clinical_trials(self, db: Session) -> list[ClinicalTrial]:
        """Pre-seed standard clinical trials into database."""
        trials_to_seed = [
            {
                "trial_id": "TRIAL-LUNG-001",
                "nct_number": "NCT05214589",
                "title": "Phase 2 Study of Next-Gen EGFR TKI in Advanced EGFR L858R NSCLC",
                "official_title": "A Multicenter Phase 2 Open-Label Trial of 4th-Gen EGFR Inhibitor for Advanced Non-Small Cell Lung Cancer",
                "sponsor": "National Cancer Center & MediGen Oncology",
                "phase": "phase_2",
                "status": "recruiting",
                "disease_condition": "Non-Small Cell Lung Cancer",
                "intervention_name": "Next-Gen EGFR TKI (MG-401)",
                "intervention_type": "targeted_therapy",
                "min_age_years": 18,
                "max_age_years": 85,
                "target_gender": "all",
                "summary": "Investigational targeted therapy for patients with metastatic NSCLC harboring activating EGFR mutations.",
                "criteria": [
                    {
                        "category": "diagnosis",
                        "criterion_type": "inclusion",
                        "field_name": "diagnosis",
                        "operator": "==",
                        "expected_value_str": "Non-Small Cell Lung Cancer",
                        "description": "Histologically or cytologically confirmed metastatic Non-Small Cell Lung Cancer",
                        "is_required": True,
                    },
                    {
                        "category": "biomarker",
                        "criterion_type": "inclusion",
                        "field_name": "EGFR",
                        "operator": "PRESENT",
                        "expected_value_str": "EGFR",
                        "expected_value_json": "L858R",
                        "description": "Documented activating EGFR mutation (L858R or Exon 19 Deletion)",
                        "is_required": True,
                    },
                    {
                        "category": "disease_stage",
                        "criterion_type": "inclusion",
                        "field_name": "stage",
                        "operator": ">=",
                        "expected_value_str": "Stage IV",
                        "description": "Locally advanced, recurrent, or metastatic disease (Stage IIIB/IV)",
                        "is_required": True,
                    },
                    {
                        "category": "biomarker",
                        "criterion_type": "exclusion",
                        "field_name": "EGFR",
                        "operator": "ABSENT",
                        "expected_value_str": "EGFR",
                        "expected_value_json": "C797S",
                        "description": "Exclusion: Presence of known C797S resistance mutation",
                        "is_required": True,
                    },
                ],
            },
            {
                "trial_id": "TRIAL-BREAST-002",
                "nct_number": "NCT04899201",
                "title": "Phase 3 Trial of PARP Inhibitor in gBRCA1/2 Metastatic Breast Cancer",
                "official_title": "Randomized Phase 3 Study of Novel Oral PARP Inhibitor vs Standard Chemotherapy in Germline BRCA-Mutated HER2-Negative Metastatic Breast Cancer",
                "sponsor": "International Breast Cancer Research Consortium",
                "phase": "phase_3",
                "status": "recruiting",
                "disease_condition": "Breast Cancer",
                "intervention_name": "Olaparib Combination",
                "intervention_type": "targeted_therapy",
                "min_age_years": 18,
                "max_age_years": 80,
                "target_gender": "all",
                "summary": "Targeted DNA repair synthetic lethality trial for BRCA1/2-deficient metastatic breast malignancy.",
                "criteria": [
                    {
                        "category": "diagnosis",
                        "criterion_type": "inclusion",
                        "field_name": "diagnosis",
                        "operator": "==",
                        "expected_value_str": "Breast Cancer",
                        "description": "Confirmed metastatic or locally advanced breast carcinoma",
                        "is_required": True,
                    },
                    {
                        "category": "biomarker",
                        "criterion_type": "inclusion",
                        "field_name": "BRCA1",
                        "operator": "PRESENT",
                        "expected_value_str": "BRCA1",
                        "description": "Deleterious or suspected deleterious germline or somatic BRCA1/2 mutation",
                        "is_required": True,
                    },
                ],
            },
            {
                "trial_id": "TRIAL-IMMUNO-003",
                "nct_number": "NCT05671122",
                "title": "Phase 1/2 Trial of Bispecific Anti-PD-L1/LAG-3 in High PD-L1 Solid Tumors",
                "official_title": "A Phase 1/2 Dose-Escalation and Expansion Study of Dual Checkpoint Antagonist in Advanced Solid Malignancies with PD-L1 TPS >= 50%",
                "sponsor": "Precision Immuno-Oncology Institute",
                "phase": "phase_1_2",
                "status": "recruiting",
                "disease_condition": "Solid Tumors",
                "intervention_name": "Bispecific Anti-PD-L1/LAG-3 mAb",
                "intervention_type": "immunotherapy",
                "min_age_years": 18,
                "max_age_years": 90,
                "target_gender": "all",
                "summary": "Novel next-generation dual checkpoint immunotherapy for PD-L1 high expressors.",
                "criteria": [
                    {
                        "category": "biomarker",
                        "criterion_type": "inclusion",
                        "field_name": "PD-L1",
                        "operator": ">=",
                        "expected_value_str": "PD-L1",
                        "expected_value_num": 50.0,
                        "unit_of_measure": "%",
                        "description": "PD-L1 expression TPS >= 50% confirmed by IHC 22C3 or SP263 assay",
                        "is_required": True,
                    },
                ],
            },
        ]

        created: list[ClinicalTrial] = []
        for t_data in trials_to_seed:
            existing = self.get_trial(db, t_data["trial_id"])
            if not existing:
                crit_data = t_data.pop("criteria", [])
                trial_obj = ClinicalTrialCreate(**t_data)
                trial = self.create_trial(db, trial_obj)
                for c in crit_data:
                    crit_obj = TrialEligibilityCriterionCreate(**c)
                    self.add_trial_criterion(db, trial.id, crit_obj)
                created.append(trial)
            else:
                created.append(existing)

        return created
