"""create clinical orders and diagnostic results tables

Revision ID: 0015_clinical_orders_and_diagnostic_results
Revises: 0014_transitions_and_discharge_protocols
Create Date: 2026-08-29 18:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0015_clinical_orders_and_diagnostic_results"
down_revision: Union[str, None] = "0014_transitions_and_discharge_protocols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create clinical_orders table
    op.create_table(
        "clinical_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("ordering_user_id", sa.Integer(), nullable=True),
        sa.Column("order_category", sa.String(length=30), server_default="laboratory", nullable=False),
        sa.Column("order_type", sa.String(length=100), nullable=False),
        sa.Column("priority", sa.String(length=20), server_default="routine", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("clinical_indication", sa.Text(), nullable=False),
        sa.Column("specimen_source", sa.String(length=100), nullable=True),
        sa.Column("order_details_json", sa.JSON(), nullable=True),
        sa.Column("ai_safety_flags_json", sa.JSON(), nullable=True),
        sa.Column("is_ai_suggested", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ordering_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clinical_orders_id"), "clinical_orders", ["id"], unique=False)
    op.create_index(op.f("ix_clinical_orders_order_id"), "clinical_orders", ["order_id"], unique=True)
    op.create_index(op.f("ix_clinical_orders_patient_id"), "clinical_orders", ["patient_id"], unique=False)
    op.create_index(op.f("ix_clinical_orders_encounter_id"), "clinical_orders", ["encounter_id"], unique=False)
    op.create_index(op.f("ix_clinical_orders_order_category"), "clinical_orders", ["order_category"], unique=False)
    op.create_index(op.f("ix_clinical_orders_order_type"), "clinical_orders", ["order_type"], unique=False)
    op.create_index(op.f("ix_clinical_orders_status"), "clinical_orders", ["status"], unique=False)

    # 2. Create diagnostic_results table
    op.create_table(
        "diagnostic_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("result_id", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("test_name", sa.String(length=255), nullable=False),
        sa.Column("test_code_loinc", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="final", nullable=False),
        sa.Column("abnormal_flag", sa.String(length=20), server_default="normal", nullable=False),
        sa.Column("findings_summary", sa.Text(), nullable=False),
        sa.Column("numeric_value", sa.Float(), nullable=True),
        sa.Column("unit_of_measure", sa.String(length=50), nullable=True),
        sa.Column("reference_range_low", sa.Float(), nullable=True),
        sa.Column("reference_range_high", sa.Float(), nullable=True),
        sa.Column("critical_threshold_low", sa.Float(), nullable=True),
        sa.Column("critical_threshold_high", sa.Float(), nullable=True),
        sa.Column("structured_components_json", sa.JSON(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resulted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["clinical_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_diagnostic_results_id"), "diagnostic_results", ["id"], unique=False)
    op.create_index(op.f("ix_diagnostic_results_result_id"), "diagnostic_results", ["result_id"], unique=True)
    op.create_index(op.f("ix_diagnostic_results_order_id"), "diagnostic_results", ["order_id"], unique=False)
    op.create_index(op.f("ix_diagnostic_results_patient_id"), "diagnostic_results", ["patient_id"], unique=False)
    op.create_index(op.f("ix_diagnostic_results_encounter_id"), "diagnostic_results", ["encounter_id"], unique=False)
    op.create_index(op.f("ix_diagnostic_results_test_name"), "diagnostic_results", ["test_name"], unique=False)
    op.create_index(op.f("ix_diagnostic_results_test_code_loinc"), "diagnostic_results", ["test_code_loinc"], unique=False)
    op.create_index(op.f("ix_diagnostic_results_status"), "diagnostic_results", ["status"], unique=False)
    op.create_index(op.f("ix_diagnostic_results_abnormal_flag"), "diagnostic_results", ["abnormal_flag"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_diagnostic_results_abnormal_flag"), table_name="diagnostic_results")
    op.drop_index(op.f("ix_diagnostic_results_status"), table_name="diagnostic_results")
    op.drop_index(op.f("ix_diagnostic_results_test_code_loinc"), table_name="diagnostic_results")
    op.drop_index(op.f("ix_diagnostic_results_test_name"), table_name="diagnostic_results")
    op.drop_index(op.f("ix_diagnostic_results_encounter_id"), table_name="diagnostic_results")
    op.drop_index(op.f("ix_diagnostic_results_patient_id"), table_name="diagnostic_results")
    op.drop_index(op.f("ix_diagnostic_results_order_id"), table_name="diagnostic_results")
    op.drop_index(op.f("ix_diagnostic_results_result_id"), table_name="diagnostic_results")
    op.drop_index(op.f("ix_diagnostic_results_id"), table_name="diagnostic_results")
    op.drop_table("diagnostic_results")

    op.drop_index(op.f("ix_clinical_orders_status"), table_name="clinical_orders")
    op.drop_index(op.f("ix_clinical_orders_order_type"), table_name="clinical_orders")
    op.drop_index(op.f("ix_clinical_orders_order_category"), table_name="clinical_orders")
    op.drop_index(op.f("ix_clinical_orders_encounter_id"), table_name="clinical_orders")
    op.drop_index(op.f("ix_clinical_orders_patient_id"), table_name="clinical_orders")
    op.drop_index(op.f("ix_clinical_orders_order_id"), table_name="clinical_orders")
    op.drop_index(op.f("ix_clinical_orders_id"), table_name="clinical_orders")
    op.drop_table("clinical_orders")
