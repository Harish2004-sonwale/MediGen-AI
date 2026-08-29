"""create vitals and clinical alerts tables for CDS and telemetry

Revision ID: 0011_vitals_and_clinical_alerts
Revises: 0010_clinical_notes
Create Date: 2026-08-29 15:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0011_vitals_and_clinical_alerts"
down_revision: Union[str, None] = "0010_clinical_notes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create vital_telemetry table
    op.create_table(
        "vital_telemetry",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("reading_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("heart_rate", sa.Integer(), nullable=True),
        sa.Column("systolic_bp", sa.Integer(), nullable=True),
        sa.Column("diastolic_bp", sa.Integer(), nullable=True),
        sa.Column("respiratory_rate", sa.Integer(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("spo2_percent", sa.Float(), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=50), server_default="manual_entry", nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vital_telemetry_id"), "vital_telemetry", ["id"], unique=False)
    op.create_index(op.f("ix_vital_telemetry_reading_id"), "vital_telemetry", ["reading_id"], unique=True)
    op.create_index(op.f("ix_vital_telemetry_patient_id"), "vital_telemetry", ["patient_id"], unique=False)
    op.create_index(op.f("ix_vital_telemetry_measured_at"), "vital_telemetry", ["measured_at"], unique=False)

    # 2. Create clinical_alerts table
    op.create_table(
        "clinical_alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_id", sa.String(length=32), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("reading_id", sa.Integer(), nullable=True),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), server_default="MODERATE", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("parameters_json", sa.JSON(), nullable=True),
        sa.Column("recurrence_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("acknowledged_by_user_id", sa.Integer(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissal_reason", sa.Text(), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reading_id"], ["vital_telemetry.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["acknowledged_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clinical_alerts_id"), "clinical_alerts", ["id"], unique=False)
    op.create_index(op.f("ix_clinical_alerts_alert_id"), "clinical_alerts", ["alert_id"], unique=True)
    op.create_index(op.f("ix_clinical_alerts_patient_id"), "clinical_alerts", ["patient_id"], unique=False)
    op.create_index(op.f("ix_clinical_alerts_alert_type"), "clinical_alerts", ["alert_type"], unique=False)
    op.create_index(op.f("ix_clinical_alerts_severity"), "clinical_alerts", ["severity"], unique=False)
    op.create_index(op.f("ix_clinical_alerts_status"), "clinical_alerts", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_clinical_alerts_status"), table_name="clinical_alerts")
    op.drop_index(op.f("ix_clinical_alerts_severity"), table_name="clinical_alerts")
    op.drop_index(op.f("ix_clinical_alerts_alert_type"), table_name="clinical_alerts")
    op.drop_index(op.f("ix_clinical_alerts_patient_id"), table_name="clinical_alerts")
    op.drop_index(op.f("ix_clinical_alerts_alert_id"), table_name="clinical_alerts")
    op.drop_index(op.f("ix_clinical_alerts_id"), table_name="clinical_alerts")
    op.drop_table("clinical_alerts")

    op.drop_index(op.f("ix_vital_telemetry_measured_at"), table_name="vital_telemetry")
    op.drop_index(op.f("ix_vital_telemetry_patient_id"), table_name="vital_telemetry")
    op.drop_index(op.f("ix_vital_telemetry_reading_id"), table_name="vital_telemetry")
    op.drop_index(op.f("ix_vital_telemetry_id"), table_name="vital_telemetry")
    op.drop_table("vital_telemetry")
