"""create clinical trials genomics and precision oncology tables

Revision ID: 0018_clinical_trials_genomics_precision_oncology
Revises: 0017_rpm_proms_telehealth
Create Date: 2026-08-29 21:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0018_clinical_trials_genomics_precision_oncology"
down_revision: Union[str, None] = "0017_rpm_proms_telehealth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create clinical_trials table
    op.create_table(
        "clinical_trials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("trial_id", sa.String(length=64), nullable=False),
        sa.Column("nct_number", sa.String(length=32), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("official_title", sa.Text(), nullable=True),
        sa.Column("sponsor", sa.String(length=150), nullable=False),
        sa.Column("phase", sa.String(length=30), server_default="phase_2", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="recruiting", nullable=False),
        sa.Column("disease_condition", sa.String(length=150), nullable=False),
        sa.Column("intervention_name", sa.String(length=255), nullable=False),
        sa.Column("intervention_type", sa.String(length=50), server_default="targeted_therapy", nullable=False),
        sa.Column("location_sites_json", sa.JSON(), nullable=True),
        sa.Column("min_age_years", sa.Integer(), nullable=True),
        sa.Column("max_age_years", sa.Integer(), nullable=True),
        sa.Column("target_gender", sa.String(length=20), server_default="all", nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("inclusion_criteria_text", sa.Text(), nullable=True),
        sa.Column("exclusion_criteria_text", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(length=120), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("version", sa.String(length=20), server_default="1.0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clinical_trials_id"), "clinical_trials", ["id"], unique=False)
    op.create_index(op.f("ix_clinical_trials_trial_id"), "clinical_trials", ["trial_id"], unique=True)
    op.create_index(op.f("ix_clinical_trials_nct_number"), "clinical_trials", ["nct_number"], unique=True)
    op.create_index(op.f("ix_clinical_trials_title"), "clinical_trials", ["title"], unique=False)
    op.create_index(op.f("ix_clinical_trials_sponsor"), "clinical_trials", ["sponsor"], unique=False)
    op.create_index(op.f("ix_clinical_trials_phase"), "clinical_trials", ["phase"], unique=False)
    op.create_index(op.f("ix_clinical_trials_status"), "clinical_trials", ["status"], unique=False)
    op.create_index(op.f("ix_clinical_trials_disease_condition"), "clinical_trials", ["disease_condition"], unique=False)

    # 2. Create trial_eligibility_criteria table
    op.create_table(
        "trial_eligibility_criteria",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("criterion_id", sa.String(length=64), nullable=False),
        sa.Column("trial_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("criterion_type", sa.String(length=20), server_default="inclusion", nullable=False),
        sa.Column("field_name", sa.String(length=80), nullable=False),
        sa.Column("operator", sa.String(length=20), server_default="==", nullable=False),
        sa.Column("expected_value_str", sa.String(length=255), nullable=True),
        sa.Column("expected_value_num", sa.Float(), nullable=True),
        sa.Column("expected_value_json", sa.JSON(), nullable=True),
        sa.Column("unit_of_measure", sa.String(length=30), nullable=True),
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["trial_id"], ["clinical_trials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trial_eligibility_criteria_id"), "trial_eligibility_criteria", ["id"], unique=False)
    op.create_index(op.f("ix_trial_eligibility_criteria_criterion_id"), "trial_eligibility_criteria", ["criterion_id"], unique=True)
    op.create_index(op.f("ix_trial_eligibility_criteria_trial_id"), "trial_eligibility_criteria", ["trial_id"], unique=False)
    op.create_index(op.f("ix_trial_eligibility_criteria_category"), "trial_eligibility_criteria", ["category"], unique=False)
    op.create_index(op.f("ix_trial_eligibility_criteria_criterion_type"), "trial_eligibility_criteria", ["criterion_type"], unique=False)

    # 3. Create genomic_profiles table
    op.create_table(
        "genomic_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("specimen_type", sa.String(length=80), server_default="tumor_tissue_biopsy", nullable=False),
        sa.Column("specimen_collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("test_name", sa.String(length=150), nullable=False),
        sa.Column("sequencing_platform", sa.String(length=100), server_default="Illumina NGS", nullable=False),
        sa.Column("performing_lab", sa.String(length=150), server_default="MediGen Genomics Core", nullable=False),
        sa.Column("accession_number", sa.String(length=80), nullable=True),
        sa.Column("tumor_mutation_burden", sa.Float(), nullable=True),
        sa.Column("microsatellite_instability_status", sa.String(length=30), nullable=True),
        sa.Column("overall_interpretation", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="final", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_genomic_profiles_id"), "genomic_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_genomic_profiles_profile_id"), "genomic_profiles", ["profile_id"], unique=True)
    op.create_index(op.f("ix_genomic_profiles_patient_id"), "genomic_profiles", ["patient_id"], unique=False)

    # 4. Create biomarker_observations table
    op.create_table(
        "biomarker_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("observation_id", sa.String(length=64), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("gene_symbol", sa.String(length=50), nullable=False),
        sa.Column("variant_name", sa.String(length=100), nullable=False),
        sa.Column("alteration_type", sa.String(length=50), server_default="missense_mutation", nullable=False),
        sa.Column("hgvs_notation", sa.String(length=120), nullable=True),
        sa.Column("chromosome", sa.String(length=10), nullable=True),
        sa.Column("genomic_position", sa.String(length=50), nullable=True),
        sa.Column("reference_allele", sa.String(length=50), nullable=True),
        sa.Column("alternate_allele", sa.String(length=50), nullable=True),
        sa.Column("zygosity", sa.String(length=30), nullable=True),
        sa.Column("variant_allele_fraction", sa.Float(), nullable=True),
        sa.Column("pathogenicity", sa.String(length=40), server_default="tier_1_strong_clinical", nullable=False),
        sa.Column("evidence_level", sa.String(length=20), server_default="FDA_Level_A", nullable=False),
        sa.Column("clinical_significance", sa.Text(), nullable=True),
        sa.Column("numeric_expression_value", sa.Float(), nullable=True),
        sa.Column("expression_unit", sa.String(length=20), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["genomic_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_biomarker_observations_id"), "biomarker_observations", ["id"], unique=False)
    op.create_index(op.f("ix_biomarker_observations_observation_id"), "biomarker_observations", ["observation_id"], unique=True)
    op.create_index(op.f("ix_biomarker_observations_profile_id"), "biomarker_observations", ["profile_id"], unique=False)
    op.create_index(op.f("ix_biomarker_observations_patient_id"), "biomarker_observations", ["patient_id"], unique=False)
    op.create_index(op.f("ix_biomarker_observations_gene_symbol"), "biomarker_observations", ["gene_symbol"], unique=False)
    op.create_index(op.f("ix_biomarker_observations_variant_name"), "biomarker_observations", ["variant_name"], unique=False)

    # 5. Create trial_matches table
    op.create_table(
        "trial_matches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.String(length=64), nullable=False),
        sa.Column("trial_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("match_status", sa.String(length=30), nullable=False),
        sa.Column("match_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("matched_criteria_json", sa.JSON(), nullable=False),
        sa.Column("failed_criteria_json", sa.JSON(), nullable=False),
        sa.Column("unknown_criteria_json", sa.JSON(), nullable=False),
        sa.Column("overall_explanation", sa.Text(), nullable=False),
        sa.Column("provenance_hash", sa.String(length=64), nullable=False),
        sa.Column("algorithm_version", sa.String(length=20), server_default="1.0.0", nullable=False),
        sa.Column("clinician_review_status", sa.String(length=30), server_default="pending_review", nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["trial_id"], ["clinical_trials.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trial_matches_id"), "trial_matches", ["id"], unique=False)
    op.create_index(op.f("ix_trial_matches_match_id"), "trial_matches", ["match_id"], unique=True)
    op.create_index(op.f("ix_trial_matches_trial_id"), "trial_matches", ["trial_id"], unique=False)
    op.create_index(op.f("ix_trial_matches_patient_id"), "trial_matches", ["patient_id"], unique=False)
    op.create_index(op.f("ix_trial_matches_match_status"), "trial_matches", ["match_status"], unique=False)
    op.create_index(op.f("ix_trial_matches_clinician_review_status"), "trial_matches", ["clinician_review_status"], unique=False)

    # 6. Create precision_treatment_eligibilities table
    op.create_table(
        "precision_treatment_eligibilities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("eligibility_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("gene_symbol", sa.String(length=50), nullable=False),
        sa.Column("variant_name", sa.String(length=100), nullable=False),
        sa.Column("recommended_intervention", sa.String(length=255), nullable=False),
        sa.Column("drug_class", sa.String(length=100), nullable=False),
        sa.Column("indication", sa.String(length=150), nullable=False),
        sa.Column("eligibility_status", sa.String(length=30), nullable=False),
        sa.Column("evidence_source", sa.String(length=100), nullable=False),
        sa.Column("supporting_observations_json", sa.JSON(), nullable=False),
        sa.Column("contraindicating_observations_json", sa.JSON(), nullable=False),
        sa.Column("unknown_factors_json", sa.JSON(), nullable=False),
        sa.Column("provenance_hash", sa.String(length=64), nullable=False),
        sa.Column("clinician_review_status", sa.String(length=30), server_default="pending_review", nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_precision_treatment_eligibilities_id"), "precision_treatment_eligibilities", ["id"], unique=False)
    op.create_index(op.f("ix_precision_treatment_eligibilities_eligibility_id"), "precision_treatment_eligibilities", ["eligibility_id"], unique=True)
    op.create_index(op.f("ix_precision_treatment_eligibilities_patient_id"), "precision_treatment_eligibilities", ["patient_id"], unique=False)
    op.create_index(op.f("ix_precision_treatment_eligibilities_gene_symbol"), "precision_treatment_eligibilities", ["gene_symbol"], unique=False)
    op.create_index(op.f("ix_precision_treatment_eligibilities_variant_name"), "precision_treatment_eligibilities", ["variant_name"], unique=False)
    op.create_index(op.f("ix_precision_treatment_eligibilities_eligibility_status"), "precision_treatment_eligibilities", ["eligibility_status"], unique=False)
    op.create_index(op.f("ix_precision_treatment_eligibilities_clinician_review_status"), "precision_treatment_eligibilities", ["clinician_review_status"], unique=False)


def downgrade() -> None:
    op.drop_table("precision_treatment_eligibilities")
    op.drop_table("trial_matches")
    op.drop_table("biomarker_observations")
    op.drop_table("genomic_profiles")
    op.drop_table("trial_eligibility_criteria")
    op.drop_table("clinical_trials")
