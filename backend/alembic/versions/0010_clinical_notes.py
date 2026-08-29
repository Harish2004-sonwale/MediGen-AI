"""create clinical notes table for AI scribe and structured documentation

Revision ID: 0010_clinical_notes
Revises: 0009_diagnostic_media
Create Date: 2026-08-29 14:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0010_clinical_notes"
down_revision: Union[str, None] = "0009_diagnostic_media"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clinical_notes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("note_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=True),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("note_type", sa.String(length=50), server_default="soap", nullable=False),
        sa.Column("status", sa.String(length=50), server_default="draft", nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("is_ai_generated", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("requires_clinician_review", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("signed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clinical_notes_id"), "clinical_notes", ["id"], unique=False)
    op.create_index(op.f("ix_clinical_notes_note_id"), "clinical_notes", ["note_id"], unique=True)
    op.create_index(op.f("ix_clinical_notes_patient_id"), "clinical_notes", ["patient_id"], unique=False)
    op.create_index(op.f("ix_clinical_notes_title"), "clinical_notes", ["title"], unique=False)
    op.create_index(op.f("ix_clinical_notes_note_type"), "clinical_notes", ["note_type"], unique=False)
    op.create_index(op.f("ix_clinical_notes_status"), "clinical_notes", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_clinical_notes_status"), table_name="clinical_notes")
    op.drop_index(op.f("ix_clinical_notes_note_type"), table_name="clinical_notes")
    op.drop_index(op.f("ix_clinical_notes_title"), table_name="clinical_notes")
    op.drop_index(op.f("ix_clinical_notes_patient_id"), table_name="clinical_notes")
    op.drop_index(op.f("ix_clinical_notes_note_id"), table_name="clinical_notes")
    op.drop_index(op.f("ix_clinical_notes_id"), table_name="clinical_notes")
    op.drop_table("clinical_notes")
