"""create care plans and care tasks tables for clinical workflow orchestration

Revision ID: 0012_care_plans_and_tasks
Revises: 0011_vitals_and_clinical_alerts
Create Date: 2026-08-29 16:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0012_care_plans_and_tasks"
down_revision: Union[str, None] = "0011_vitals_and_clinical_alerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create care_plans table
    op.create_table(
        "care_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=True),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=50), server_default="chronic_disease_management", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("intent", sa.String(length=30), server_default="plan", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("goals_json", sa.JSON(), nullable=True),
        sa.Column("interventions_json", sa.JSON(), nullable=True),
        sa.Column("is_ai_generated", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_care_plans_id"), "care_plans", ["id"], unique=False)
    op.create_index(op.f("ix_care_plans_plan_id"), "care_plans", ["plan_id"], unique=True)
    op.create_index(op.f("ix_care_plans_patient_id"), "care_plans", ["patient_id"], unique=False)
    op.create_index(op.f("ix_care_plans_status"), "care_plans", ["status"], unique=False)

    # 2. Create care_tasks table
    op.create_table(
        "care_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("care_plan_id", sa.Integer(), nullable=True),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("appointment_id", sa.Integer(), nullable=True),
        sa.Column("assigned_user_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("task_type", sa.String(length=50), server_default="general_task", nullable=False),
        sa.Column("priority", sa.String(length=20), server_default="ROUTINE", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["care_plan_id"], ["care_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_care_tasks_id"), "care_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_care_tasks_task_id"), "care_tasks", ["task_id"], unique=True)
    op.create_index(op.f("ix_care_tasks_patient_id"), "care_tasks", ["patient_id"], unique=False)
    op.create_index(op.f("ix_care_tasks_care_plan_id"), "care_tasks", ["care_plan_id"], unique=False)
    op.create_index(op.f("ix_care_tasks_priority"), "care_tasks", ["priority"], unique=False)
    op.create_index(op.f("ix_care_tasks_status"), "care_tasks", ["status"], unique=False)
    op.create_index(op.f("ix_care_tasks_due_date"), "care_tasks", ["due_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_care_tasks_due_date"), table_name="care_tasks")
    op.drop_index(op.f("ix_care_tasks_status"), table_name="care_tasks")
    op.drop_index(op.f("ix_care_tasks_priority"), table_name="care_tasks")
    op.drop_index(op.f("ix_care_tasks_care_plan_id"), table_name="care_tasks")
    op.drop_index(op.f("ix_care_tasks_patient_id"), table_name="care_tasks")
    op.drop_index(op.f("ix_care_tasks_task_id"), table_name="care_tasks")
    op.drop_index(op.f("ix_care_tasks_id"), table_name="care_tasks")
    op.drop_table("care_tasks")

    op.drop_index(op.f("ix_care_plans_status"), table_name="care_plans")
    op.drop_index(op.f("ix_care_plans_patient_id"), table_name="care_plans")
    op.drop_index(op.f("ix_care_plans_plan_id"), table_name="care_plans")
    op.drop_index(op.f("ix_care_plans_id"), table_name="care_plans")
    op.drop_table("care_plans")
