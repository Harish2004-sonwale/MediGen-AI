"""Create EMPI, C-CDA, and Regional Clinical Pathway tables

Revision ID: 0025_empi_ccda_regional_pathways
Revises: 0024_handoff_concurrency_version
Create Date: 2026-09-01 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0025_empi_ccda_regional_pathways"
down_revision: Union[str, None] = "0024_handoff_concurrency_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. EMPI Tables
    op.create_table(
        "enterprise_patient_identities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("enterprise_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="TENANT-001", nullable=False),
        sa.Column("primary_patient_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("confidence_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enterprise_id"),
    )
    op.create_index("ix_enterprise_patient_identities_enterprise_id", "enterprise_patient_identities", ["enterprise_id"])
    op.create_index("ix_enterprise_patient_identities_primary_patient_id", "enterprise_patient_identities", ["primary_patient_id"])

    op.create_table(
        "patient_identity_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("enterprise_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.String(length=64), nullable=False),
        sa.Column("facility_id", sa.String(length=64), nullable=False),
        sa.Column("link_type", sa.String(length=32), server_default="deterministic_exact", nullable=False),
        sa.Column("match_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["enterprise_id"], ["enterprise_patient_identities.enterprise_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patient_identity_links_enterprise_id", "patient_identity_links", ["enterprise_id"])
    op.create_index("ix_patient_identity_links_patient_id", "patient_identity_links", ["patient_id"])
    op.create_index("ix_patient_identity_links_facility_id", "patient_identity_links", ["facility_id"])

    op.create_table(
        "empi_match_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("review_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id_a", sa.String(length=64), nullable=False),
        sa.Column("patient_id_b", sa.String(length=64), nullable=False),
        sa.Column("facility_id_a", sa.String(length=64), nullable=False),
        sa.Column("facility_id_b", sa.String(length=64), nullable=False),
        sa.Column("enterprise_id_a", sa.String(length=64), nullable=True),
        sa.Column("enterprise_id_b", sa.String(length=64), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("feature_breakdown", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending_review", nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_id"),
    )
    op.create_index("ix_empi_match_reviews_review_id", "empi_match_reviews", ["review_id"])
    op.create_index("ix_empi_match_reviews_status", "empi_match_reviews", ["status"])

    op.create_table(
        "empi_merge_histories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("merge_id", sa.String(length=64), nullable=False),
        sa.Column("target_enterprise_id", sa.String(length=64), nullable=False),
        sa.Column("source_enterprise_id", sa.String(length=64), nullable=False),
        sa.Column("target_patient_id", sa.String(length=64), nullable=False),
        sa.Column("source_patient_id", sa.String(length=64), nullable=False),
        sa.Column("merged_by_user_id", sa.Integer(), nullable=False),
        sa.Column("merge_reason", sa.String(length=255), nullable=False),
        sa.Column("is_reverted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("reverted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("merge_id"),
    )
    op.create_index("ix_empi_merge_histories_merge_id", "empi_merge_histories", ["merge_id"])

    # 2. C-CDA Tables
    op.create_table(
        "ccda_document_exchanges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.String(length=64), nullable=False),
        sa.Column("facility_id", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=64), server_default="continuity_of_care_document", nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_facility", sa.String(length=128), nullable=True),
        sa.Column("destination_facility", sa.String(length=128), nullable=True),
        sa.Column("sha256_hash", sa.String(length=64), nullable=False),
        sa.Column("section_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("parsed_summary_json", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index("ix_ccda_document_exchanges_document_id", "ccda_document_exchanges", ["document_id"])
    op.create_index("ix_ccda_document_exchanges_patient_id", "ccda_document_exchanges", ["patient_id"])
    op.create_index("ix_ccda_document_exchanges_facility_id", "ccda_document_exchanges", ["facility_id"])

    # 3. Regional Clinical Pathway Tables
    op.create_table(
        "regional_clinical_pathways",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pathway_id", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), server_default="TENANT-001", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("target_duration_hours", sa.Integer(), server_default="48", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pathway_id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_regional_clinical_pathways_pathway_id", "regional_clinical_pathways", ["pathway_id"])
    op.create_index("ix_regional_clinical_pathways_code", "regional_clinical_pathways", ["code"])

    op.create_table(
        "pathway_stages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("stage_id", sa.String(length=64), nullable=False),
        sa.Column("pathway_id", sa.String(length=64), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("assigned_facility_id", sa.String(length=64), nullable=True),
        sa.Column("target_duration_minutes", sa.Integer(), server_default="180", nullable=False),
        sa.Column("required_role", sa.String(length=32), server_default="doctor", nullable=False),
        sa.Column("clinical_criteria_json", sa.JSON(), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["pathway_id"], ["regional_clinical_pathways.pathway_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stage_id"),
    )
    op.create_index("ix_pathway_stages_stage_id", "pathway_stages", ["stage_id"])
    op.create_index("ix_pathway_stages_pathway_id", "pathway_stages", ["pathway_id"])

    op.create_table(
        "pathway_milestones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("milestone_id", sa.String(length=64), nullable=False),
        sa.Column("stage_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("criteria_code", sa.String(length=64), nullable=False),
        sa.Column("expected_order_type", sa.String(length=64), nullable=True),
        sa.Column("is_critical", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["stage_id"], ["pathway_stages.stage_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("milestone_id"),
    )
    op.create_index("ix_pathway_milestones_milestone_id", "pathway_milestones", ["milestone_id"])
    op.create_index("ix_pathway_milestones_stage_id", "pathway_milestones", ["stage_id"])

    op.create_table(
        "patient_pathway_enrollments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("enrollment_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.String(length=64), nullable=False),
        sa.Column("pathway_id", sa.String(length=64), nullable=False),
        sa.Column("facility_id", sa.String(length=64), nullable=False),
        sa.Column("current_stage_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_care_team_user_id", sa.Integer(), nullable=True),
        sa.Column("completed_milestones", sa.JSON(), nullable=False),
        sa.Column("variance_notes", sa.Text(), nullable=True),
        sa.Column("has_variance", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["pathway_id"], ["regional_clinical_pathways.pathway_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id"),
    )
    op.create_index("ix_patient_pathway_enrollments_enrollment_id", "patient_pathway_enrollments", ["enrollment_id"])
    op.create_index("ix_patient_pathway_enrollments_patient_id", "patient_pathway_enrollments", ["patient_id"])
    op.create_index("ix_patient_pathway_enrollments_status", "patient_pathway_enrollments", ["status"])

    op.create_table(
        "pathway_stage_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("enrollment_id", sa.String(length=64), nullable=False),
        sa.Column("stage_id", sa.String(length=64), nullable=False),
        sa.Column("facility_id", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("transition_type", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("variance_detected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("variance_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["enrollment_id"], ["patient_pathway_enrollments.enrollment_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_pathway_stage_events_event_id", "pathway_stage_events", ["event_id"])
    op.create_index("ix_pathway_stage_events_enrollment_id", "pathway_stage_events", ["enrollment_id"])


def downgrade() -> None:
    op.drop_table("pathway_stage_events")
    op.drop_table("patient_pathway_enrollments")
    op.drop_table("pathway_milestones")
    op.drop_table("pathway_stages")
    op.drop_table("regional_clinical_pathways")
    op.drop_table("ccda_document_exchanges")
    op.drop_table("empi_merge_histories")
    op.drop_table("empi_match_reviews")
    op.drop_table("patient_identity_links")
    op.drop_table("enterprise_patient_identities")
