"""add doctor department column and index

Revision ID: 0005_add_doctor_department
Revises: 0004_create_doctors_table
Create Date: 2026-08-28 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_add_doctor_department"
down_revision: Union[str, None] = "0004_create_doctors_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "doctors",
        sa.Column("department", sa.String(length=100), server_default="General Medicine", nullable=False),
    )
    op.create_index(op.f("ix_doctors_department"), "doctors", ["department"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_doctors_department"), table_name="doctors")
    op.drop_column("doctors", "department")
