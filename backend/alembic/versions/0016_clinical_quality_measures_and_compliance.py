"""create clinical quality measures and compliance tables

Revision ID: 0016_clinical_quality_measures_and_compliance
Revises: 0015_clinical_orders_and_diagnostic_results
Create Date: 2026-08-29 18:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0016_clinical_quality_measures_and_compliance"
down_revision: Union[str, None] = "0015_clinical_orders_and_diagnostic_results"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create quality_measures table
    op.create_table(
        "quality_measures",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("measure_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=20), server_default="1.0.0", nullable=False),
        sa.Column("domain", sa.String(length=50), server_default="chronic_disease_management", nullable=False),
        sa.Column("hedis_mips_reference", sa.String(length=100), nullable=True),
        sa.Column("denominator_criteria_json", sa.JSON(), nullable=True),
        sa.Column("numerator_criteria_json", sa.JSON(), nullable=True),
        sa.Column("exclusion_criteria_json", sa.JSON(), nullable=True),
        sa.Column("target_compliance_rate", sa.Float(), server_default="80.0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quality_measures_id"), "quality_measures", ["id"], unique=False)
    op.create_index(op.f("ix_quality_measures_measure_id"), "quality_measures", ["measure_id"], unique=True)
    op.create_index(op.f("ix_quality_measures_domain"), "quality_measures", ["domain"], unique=False)

    # 2. Create quality_measure_results table
    op.create_table(
        "quality_measure_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("result_id", sa.String(length=32), nullable=False),
        sa.Column("measure_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("measurement_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("measurement_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_eligible", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_excluded", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("exclusion_reason", sa.Text(), nullable=True),
        sa.Column("is_numerator_compliant", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("compliance_status", sa.String(length=30), server_default="non_compliant", nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("gap_reason", sa.Text(), nullable=True),
        sa.Column("remediation_action", sa.Text(), nullable=True),
        sa.Column("calculated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["measure_id"], ["quality_measures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["calculated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quality_measure_results_id"), "quality_measure_results", ["id"], unique=False)
    op.create_index(op.f("ix_quality_measure_results_result_id"), "quality_measure_results", ["result_id"], unique=True)
    op.create_index(op.f("ix_quality_measure_results_measure_id"), "quality_measure_results", ["measure_id"], unique=False)
    op.create_index(op.f("ix_quality_measure_results_patient_id"), "quality_measure_results", ["patient_id"], unique=False)
    op.create_index(op.f("ix_quality_measure_results_compliance_status"), "quality_measure_results", ["compliance_status"], unique=False)

    # 3. Create quality_measure_gaps table
    op.create_table(
        "quality_measure_gaps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gap_id", sa.String(length=32), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("measure_id", sa.Integer(), nullable=False),
        sa.Column("gap_type", sa.String(length=50), server_default="clinical_measure_gap", nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="MODERATE", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="open", nullable=False),
        sa.Column("gap_description", sa.Text(), nullable=False),
        sa.Column("missing_data_elements", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linked_care_task_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["result_id"], ["quality_measure_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["measure_id"], ["quality_measures.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["linked_care_task_id"], ["care_tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quality_measure_gaps_id"), "quality_measure_gaps", ["id"], unique=False)
    op.create_index(op.f("ix_quality_measure_gaps_gap_id"), "quality_measure_gaps", ["gap_id"], unique=True)
    op.create_index(op.f("ix_quality_measure_gaps_result_id"), "quality_measure_gaps", ["result_id"], unique=False)
    op.create_index(op.f("ix_quality_measure_gaps_patient_id"), "quality_measure_gaps", ["patient_id"], unique=False)
    op.create_index(op.f("ix_quality_measure_gaps_measure_id"), "quality_measure_gaps", ["measure_id"], unique=False)
    op.create_index(op.f("ix_quality_measure_gaps_severity"), "quality_measure_gaps", ["severity"], unique=False)
    op.create_index(op.f("ix_quality_measure_gaps_status"), "quality_measure_gaps", ["status"], unique=False)

    # 4. Create quality_measure_reports table
    op.create_table(
        "quality_measure_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("report_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("reporting_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reporting_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report_scope", sa.String(length=30), server_default="organization", nullable=False),
        sa.Column("total_eligible_population", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_numerator_compliant", sa.Integer(), server_default="0", nullable=False),
        sa.Column("overall_performance_rate", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("measure_summaries_json", sa.JSON(), nullable=False),
        sa.Column("audit_metadata_json", sa.JSON(), nullable=True),
        sa.Column("generated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quality_measure_reports_id"), "quality_measure_reports", ["id"], unique=False)
    op.create_index(op.f("ix_quality_measure_reports_report_id"), "quality_measure_reports", ["report_id"], unique=True)
    op.create_index(op.f("ix_quality_measure_reports_report_scope"), "quality_measure_reports", ["report_scope"], unique=False)


def downgrade() -> None:
    op.drop_table("quality_measure_reports")
    op.drop_table("quality_measure_gaps")
    op.drop_table("quality_measure_results")
    op.drop_table("quality_measures")
