"""create clinical ai agents and care coordination tables

Revision ID: 0019_clinical_ai_agents_and_care_coordination
Revises: 0018_clinical_trials_genomics_precision_oncology
Create Date: 2026-08-29 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0019_clinical_ai_agents_and_care_coordination"
down_revision: Union[str, None] = "0018_clinical_trials_genomics_precision_oncology"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create clinical_agent_definitions table
    op.create_table(
        "clinical_agent_definitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("agent_type", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=32), server_default="1.0.0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("capabilities_json", sa.JSON(), nullable=True),
        sa.Column("default_action_class", sa.String(length=64), server_default="RECOMMENDATION", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id"),
    )
    op.create_index(op.f("ix_clinical_agent_definitions_id"), "clinical_agent_definitions", ["id"], unique=False)
    op.create_index(op.f("ix_clinical_agent_definitions_agent_id"), "clinical_agent_definitions", ["agent_id"], unique=True)
    op.create_index(op.f("ix_clinical_agent_definitions_agent_type"), "clinical_agent_definitions", ["agent_type"], unique=False)

    # 2. Create clinical_agent_runs table
    op.create_table(
        "clinical_agent_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("agent_type", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("initiated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_context_snapshot_json", sa.JSON(), nullable=True),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column("provenance_hash", sa.String(length=64), nullable=False),
        sa.Column("overall_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["initiated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id"),
    )
    op.create_index(op.f("ix_clinical_agent_runs_id"), "clinical_agent_runs", ["id"], unique=False)
    op.create_index(op.f("ix_clinical_agent_runs_run_id"), "clinical_agent_runs", ["run_id"], unique=True)
    op.create_index(op.f("ix_clinical_agent_runs_agent_type"), "clinical_agent_runs", ["agent_type"], unique=False)
    op.create_index(op.f("ix_clinical_agent_runs_patient_id"), "clinical_agent_runs", ["patient_id"], unique=False)
    op.create_index(op.f("ix_clinical_agent_runs_status"), "clinical_agent_runs", ["status"], unique=False)

    # 3. Create clinical_agent_recommendations table
    op.create_table(
        "clinical_agent_recommendations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recommendation_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=32), server_default="medium", nullable=False),
        sa.Column("action_class", sa.String(length=64), server_default="RECOMMENDATION", nullable=False),
        sa.Column("suggested_action_type", sa.String(length=64), nullable=True),
        sa.Column("suggested_action_payload_json", sa.JSON(), nullable=True),
        sa.Column("approval_status", sa.String(length=32), server_default="pending_review", nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("execution_status", sa.String(length=32), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_result_json", sa.JSON(), nullable=True),
        sa.Column("provenance_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["clinical_agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recommendation_id"),
    )
    op.create_index(op.f("ix_clinical_agent_recommendations_id"), "clinical_agent_recommendations", ["id"], unique=False)
    op.create_index(op.f("ix_clinical_agent_recommendations_recommendation_id"), "clinical_agent_recommendations", ["recommendation_id"], unique=True)
    op.create_index(op.f("ix_clinical_agent_recommendations_run_id"), "clinical_agent_recommendations", ["run_id"], unique=False)
    op.create_index(op.f("ix_clinical_agent_recommendations_patient_id"), "clinical_agent_recommendations", ["patient_id"], unique=False)
    op.create_index(op.f("ix_clinical_agent_recommendations_category"), "clinical_agent_recommendations", ["category"], unique=False)
    op.create_index(op.f("ix_clinical_agent_recommendations_priority"), "clinical_agent_recommendations", ["priority"], unique=False)
    op.create_index(op.f("ix_clinical_agent_recommendations_action_class"), "clinical_agent_recommendations", ["action_class"], unique=False)
    op.create_index(op.f("ix_clinical_agent_recommendations_approval_status"), "clinical_agent_recommendations", ["approval_status"], unique=False)

    # 4. Create agent_evidence_references table
    op.create_table(
        "agent_evidence_references",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evidence_id", sa.String(length=64), nullable=False),
        sa.Column("recommendation_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_identifier", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), server_default="1.0", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recommendation_id"], ["clinical_agent_recommendations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evidence_id"),
    )
    op.create_index(op.f("ix_agent_evidence_references_id"), "agent_evidence_references", ["id"], unique=False)
    op.create_index(op.f("ix_agent_evidence_references_evidence_id"), "agent_evidence_references", ["evidence_id"], unique=True)
    op.create_index(op.f("ix_agent_evidence_references_recommendation_id"), "agent_evidence_references", ["recommendation_id"], unique=False)
    op.create_index(op.f("ix_agent_evidence_references_entity_type"), "agent_evidence_references", ["entity_type"], unique=False)


def downgrade() -> None:
    op.drop_table("agent_evidence_references")
    op.drop_table("clinical_agent_recommendations")
    op.drop_table("clinical_agent_runs")
    op.drop_table("clinical_agent_definitions")
