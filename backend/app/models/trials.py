"""SQLAlchemy models for Clinical Trials, Genomics & Precision Oncology.

Phase 9.0.16: Clinical Trials Matching, Biomarker Precision Oncology & Genomic Treatment Eligibility.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.user import User


class ClinicalTrial(Base):
    """Clinical trial registry entity storing study metadata and target conditions."""

    __tablename__ = "clinical_trials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    trial_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    nct_number: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    official_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sponsor: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(30), nullable=False, default="phase_2", index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="recruiting", index=True)
    disease_condition: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    intervention_name: Mapped[str] = mapped_column(String(255), nullable=False)
    intervention_type: Mapped[str] = mapped_column(String(50), nullable=False, default="targeted_therapy")
    location_sites_json: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    min_age_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_age_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_gender: Mapped[str] = mapped_column(String(20), nullable=False, default="all")
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inclusion_criteria_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exclusion_criteria_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    criteria: Mapped[list["TrialEligibilityCriterion"]] = relationship(
        "TrialEligibilityCriterion", back_populates="trial", cascade="all, delete-orphan"
    )
    matches: Mapped[list["TrialMatch"]] = relationship("TrialMatch", back_populates="trial")


class TrialEligibilityCriterion(Base):
    """Structured eligibility criterion for clinical trial matching."""

    __tablename__ = "trial_eligibility_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    criterion_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    trial_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clinical_trials.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    criterion_type: Mapped[str] = mapped_column(String(20), nullable=False, default="inclusion", index=True)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False, default="==")
    expected_value_str: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    expected_value_num: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expected_value_json: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    trial: Mapped["ClinicalTrial"] = relationship("ClinicalTrial", back_populates="criteria")


class GenomicProfile(Base):
    """Patient genomic / molecular test profile report."""

    __tablename__ = "genomic_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    specimen_type: Mapped[str] = mapped_column(String(80), nullable=False, default="tumor_tissue_biopsy")
    specimen_collected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    test_name: Mapped[str] = mapped_column(String(150), nullable=False)
    sequencing_platform: Mapped[str] = mapped_column(String(100), nullable=False, default="Illumina NGS")
    performing_lab: Mapped[str] = mapped_column(String(150), nullable=False, default="MediGen Genomics Core")
    accession_number: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    tumor_mutation_burden: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    microsatellite_instability_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    overall_interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="final", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    biomarkers: Mapped[list["BiomarkerObservation"]] = relationship(
        "BiomarkerObservation", back_populates="profile", cascade="all, delete-orphan"
    )


class BiomarkerObservation(Base):
    """Structured genomic biomarker alteration or expression observation."""

    __tablename__ = "biomarker_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    observation_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("genomic_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    gene_symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    variant_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    alteration_type: Mapped[str] = mapped_column(String(50), nullable=False, default="missense_mutation")
    hgvs_notation: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    chromosome: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    genomic_position: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_allele: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    alternate_allele: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    zygosity: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    variant_allele_fraction: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pathogenicity: Mapped[str] = mapped_column(String(40), nullable=False, default="tier_1_strong_clinical")
    evidence_level: Mapped[str] = mapped_column(String(20), nullable=False, default="FDA_Level_A")
    clinical_significance: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    numeric_expression_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expression_unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    profile: Mapped["GenomicProfile"] = relationship("GenomicProfile", back_populates="biomarkers")
    patient: Mapped["Patient"] = relationship("Patient")


class TrialMatch(Base):
    """Patient-to-clinical-trial deterministic evaluation match result."""

    __tablename__ = "trial_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    trial_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clinical_trials.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    match_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    matched_criteria_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    failed_criteria_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    unknown_criteria_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    overall_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    provenance_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(20), default="1.0.0", nullable=False)
    clinician_review_status: Mapped[str] = mapped_column(
        String(30), default="pending_review", index=True, nullable=False
    )
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    trial: Mapped["ClinicalTrial"] = relationship("ClinicalTrial", back_populates="matches")
    patient: Mapped["Patient"] = relationship("Patient")
    reviewed_by: Mapped[Optional["User"]] = relationship("User")


class PrecisionTreatmentEligibility(Base):
    """Biomarker-driven precision oncology treatment eligibility assessment."""

    __tablename__ = "precision_treatment_eligibilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    eligibility_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("patients.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    gene_symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    variant_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    recommended_intervention: Mapped[str] = mapped_column(String(255), nullable=False)
    drug_class: Mapped[str] = mapped_column(String(100), nullable=False)
    indication: Mapped[str] = mapped_column(String(150), nullable=False)
    eligibility_status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    evidence_source: Mapped[str] = mapped_column(String(100), nullable=False)
    supporting_observations_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    contraindicating_observations_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    unknown_factors_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    provenance_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    clinician_review_status: Mapped[str] = mapped_column(
        String(30), default="pending_review", index=True, nullable=False
    )
    reviewed_by_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient")
    reviewed_by: Mapped[Optional["User"]] = relationship("User")
