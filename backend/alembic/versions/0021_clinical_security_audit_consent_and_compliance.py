"""create clinical security audit consent and compliance tables

Revision ID: 0021_clinical_security_audit_consent_and_compliance
Revises: 0020_medical_imaging_and_radiology_workflow
Create Date: 2026-08-30 16:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0021_clinical_security_audit_consent_and_compliance"
down_revision: Union[str, None] = "0020_medical_imaging_and_radiology_workflow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create clinical_audit_events table
    op.create_table(
        "clinical_audit_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_role", sa.String(length=32), server_default="ANONYMOUS", nullable=False),
        sa.Column("patient_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("purpose_of_use", sa.String(length=32), server_default="TREATMENT", nullable=False),
        sa.Column("outcome", sa.String(length=32), server_default="SUCCESS", nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("prev_record_hash", sa.String(length=64), server_default="0" * 64, nullable=False),
        sa.Column("record_hash", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_clinical_audit_events_id"), "clinical_audit_events", ["id"], unique=False)
    op.create_index(op.f("ix_clinical_audit_events_event_id"), "clinical_audit_events", ["event_id"], unique=True)
    op.create_index(op.f("ix_clinical_audit_events_timestamp"), "clinical_audit_events", ["timestamp"], unique=False)
    op.create_index(op.f("ix_clinical_audit_events_user_id"), "clinical_audit_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_clinical_audit_events_user_role"), "clinical_audit_events", ["user_role"], unique=False)
    op.create_index(op.f("ix_clinical_audit_events_patient_id"), "clinical_audit_events", ["patient_id"], unique=False)
    op.create_index(op.f("ix_clinical_audit_events_action"), "clinical_audit_events", ["action"], unique=False)
    op.create_index(op.f("ix_clinical_audit_events_resource_type"), "clinical_audit_events", ["resource_type"], unique=False)
    op.create_index(op.f("ix_clinical_audit_events_resource_id"), "clinical_audit_events", ["resource_id"], unique=False)
    op.create_index(op.f("ix_clinical_audit_events_purpose_of_use"), "clinical_audit_events", ["purpose_of_use"], unique=False)
    op.create_index(op.f("ix_clinical_audit_events_outcome"), "clinical_audit_events", ["outcome"], unique=False)
    op.create_index(op.f("ix_clinical_audit_events_record_hash"), "clinical_audit_events", ["record_hash"], unique=False)

    # 2. Create patient_consents table
    op.create_table(
        "patient_consents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("consent_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("scope", sa.String(length=32), server_default="ALL_RECORDS", nullable=False),
        sa.Column("policy_rule", sa.String(length=16), server_default="PERMIT", nullable=False),
        sa.Column("purpose_of_use", sa.String(length=32), server_default="TREATMENT", nullable=False),
        sa.Column("data_category", sa.String(length=64), nullable=True),
        sa.Column("actor_type", sa.String(length=32), server_default="CARE_TEAM", nullable=False),
        sa.Column("actor_reference", sa.String(length=128), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_by_patient", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("signer_name", sa.String(length=128), nullable=False),
        sa.Column("signer_relationship", sa.String(length=32), server_default="SELF", nullable=False),
        sa.Column("witness_or_clinician_id", sa.Integer(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.String(length=255), nullable=True),
        sa.Column("revoked_by_user_id", sa.Integer(), nullable=True),
        sa.Column("digital_signature_hash", sa.String(length=64), server_default="UNVERIFIED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.patient_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["witness_or_clinician_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("consent_id"),
    )
    op.create_index(op.f("ix_patient_consents_id"), "patient_consents", ["id"], unique=False)
    op.create_index(op.f("ix_patient_consents_consent_id"), "patient_consents", ["consent_id"], unique=True)
    op.create_index(op.f("ix_patient_consents_patient_id"), "patient_consents", ["patient_id"], unique=False)
    op.create_index(op.f("ix_patient_consents_status"), "patient_consents", ["status"], unique=False)
    op.create_index(op.f("ix_patient_consents_scope"), "patient_consents", ["scope"], unique=False)
    op.create_index(op.f("ix_patient_consents_policy_rule"), "patient_consents", ["policy_rule"], unique=False)
    op.create_index(op.f("ix_patient_consents_purpose_of_use"), "patient_consents", ["purpose_of_use"], unique=False)
    op.create_index(op.f("ix_patient_consents_data_category"), "patient_consents", ["data_category"], unique=False)

    # 3. Create security_incidents table
    op.create_table(
        "security_incidents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("incident_id", sa.String(length=64), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("severity", sa.String(length=16), server_default="MEDIUM", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="OPEN", nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("patient_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("evidence_metadata", sa.JSON(), nullable=False),
        sa.Column("assigned_to_user_id", sa.Integer(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incident_id"),
    )
    op.create_index(op.f("ix_security_incidents_id"), "security_incidents", ["id"], unique=False)
    op.create_index(op.f("ix_security_incidents_incident_id"), "security_incidents", ["incident_id"], unique=True)
    op.create_index(op.f("ix_security_incidents_detected_at"), "security_incidents", ["detected_at"], unique=False)
    op.create_index(op.f("ix_security_incidents_severity"), "security_incidents", ["severity"], unique=False)
    op.create_index(op.f("ix_security_incidents_status"), "security_incidents", ["status"], unique=False)
    op.create_index(op.f("ix_security_incidents_event_type"), "security_incidents", ["event_type"], unique=False)
    op.create_index(op.f("ix_security_incidents_user_id"), "security_incidents", ["user_id"], unique=False)
    op.create_index(op.f("ix_security_incidents_patient_id"), "security_incidents", ["patient_id"], unique=False)

    # 4. Create data_retention_policies table
    op.create_table(
        "data_retention_policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("policy_code", sa.String(length=32), nullable=False),
        sa.Column("data_category", sa.String(length=64), nullable=False),
        sa.Column("retention_period_days", sa.Integer(), server_default="2555", nullable=False),
        sa.Column("action_on_expiry", sa.String(length=32), server_default="FLAG_REVIEW", nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_code"),
    )
    op.create_index(op.f("ix_data_retention_policies_id"), "data_retention_policies", ["id"], unique=False)
    op.create_index(op.f("ix_data_retention_policies_policy_code"), "data_retention_policies", ["policy_code"], unique=True)
    op.create_index(op.f("ix_data_retention_policies_data_category"), "data_retention_policies", ["data_category"], unique=False)

    # 5. Create legal_clinical_holds table
    op.create_table(
        "legal_clinical_holds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("hold_id", sa.String(length=64), nullable=False),
        sa.Column("patient_id", sa.String(length=64), nullable=True),
        sa.Column("scope_category", sa.String(length=64), server_default="ALL_RECORDS", nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column("placed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("placed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("released_by_user_id", sa.Integer(), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["placed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["released_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hold_id"),
    )
    op.create_index(op.f("ix_legal_clinical_holds_id"), "legal_clinical_holds", ["id"], unique=False)
    op.create_index(op.f("ix_legal_clinical_holds_hold_id"), "legal_clinical_holds", ["hold_id"], unique=True)
    op.create_index(op.f("ix_legal_clinical_holds_patient_id"), "legal_clinical_holds", ["patient_id"], unique=False)
    op.create_index(op.f("ix_legal_clinical_holds_status"), "legal_clinical_holds", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_legal_clinical_holds_status"), table_name="legal_clinical_holds")
    op.drop_index(op.f("ix_legal_clinical_holds_patient_id"), table_name="legal_clinical_holds")
    op.drop_index(op.f("ix_legal_clinical_holds_hold_id"), table_name="legal_clinical_holds")
    op.drop_index(op.f("ix_legal_clinical_holds_id"), table_name="legal_clinical_holds")
    op.drop_table("legal_clinical_holds")

    op.drop_index(op.f("ix_data_retention_policies_data_category"), table_name="data_retention_policies")
    op.drop_index(op.f("ix_data_retention_policies_policy_code"), table_name="data_retention_policies")
    op.drop_index(op.f("ix_data_retention_policies_id"), table_name="data_retention_policies")
    op.drop_table("data_retention_policies")

    op.drop_index(op.f("ix_security_incidents_patient_id"), table_name="security_incidents")
    op.drop_index(op.f("ix_security_incidents_user_id"), table_name="security_incidents")
    op.drop_index(op.f("ix_security_incidents_event_type"), table_name="security_incidents")
    op.drop_index(op.f("ix_security_incidents_status"), table_name="security_incidents")
    op.drop_index(op.f("ix_security_incidents_severity"), table_name="security_incidents")
    op.drop_index(op.f("ix_security_incidents_detected_at"), table_name="security_incidents")
    op.drop_index(op.f("ix_security_incidents_incident_id"), table_name="security_incidents")
    op.drop_index(op.f("ix_security_incidents_id"), table_name="security_incidents")
    op.drop_table("security_incidents")

    op.drop_index(op.f("ix_patient_consents_data_category"), table_name="patient_consents")
    op.drop_index(op.f("ix_patient_consents_purpose_of_use"), table_name="patient_consents")
    op.drop_index(op.f("ix_patient_consents_policy_rule"), table_name="patient_consents")
    op.drop_index(op.f("ix_patient_consents_scope"), table_name="patient_consents")
    op.drop_index(op.f("ix_patient_consents_status"), table_name="patient_consents")
    op.drop_index(op.f("ix_patient_consents_patient_id"), table_name="patient_consents")
    op.drop_index(op.f("ix_patient_consents_consent_id"), table_name="patient_consents")
    op.drop_index(op.f("ix_patient_consents_id"), table_name="patient_consents")
    op.drop_table("patient_consents")

    op.drop_index(op.f("ix_clinical_audit_events_record_hash"), table_name="clinical_audit_events")
    op.drop_index(op.f("ix_clinical_audit_events_outcome"), table_name="clinical_audit_events")
    op.drop_index(op.f("ix_clinical_audit_events_purpose_of_use"), table_name="clinical_audit_events")
    op.drop_index(op.f("ix_clinical_audit_events_resource_id"), table_name="clinical_audit_events")
    op.drop_index(op.f("ix_clinical_audit_events_resource_type"), table_name="clinical_audit_events")
    op.drop_index(op.f("ix_clinical_audit_events_action"), table_name="clinical_audit_events")
    op.drop_index(op.f("ix_clinical_audit_events_patient_id"), table_name="clinical_audit_events")
    op.drop_index(op.f("ix_clinical_audit_events_user_role"), table_name="clinical_audit_events")
    op.drop_index(op.f("ix_clinical_audit_events_user_id"), table_name="clinical_audit_events")
    op.drop_index(op.f("ix_clinical_audit_events_timestamp"), table_name="clinical_audit_events")
    op.drop_index(op.f("ix_clinical_audit_events_event_id"), table_name="clinical_audit_events")
    op.drop_index(op.f("ix_clinical_audit_events_id"), table_name="clinical_audit_events")
    op.drop_table("clinical_audit_events")
