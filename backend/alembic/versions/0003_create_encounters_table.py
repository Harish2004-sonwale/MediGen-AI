"""create encounters table

Revision ID: 0003_create_encounters_table
Revises: 0002_create_patients_table
Create Date: 2026-08-28 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003_create_encounters_table"
down_revision: Union[str, None] = "0002_create_patients_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "encounters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("encounter_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("attending_user_id", sa.Integer(), nullable=True),
        sa.Column("encounter_date", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("encounter_type", sa.String(length=50), server_default="initial_consultation", nullable=False),
        sa.Column("chief_complaint", sa.String(length=255), nullable=False),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("assessment", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="completed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["attending_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_encounters_id"), "encounters", ["id"], unique=False)
    op.create_index(op.f("ix_encounters_encounter_id"), "encounters", ["encounter_id"], unique=True)
    op.create_index(op.f("ix_encounters_patient_id"), "encounters", ["patient_id"], unique=False)
    op.create_index(op.f("ix_encounters_attending_user_id"), "encounters", ["attending_user_id"], unique=False)
    op.create_index(op.f("ix_encounters_encounter_date"), "encounters", ["encounter_date"], unique=False)
    op.create_index(op.f("ix_encounters_status"), "encounters", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_encounters_status"), table_name="encounters")
    op.drop_index(op.f("ix_encounters_encounter_date"), table_name="encounters")
    op.drop_index(op.f("ix_encounters_attending_user_id"), table_name="encounters")
    op.drop_index(op.f("ix_encounters_patient_id"), table_name="encounters")
    op.drop_index(op.f("ix_encounters_encounter_id"), table_name="encounters")
    op.drop_index(op.f("ix_encounters_id"), table_name="encounters")
    op.drop_table("encounters")
