"""create clinical handoffs and discharge protocols tables

Revision ID: 0014_transitions_and_discharge_protocols
Revises: 0013_cohorts_and_risk_stratification
Create Date: 2026-08-29 17:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0014_transitions_and_discharge_protocols"
down_revision: Union[str, None] = "0013_cohorts_and_risk_stratification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create clinical_handoffs table
    op.create_table(
        "clinical_handoffs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("handoff_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("sender_user_id", sa.Integer(), nullable=True),
        sa.Column("receiver_user_id", sa.Integer(), nullable=True),
        sa.Column("framework", sa.String(length=20), server_default="ipass", nullable=False),
        sa.Column("handoff_type", sa.String(length=30), server_default="shift_change", nullable=False),
        sa.Column("illness_severity", sa.String(length=20), server_default="stable", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("action_items_json", sa.JSON(), nullable=True),
        sa.Column("situational_awareness_json", sa.JSON(), nullable=True),
        sa.Column("synthesis_notes", sa.Text(), nullable=True),
        sa.Column("is_ai_generated", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["receiver_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clinical_handoffs_id"), "clinical_handoffs", ["id"], unique=False)
    op.create_index(op.f("ix_clinical_handoffs_handoff_id"), "clinical_handoffs", ["handoff_id"], unique=True)
    op.create_index(op.f("ix_clinical_handoffs_patient_id"), "clinical_handoffs", ["patient_id"], unique=False)
    op.create_index(op.f("ix_clinical_handoffs_encounter_id"), "clinical_handoffs", ["encounter_id"], unique=False)
    op.create_index(op.f("ix_clinical_handoffs_status"), "clinical_handoffs", ["status"], unique=False)

    # 2. Create discharge_protocols table
    op.create_table(
        "discharge_protocols",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("discharge_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("attending_user_id", sa.Integer(), nullable=True),
        sa.Column("nurse_user_id", sa.Integer(), nullable=True),
        sa.Column("pharmacist_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("disposition", sa.String(length=40), server_default="home_self_care", nullable=False),
        sa.Column("discharge_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hospital_course_summary", sa.Text(), nullable=False),
        sa.Column("primary_discharge_diagnosis", sa.String(length=255), nullable=False),
        sa.Column("secondary_diagnoses_json", sa.JSON(), nullable=True),
        sa.Column("medication_reconciliation_json", sa.JSON(), nullable=True),
        sa.Column("followup_instructions_json", sa.JSON(), nullable=True),
        sa.Column("pending_tests_json", sa.JSON(), nullable=True),
        sa.Column("warning_symptoms_json", sa.JSON(), nullable=True),
        sa.Column("activity_and_diet_instructions", sa.Text(), nullable=True),
        sa.Column("is_ai_generated", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("signed_off_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["attending_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["nurse_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["pharmacist_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_discharge_protocols_id"), "discharge_protocols", ["id"], unique=False)
    op.create_index(op.f("ix_discharge_protocols_discharge_id"), "discharge_protocols", ["discharge_id"], unique=True)
    op.create_index(op.f("ix_discharge_protocols_patient_id"), "discharge_protocols", ["patient_id"], unique=False)
    op.create_index(op.f("ix_discharge_protocols_encounter_id"), "discharge_protocols", ["encounter_id"], unique=False)
    op.create_index(op.f("ix_discharge_protocols_status"), "discharge_protocols", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_discharge_protocols_status"), table_name="discharge_protocols")
    op.drop_index(op.f("ix_discharge_protocols_encounter_id"), table_name="discharge_protocols")
    op.drop_index(op.f("ix_discharge_protocols_patient_id"), table_name="discharge_protocols")
    op.drop_index(op.f("ix_discharge_protocols_discharge_id"), table_name="discharge_protocols")
    op.drop_index(op.f("ix_discharge_protocols_id"), table_name="discharge_protocols")
    op.drop_table("discharge_protocols")

    op.drop_index(op.f("ix_clinical_handoffs_status"), table_name="clinical_handoffs")
    op.drop_index(op.f("ix_clinical_handoffs_encounter_id"), table_name="clinical_handoffs")
    op.drop_index(op.f("ix_clinical_handoffs_patient_id"), table_name="clinical_handoffs")
    op.drop_index(op.f("ix_clinical_handoffs_handoff_id"), table_name="clinical_handoffs")
    op.drop_index(op.f("ix_clinical_handoffs_id"), table_name="clinical_handoffs")
    op.drop_table("clinical_handoffs")
