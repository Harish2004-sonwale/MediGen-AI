"""create patients table

Revision ID: 0002_create_patients_table
Revises: 0001_create_users_table
Create Date: 2026-08-28 15:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_create_patients_table"
down_revision: Union[str, None] = "0001_create_users_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("patient_id", sa.String(length=32), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(length=20), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("emergency_contact_name", sa.String(length=100), nullable=True),
        sa.Column("emergency_contact_phone", sa.String(length=30), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patients_id"), "patients", ["id"], unique=False)
    op.create_index(op.f("ix_patients_patient_id"), "patients", ["patient_id"], unique=True)
    op.create_index(op.f("ix_patients_first_name"), "patients", ["first_name"], unique=False)
    op.create_index(op.f("ix_patients_last_name"), "patients", ["last_name"], unique=False)
    op.create_index(op.f("ix_patients_phone"), "patients", ["phone"], unique=False)
    op.create_index(op.f("ix_patients_status"), "patients", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_patients_status"), table_name="patients")
    op.drop_index(op.f("ix_patients_phone"), table_name="patients")
    op.drop_index(op.f("ix_patients_last_name"), table_name="patients")
    op.drop_index(op.f("ix_patients_first_name"), table_name="patients")
    op.drop_index(op.f("ix_patients_patient_id"), table_name="patients")
    op.drop_index(op.f("ix_patients_id"), table_name="patients")
    op.drop_table("patients")
