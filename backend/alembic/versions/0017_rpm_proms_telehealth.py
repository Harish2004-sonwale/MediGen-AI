"""create rpm proms and telehealth tables

Revision ID: 0017_rpm_proms_telehealth
Revises: 0016_clinical_quality_measures_and_compliance
Create Date: 2026-08-29 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0017_rpm_proms_telehealth"
down_revision: Union[str, None] = "0016_clinical_quality_measures_and_compliance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create rpm_programs table
    op.create_table(
        "rpm_programs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("program_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("enrolled_by_user_id", sa.Integer(), nullable=True),
        sa.Column("condition_name", sa.String(length=100), nullable=False),
        sa.Column("program_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("target_cadence_days", sa.Integer(), server_default="1", nullable=False),
        sa.Column("clinical_goals_json", sa.JSON(), nullable=True),
        sa.Column("discharged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discharge_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["enrolled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rpm_programs_id"), "rpm_programs", ["id"], unique=False)
    op.create_index(op.f("ix_rpm_programs_program_id"), "rpm_programs", ["program_id"], unique=True)
    op.create_index(op.f("ix_rpm_programs_patient_id"), "rpm_programs", ["patient_id"], unique=False)
    op.create_index(op.f("ix_rpm_programs_condition_name"), "rpm_programs", ["condition_name"], unique=False)
    op.create_index(op.f("ix_rpm_programs_status"), "rpm_programs", ["status"], unique=False)

    # 2. Create rpm_devices table
    op.create_table(
        "rpm_devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("device_type", sa.String(length=50), nullable=False),
        sa.Column("manufacturer", sa.String(length=100), nullable=False),
        sa.Column("model_number", sa.String(length=100), nullable=False),
        sa.Column("serial_number", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("supported_measurements_json", sa.JSON(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rpm_devices_id"), "rpm_devices", ["id"], unique=False)
    op.create_index(op.f("ix_rpm_devices_device_id"), "rpm_devices", ["device_id"], unique=True)
    op.create_index(op.f("ix_rpm_devices_patient_id"), "rpm_devices", ["patient_id"], unique=False)
    op.create_index(op.f("ix_rpm_devices_device_type"), "rpm_devices", ["device_type"], unique=False)
    op.create_index(op.f("ix_rpm_devices_serial_number"), "rpm_devices", ["serial_number"], unique=True)
    op.create_index(op.f("ix_rpm_devices_status"), "rpm_devices", ["status"], unique=False)

    # 3. Create rpm_observations table
    op.create_table(
        "rpm_observations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("observation_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("observation_type", sa.String(length=50), nullable=False),
        sa.Column("numeric_value", sa.Float(), nullable=False),
        sa.Column("secondary_value", sa.Float(), nullable=True),
        sa.Column("unit_of_measure", sa.String(length=30), nullable=False),
        sa.Column("classification", sa.String(length=30), server_default="normal", nullable=False),
        sa.Column("source_type", sa.String(length=50), server_default="bluetooth_sync", nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_acknowledged", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["device_id"], ["rpm_devices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rpm_observations_id"), "rpm_observations", ["id"], unique=False)
    op.create_index(op.f("ix_rpm_observations_observation_id"), "rpm_observations", ["observation_id"], unique=True)
    op.create_index(op.f("ix_rpm_observations_patient_id"), "rpm_observations", ["patient_id"], unique=False)
    op.create_index(op.f("ix_rpm_observations_observation_type"), "rpm_observations", ["observation_type"], unique=False)
    op.create_index(op.f("ix_rpm_observations_classification"), "rpm_observations", ["classification"], unique=False)
    op.create_index(op.f("ix_rpm_observations_measured_at"), "rpm_observations", ["measured_at"], unique=False)

    # 4. Create rpm_threshold_rules table
    op.create_table(
        "rpm_threshold_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=True),
        sa.Column("observation_type", sa.String(length=50), nullable=False),
        sa.Column("normal_min", sa.Float(), nullable=True),
        sa.Column("normal_max", sa.Float(), nullable=True),
        sa.Column("critical_low", sa.Float(), nullable=True),
        sa.Column("critical_high", sa.Float(), nullable=True),
        sa.Column("consecutive_readings_trigger", sa.Integer(), server_default="2", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rpm_threshold_rules_id"), "rpm_threshold_rules", ["id"], unique=False)
    op.create_index(op.f("ix_rpm_threshold_rules_rule_id"), "rpm_threshold_rules", ["rule_id"], unique=True)
    op.create_index(op.f("ix_rpm_threshold_rules_patient_id"), "rpm_threshold_rules", ["patient_id"], unique=False)
    op.create_index(op.f("ix_rpm_threshold_rules_observation_type"), "rpm_threshold_rules", ["observation_type"], unique=False)

    # 5. Create rpm_escalation_alerts table
    op.create_table(
        "rpm_escalation_alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("observation_id", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=20), server_default="HIGH", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="open", nullable=False),
        sa.Column("escalation_reason", sa.Text(), nullable=False),
        sa.Column("clinical_action_taken", sa.Text(), nullable=True),
        sa.Column("linked_care_task_id", sa.Integer(), nullable=True),
        sa.Column("acknowledged_by_user_id", sa.Integer(), nullable=True),
        sa.Column("resolved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["observation_id"], ["rpm_observations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_care_task_id"], ["care_tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["acknowledged_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rpm_escalation_alerts_id"), "rpm_escalation_alerts", ["id"], unique=False)
    op.create_index(op.f("ix_rpm_escalation_alerts_alert_id"), "rpm_escalation_alerts", ["alert_id"], unique=True)
    op.create_index(op.f("ix_rpm_escalation_alerts_patient_id"), "rpm_escalation_alerts", ["patient_id"], unique=False)
    op.create_index(op.f("ix_rpm_escalation_alerts_severity"), "rpm_escalation_alerts", ["severity"], unique=False)
    op.create_index(op.f("ix_rpm_escalation_alerts_status"), "rpm_escalation_alerts", ["status"], unique=False)

    # 6. Create prom_definitions table
    op.create_table(
        "prom_definitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("prom_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=50), server_default="symptom_burden", nullable=False),
        sa.Column("version", sa.String(length=20), server_default="1.0.0", nullable=False),
        sa.Column("questions_json", sa.JSON(), nullable=False),
        sa.Column("scoring_method", sa.String(length=50), server_default="sum_total", nullable=False),
        sa.Column("interpretation_ranges_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prom_definitions_id"), "prom_definitions", ["id"], unique=False)
    op.create_index(op.f("ix_prom_definitions_prom_id"), "prom_definitions", ["prom_id"], unique=True)
    op.create_index(op.f("ix_prom_definitions_domain"), "prom_definitions", ["domain"], unique=False)

    # 7. Create prom_responses table
    op.create_table(
        "prom_responses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("response_id", sa.String(length=64), nullable=False),
        sa.Column("prom_id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("answers_json", sa.JSON(), nullable=False),
        sa.Column("calculated_score", sa.Float(), nullable=False),
        sa.Column("severity_interpretation", sa.String(length=100), nullable=False),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["prom_id"], ["prom_definitions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prom_responses_id"), "prom_responses", ["id"], unique=False)
    op.create_index(op.f("ix_prom_responses_response_id"), "prom_responses", ["response_id"], unique=True)
    op.create_index(op.f("ix_prom_responses_prom_id"), "prom_responses", ["prom_id"], unique=False)
    op.create_index(op.f("ix_prom_responses_patient_id"), "prom_responses", ["patient_id"], unique=False)

    # 8. Create telehealth_sessions table
    op.create_table(
        "telehealth_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("clinician_user_id", sa.Integer(), nullable=False),
        sa.Column("appointment_id", sa.Integer(), nullable=True),
        sa.Column("encounter_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="scheduled", nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("visit_reason", sa.String(length=255), nullable=False),
        sa.Column("pre_visit_rpm_summary_json", sa.JSON(), nullable=True),
        sa.Column("pre_visit_prom_summary_json", sa.JSON(), nullable=True),
        sa.Column("session_notes", sa.Text(), nullable=True),
        sa.Column("followup_instructions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["clinician_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_telehealth_sessions_id"), "telehealth_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_telehealth_sessions_session_id"), "telehealth_sessions", ["session_id"], unique=True)
    op.create_index(op.f("ix_telehealth_sessions_patient_id"), "telehealth_sessions", ["patient_id"], unique=False)
    op.create_index(op.f("ix_telehealth_sessions_clinician_user_id"), "telehealth_sessions", ["clinician_user_id"], unique=False)
    op.create_index(op.f("ix_telehealth_sessions_status"), "telehealth_sessions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("telehealth_sessions")
    op.drop_table("prom_responses")
    op.drop_table("prom_definitions")
    op.drop_table("rpm_escalation_alerts")
    op.drop_table("rpm_threshold_rules")
    op.drop_table("rpm_observations")
    op.drop_table("rpm_devices")
    op.drop_table("rpm_programs")
