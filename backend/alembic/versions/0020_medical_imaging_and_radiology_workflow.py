"""create medical imaging and radiology workflow tables

Revision ID: 0020_medical_imaging_and_radiology_workflow
Revises: 0019_clinical_ai_agents_and_care_coordination
Create Date: 2026-08-30 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0020_medical_imaging_and_radiology_workflow"
down_revision: Union[str, None] = "0019_clinical_ai_agents_and_care_coordination"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create imaging_studies table
    op.create_table(
        "imaging_studies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("study_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("modality", sa.String(length=32), nullable=False),
        sa.Column("body_site", sa.String(length=32), nullable=False),
        sa.Column("study_description", sa.String(length=255), nullable=False),
        sa.Column("accession_number", sa.String(length=64), nullable=False),
        sa.Column("study_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("performing_department", sa.String(length=100), server_default="Radiology & Diagnostic Imaging", nullable=False),
        sa.Column("referring_provider", sa.String(length=150), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="ORDERED", nullable=False),
        sa.Column("source", sa.String(length=50), server_default="PACS_IMPORT", nullable=False),
        sa.Column("external_identifier", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("provenance_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["clinical_orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("study_id"),
        sa.UniqueConstraint("accession_number"),
    )
    op.create_index(op.f("ix_imaging_studies_id"), "imaging_studies", ["id"], unique=False)
    op.create_index(op.f("ix_imaging_studies_study_id"), "imaging_studies", ["study_id"], unique=True)
    op.create_index(op.f("ix_imaging_studies_accession_number"), "imaging_studies", ["accession_number"], unique=True)
    op.create_index(op.f("ix_imaging_studies_patient_id"), "imaging_studies", ["patient_id"], unique=False)
    op.create_index(op.f("ix_imaging_studies_encounter_id"), "imaging_studies", ["encounter_id"], unique=False)
    op.create_index(op.f("ix_imaging_studies_order_id"), "imaging_studies", ["order_id"], unique=False)
    op.create_index(op.f("ix_imaging_studies_modality"), "imaging_studies", ["modality"], unique=False)
    op.create_index(op.f("ix_imaging_studies_body_site"), "imaging_studies", ["body_site"], unique=False)
    op.create_index(op.f("ix_imaging_studies_status"), "imaging_studies", ["status"], unique=False)

    # 2. Create imaging_assets table
    op.create_table(
        "imaging_assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.String(length=64), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("series_instance_uid", sa.String(length=128), nullable=True),
        sa.Column("sop_instance_uid", sa.String(length=128), nullable=True),
        sa.Column("series_number", sa.Integer(), server_default="1", nullable=True),
        sa.Column("instance_number", sa.Integer(), server_default="1", nullable=True),
        sa.Column("series_description", sa.String(length=255), nullable=True),
        sa.Column("modality", sa.String(length=32), nullable=False),
        sa.Column("body_site", sa.String(length=32), nullable=True),
        sa.Column("mime_type", sa.String(length=100), server_default="image/png", nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("thumbnail_storage_path", sa.String(length=500), nullable=True),
        sa.Column("image_dimensions", sa.JSON(), nullable=True),
        sa.Column("dicom_metadata_json", sa.JSON(), nullable=True),
        sa.Column("provenance_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["study_id"], ["imaging_studies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id"),
    )
    op.create_index(op.f("ix_imaging_assets_id"), "imaging_assets", ["id"], unique=False)
    op.create_index(op.f("ix_imaging_assets_asset_id"), "imaging_assets", ["asset_id"], unique=True)
    op.create_index(op.f("ix_imaging_assets_study_id"), "imaging_assets", ["study_id"], unique=False)
    op.create_index(op.f("ix_imaging_assets_series_instance_uid"), "imaging_assets", ["series_instance_uid"], unique=False)
    op.create_index(op.f("ix_imaging_assets_sop_instance_uid"), "imaging_assets", ["sop_instance_uid"], unique=False)

    # 3. Create imaging_findings table
    op.create_table(
        "imaging_findings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("finding_id", sa.String(length=64), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("finding_type", sa.String(length=64), nullable=False),
        sa.Column("anatomical_location", sa.String(length=128), nullable=False),
        sa.Column("laterality", sa.String(length=32), server_default="NOT_APPLICABLE", nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="NORMAL", nullable=False),
        sa.Column("confidence_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("is_critical", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("finding_nature", sa.String(length=32), server_default="AI_GENERATED_FINDING", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("bounding_box_json", sa.JSON(), nullable=True),
        sa.Column("clinician_review_status", sa.String(length=32), server_default="pending_review", nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("provenance_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["study_id"], ["imaging_studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["imaging_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("finding_id"),
    )
    op.create_index(op.f("ix_imaging_findings_id"), "imaging_findings", ["id"], unique=False)
    op.create_index(op.f("ix_imaging_findings_finding_id"), "imaging_findings", ["finding_id"], unique=True)
    op.create_index(op.f("ix_imaging_findings_study_id"), "imaging_findings", ["study_id"], unique=False)
    op.create_index(op.f("ix_imaging_findings_asset_id"), "imaging_findings", ["asset_id"], unique=False)
    op.create_index(op.f("ix_imaging_findings_patient_id"), "imaging_findings", ["patient_id"], unique=False)
    op.create_index(op.f("ix_imaging_findings_finding_type"), "imaging_findings", ["finding_type"], unique=False)
    op.create_index(op.f("ix_imaging_findings_severity"), "imaging_findings", ["severity"], unique=False)
    op.create_index(op.f("ix_imaging_findings_is_critical"), "imaging_findings", ["is_critical"], unique=False)
    op.create_index(op.f("ix_imaging_findings_clinician_review_status"), "imaging_findings", ["clinician_review_status"], unique=False)

    # 4. Create radiology_reports table
    op.create_table(
        "radiology_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.String(length=64), nullable=False),
        sa.Column("study_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="DRAFT", nullable=False),
        sa.Column("clinical_indication", sa.Text(), nullable=False),
        sa.Column("technique", sa.Text(), nullable=False),
        sa.Column("comparison_studies", sa.Text(), server_default="None available.", nullable=False),
        sa.Column("findings", sa.Text(), nullable=False),
        sa.Column("impression", sa.Text(), nullable=False),
        sa.Column("recommendations", sa.Text(), nullable=False),
        sa.Column("critical_findings_summary", sa.Text(), nullable=True),
        sa.Column("is_critical", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ai_assistance_metadata_json", sa.JSON(), nullable=True),
        sa.Column("author_user_id", sa.Integer(), nullable=True),
        sa.Column("signed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amendment_reason", sa.Text(), nullable=True),
        sa.Column("amended_from_report_id", sa.Integer(), nullable=True),
        sa.Column("provenance_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["study_id"], ["imaging_studies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["clinical_orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["amended_from_report_id"], ["radiology_reports.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id"),
    )
    op.create_index(op.f("ix_radiology_reports_id"), "radiology_reports", ["id"], unique=False)
    op.create_index(op.f("ix_radiology_reports_report_id"), "radiology_reports", ["report_id"], unique=True)
    op.create_index(op.f("ix_radiology_reports_study_id"), "radiology_reports", ["study_id"], unique=False)
    op.create_index(op.f("ix_radiology_reports_patient_id"), "radiology_reports", ["patient_id"], unique=False)
    op.create_index(op.f("ix_radiology_reports_status"), "radiology_reports", ["status"], unique=False)
    op.create_index(op.f("ix_radiology_reports_is_critical"), "radiology_reports", ["is_critical"], unique=False)


def downgrade() -> None:
    op.drop_table("radiology_reports")
    op.drop_table("imaging_findings")
    op.drop_table("imaging_assets")
    op.drop_table("imaging_studies")
