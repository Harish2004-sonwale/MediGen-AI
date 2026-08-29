"""create patient cohorts, cohort memberships, and clinical risk assessments tables

Revision ID: 0013_cohorts_and_risk_stratification
Revises: 0012_care_plans_and_tasks
Create Date: 2026-08-29 17:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0013_cohorts_and_risk_stratification"
down_revision: Union[str, None] = "0012_care_plans_and_tasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create patient_cohorts table
    op.create_table(
        "patient_cohorts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cohort_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("cohort_type", sa.String(length=50), server_default="disease_registry", nullable=False),
        sa.Column("criteria_json", sa.JSON(), nullable=True),
        sa.Column("is_dynamic", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_patient_cohorts_id"), "patient_cohorts", ["id"], unique=False)
    op.create_index(op.f("ix_patient_cohorts_cohort_id"), "patient_cohorts", ["cohort_id"], unique=True)
    op.create_index(op.f("ix_patient_cohorts_name"), "patient_cohorts", ["name"], unique=False)
    op.create_index(op.f("ix_patient_cohorts_cohort_type"), "patient_cohorts", ["cohort_type"], unique=False)

    # 2. Create cohort_memberships table
    op.create_table(
        "cohort_memberships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cohort_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["cohort_id"], ["patient_cohorts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cohort_id", "patient_id", name="uq_cohort_patient_membership"),
    )
    op.create_index(op.f("ix_cohort_memberships_id"), "cohort_memberships", ["id"], unique=False)
    op.create_index(op.f("ix_cohort_memberships_cohort_id"), "cohort_memberships", ["cohort_id"], unique=False)
    op.create_index(op.f("ix_cohort_memberships_patient_id"), "cohort_memberships", ["patient_id"], unique=False)

    # 3. Create clinical_risk_assessments table
    op.create_table(
        "clinical_risk_assessments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("assessment_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("risk_type", sa.String(length=50), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("risk_tier", sa.String(length=20), server_default="MODERATE", nullable=False),
        sa.Column("predicted_outcome", sa.String(length=255), nullable=False),
        sa.Column("contributing_factors_json", sa.JSON(), nullable=True),
        sa.Column("mitigation_recommendations_json", sa.JSON(), nullable=True),
        sa.Column("assessed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("is_ai_generated", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assessed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clinical_risk_assessments_id"), "clinical_risk_assessments", ["id"], unique=False)
    op.create_index(op.f("ix_clinical_risk_assessments_assessment_id"), "clinical_risk_assessments", ["assessment_id"], unique=True)
    op.create_index(op.f("ix_clinical_risk_assessments_patient_id"), "clinical_risk_assessments", ["patient_id"], unique=False)
    op.create_index(op.f("ix_clinical_risk_assessments_risk_type"), "clinical_risk_assessments", ["risk_type"], unique=False)
    op.create_index(op.f("ix_clinical_risk_assessments_risk_tier"), "clinical_risk_assessments", ["risk_tier"], unique=False)
    op.create_index(op.f("ix_clinical_risk_assessments_assessed_at"), "clinical_risk_assessments", ["assessed_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_clinical_risk_assessments_assessed_at"), table_name="clinical_risk_assessments")
    op.drop_index(op.f("ix_clinical_risk_assessments_risk_tier"), table_name="clinical_risk_assessments")
    op.drop_index(op.f("ix_clinical_risk_assessments_risk_type"), table_name="clinical_risk_assessments")
    op.drop_index(op.f("ix_clinical_risk_assessments_patient_id"), table_name="clinical_risk_assessments")
    op.drop_index(op.f("ix_clinical_risk_assessments_assessment_id"), table_name="clinical_risk_assessments")
    op.drop_index(op.f("ix_clinical_risk_assessments_id"), table_name="clinical_risk_assessments")
    op.drop_table("clinical_risk_assessments")

    op.drop_index(op.f("ix_cohort_memberships_patient_id"), table_name="cohort_memberships")
    op.drop_index(op.f("ix_cohort_memberships_cohort_id"), table_name="cohort_memberships")
    op.drop_index(op.f("ix_cohort_memberships_id"), table_name="cohort_memberships")
    op.drop_table("cohort_memberships")

    op.drop_index(op.f("ix_patient_cohorts_cohort_type"), table_name="patient_cohorts")
    op.drop_index(op.f("ix_patient_cohorts_name"), table_name="patient_cohorts")
    op.drop_index(op.f("ix_patient_cohorts_cohort_id"), table_name="patient_cohorts")
    op.drop_index(op.f("ix_patient_cohorts_id"), table_name="patient_cohorts")
    op.drop_table("patient_cohorts")
