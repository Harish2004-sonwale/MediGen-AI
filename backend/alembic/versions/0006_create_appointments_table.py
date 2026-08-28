"""create appointments table

Revision ID: 0006_create_appointments_table
Revises: 0005_add_doctor_department
Create Date: 2026-08-28 17:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006_create_appointments_table"
down_revision: Union[str, None] = "0005_add_doctor_department"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("appointment_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=False),
        sa.Column("appointment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), server_default="30", nullable=False),
        sa.Column("consultation_mode", sa.String(length=50), server_default="in_person", nullable=False),
        sa.Column("reason_for_visit", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="scheduled", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_appointments_id"), "appointments", ["id"], unique=False)
    op.create_index(op.f("ix_appointments_appointment_id"), "appointments", ["appointment_id"], unique=True)
    op.create_index(op.f("ix_appointments_patient_id"), "appointments", ["patient_id"], unique=False)
    op.create_index(op.f("ix_appointments_doctor_id"), "appointments", ["doctor_id"], unique=False)
    op.create_index(op.f("ix_appointments_appointment_date"), "appointments", ["appointment_date"], unique=False)
    op.create_index(op.f("ix_appointments_status"), "appointments", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_appointments_status"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_appointment_date"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_doctor_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_patient_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_appointment_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_id"), table_name="appointments")
    op.drop_table("appointments")
