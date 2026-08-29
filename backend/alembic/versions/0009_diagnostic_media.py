"""create diagnostic media table for multi-modal medical imaging

Revision ID: 0009_diagnostic_media
Revises: 0008_create_chat_sessions_tables
Create Date: 2026-08-29 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0009_diagnostic_media"
down_revision: Union[str, None] = "0008_create_chat_sessions_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "diagnostic_media",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("media_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("uploader_user_id", sa.Integer(), nullable=True),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("modality", sa.String(length=50), server_default="other", nullable=False),
        sa.Column("body_site", sa.String(length=50), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("file_extension", sa.String(length=20), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="uploaded", nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("findings_summary", sa.Text(), nullable=True),
        sa.Column("structured_findings", sa.JSON(), nullable=True),
        sa.Column("anomalies_detected", sa.JSON(), nullable=True),
        sa.Column("requires_clinician_review", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("clinician_confirmed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("clinician_notes", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["uploader_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_diagnostic_media_id"), "diagnostic_media", ["id"], unique=False)
    op.create_index(op.f("ix_diagnostic_media_media_id"), "diagnostic_media", ["media_id"], unique=True)
    op.create_index(op.f("ix_diagnostic_media_patient_id"), "diagnostic_media", ["patient_id"], unique=False)
    op.create_index(op.f("ix_diagnostic_media_title"), "diagnostic_media", ["title"], unique=False)
    op.create_index(op.f("ix_diagnostic_media_modality"), "diagnostic_media", ["modality"], unique=False)
    op.create_index(op.f("ix_diagnostic_media_status"), "diagnostic_media", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_diagnostic_media_status"), table_name="diagnostic_media")
    op.drop_index(op.f("ix_diagnostic_media_modality"), table_name="diagnostic_media")
    op.drop_index(op.f("ix_diagnostic_media_title"), table_name="diagnostic_media")
    op.drop_index(op.f("ix_diagnostic_media_patient_id"), table_name="diagnostic_media")
    op.drop_index(op.f("ix_diagnostic_media_media_id"), table_name="diagnostic_media")
    op.drop_index(op.f("ix_diagnostic_media_id"), table_name="diagnostic_media")
    op.drop_table("diagnostic_media")
