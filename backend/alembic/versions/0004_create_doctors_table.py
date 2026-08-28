"""create doctors table

Revision ID: 0004_create_doctors_table
Revises: 0003_create_encounters_table
Create Date: 2026-08-28 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_create_doctors_table"
down_revision: Union[str, None] = "0003_create_encounters_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doctor_id", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("professional_title", sa.String(length=50), server_default="Dr.", nullable=False),
        sa.Column("specialization", sa.String(length=100), nullable=False),
        sa.Column("qualifications", sa.String(length=255), nullable=True),
        sa.Column("medical_degree", sa.String(length=100), nullable=True),
        sa.Column("medical_registration_number", sa.String(length=100), nullable=False),
        sa.Column("years_of_experience", sa.Integer(), server_default="0", nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("clinic_hospital_name", sa.String(length=150), nullable=True),
        sa.Column("consultation_location", sa.String(length=255), nullable=True),
        sa.Column("consultation_mode", sa.String(length=50), server_default="in_person", nullable=False),
        sa.Column("professional_bio", sa.Text(), nullable=True),
        sa.Column("profile_image_url", sa.String(length=500), nullable=True),
        sa.Column("verification_status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("availability_status", sa.String(length=20), server_default="available", nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_doctors_id"), "doctors", ["id"], unique=False)
    op.create_index(op.f("ix_doctors_doctor_id"), "doctors", ["doctor_id"], unique=True)
    op.create_index(op.f("ix_doctors_user_id"), "doctors", ["user_id"], unique=True)
    op.create_index(op.f("ix_doctors_full_name"), "doctors", ["full_name"], unique=False)
    op.create_index(op.f("ix_doctors_specialization"), "doctors", ["specialization"], unique=False)
    op.create_index(op.f("ix_doctors_medical_registration_number"), "doctors", ["medical_registration_number"], unique=True)
    op.create_index(op.f("ix_doctors_verification_status"), "doctors", ["verification_status"], unique=False)
    op.create_index(op.f("ix_doctors_availability_status"), "doctors", ["availability_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_doctors_availability_status"), table_name="doctors")
    op.drop_index(op.f("ix_doctors_verification_status"), table_name="doctors")
    op.drop_index(op.f("ix_doctors_medical_registration_number"), table_name="doctors")
    op.drop_index(op.f("ix_doctors_specialization"), table_name="doctors")
    op.drop_index(op.f("ix_doctors_full_name"), table_name="doctors")
    op.drop_index(op.f("ix_doctors_user_id"), table_name="doctors")
    op.drop_index(op.f("ix_doctors_doctor_id"), table_name="doctors")
    op.drop_index(op.f("ix_doctors_id"), table_name="doctors")
    op.drop_table("doctors")
