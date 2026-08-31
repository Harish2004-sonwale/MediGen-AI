"""multi-tenant clinical isolation, optimistic locking, outbox, idempotency, mfa, subscriptions and bulk export

Revision ID: 0023_multi_tenant_clinical_isolation_and_outbox
Revises: 0022_multi_tenant_facilities_and_ehr_integrations
Create Date: 2026-08-31 11:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0023_multi_tenant_clinical_isolation_and_outbox"
down_revision: Union[str, None] = "0022_multi_tenant_facilities_and_ehr_integrations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Ensure default seed organization and facility exist before backfill
    # -------------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO health_organizations (org_id, name, org_type, is_active, created_at, updated_at)
        VALUES ('ORG-001', 'MetroHealth Network', 'HOSPITAL_NETWORK', true, now(), now())
        ON CONFLICT (org_id) DO NOTHING;
        """
    )
    op.execute(
        """
        INSERT INTO clinical_facilities (facility_id, org_id, name, facility_code, address_json, is_active, created_at, updated_at)
        VALUES ('FAC-001', 'ORG-001', 'MetroHealth General Hospital', 'MH-MAIN', '{"street": "100 Medical Center Way", "city": "Metro City", "state": "CA", "zip": "94102"}', true, now(), now())
        ON CONFLICT (facility_id) DO NOTHING;
        """
    )

    # -------------------------------------------------------------------------
    # 2. Add facility_id, version, and escalation columns (Nullable initially)
    # -------------------------------------------------------------------------
    # users
    op.add_column("users", sa.Column("default_facility_id", sa.String(length=64), nullable=True))
    op.create_foreign_key("fk_users_default_facility_id", "users", "clinical_facilities", ["default_facility_id"], ["facility_id"], ondelete="SET NULL")

    # patients
    op.add_column("patients", sa.Column("facility_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_patients_facility_id"), "patients", ["facility_id"], unique=False)
    op.create_foreign_key("fk_patients_facility_id", "patients", "clinical_facilities", ["facility_id"], ["facility_id"], ondelete="RESTRICT")

    # encounters
    op.add_column("encounters", sa.Column("facility_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_encounters_facility_id"), "encounters", ["facility_id"], unique=False)
    op.create_foreign_key("fk_encounters_facility_id", "encounters", "clinical_facilities", ["facility_id"], ["facility_id"], ondelete="RESTRICT")

    # clinical_orders (facility_id + optimistic locking version)
    op.add_column("clinical_orders", sa.Column("facility_id", sa.String(length=64), nullable=True))
    op.add_column("clinical_orders", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.create_index(op.f("ix_clinical_orders_facility_id"), "clinical_orders", ["facility_id"], unique=False)
    op.create_foreign_key("fk_clinical_orders_facility_id", "clinical_orders", "clinical_facilities", ["facility_id"], ["facility_id"], ondelete="RESTRICT")

    # clinical_notes
    op.add_column("clinical_notes", sa.Column("facility_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_clinical_notes_facility_id"), "clinical_notes", ["facility_id"], unique=False)
    op.create_foreign_key("fk_clinical_notes_facility_id", "clinical_notes", "clinical_facilities", ["facility_id"], ["facility_id"], ondelete="RESTRICT")

    # medical_documents
    op.add_column("medical_documents", sa.Column("facility_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_medical_documents_facility_id"), "medical_documents", ["facility_id"], unique=False)
    op.create_foreign_key("fk_medical_documents_facility_id", "medical_documents", "clinical_facilities", ["facility_id"], ["facility_id"], ondelete="RESTRICT")

    # care_plans (facility_id + optimistic locking version)
    op.add_column("care_plans", sa.Column("facility_id", sa.String(length=64), nullable=True))
    op.add_column("care_plans", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.create_index(op.f("ix_care_plans_facility_id"), "care_plans", ["facility_id"], unique=False)
    op.create_foreign_key("fk_care_plans_facility_id", "care_plans", "clinical_facilities", ["facility_id"], ["facility_id"], ondelete="RESTRICT")

    # discharge_protocols (optimistic locking version)
    op.add_column("discharge_protocols", sa.Column("version", sa.Integer(), server_default="1", nullable=False))

    # imaging_studies
    op.add_column("imaging_studies", sa.Column("facility_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_imaging_studies_facility_id"), "imaging_studies", ["facility_id"], unique=False)
    op.create_foreign_key("fk_imaging_studies_facility_id", "imaging_studies", "clinical_facilities", ["facility_id"], ["facility_id"], ondelete="RESTRICT")

    # diagnostic_media
    op.add_column("diagnostic_media", sa.Column("facility_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_diagnostic_media_facility_id"), "diagnostic_media", ["facility_id"], unique=False)
    op.create_foreign_key("fk_diagnostic_media_facility_id", "diagnostic_media", "clinical_facilities", ["facility_id"], ["facility_id"], ondelete="RESTRICT")

    # clinical_alerts (facility_id + escalation metadata)
    op.add_column("clinical_alerts", sa.Column("facility_id", sa.String(length=64), nullable=True))
    op.add_column("clinical_alerts", sa.Column("escalation_level", sa.Integer(), server_default="0", nullable=False))
    op.add_column("clinical_alerts", sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("clinical_alerts", sa.Column("escalation_notes", sa.Text(), nullable=True))
    op.create_index(op.f("ix_clinical_alerts_facility_id"), "clinical_alerts", ["facility_id"], unique=False)
    op.create_foreign_key("fk_clinical_alerts_facility_id", "clinical_alerts", "clinical_facilities", ["facility_id"], ["facility_id"], ondelete="RESTRICT")

    # -------------------------------------------------------------------------
    # 3. Relationship-Driven Data Backfill
    # -------------------------------------------------------------------------
    # Backfill default facility for users
    op.execute("UPDATE users SET default_facility_id = 'FAC-001' WHERE default_facility_id IS NULL;")
    # Backfill patients to FAC-001 (or derived from existing relations)
    op.execute("UPDATE patients SET facility_id = 'FAC-001' WHERE facility_id IS NULL;")
    # Backfill encounters from parent patient facility
    op.execute(
        """
        UPDATE encounters
        SET facility_id = COALESCE(patients.facility_id, 'FAC-001')
        FROM patients
        WHERE encounters.patient_id = patients.patient_id AND encounters.facility_id IS NULL;
        """
    )
    op.execute("UPDATE encounters SET facility_id = 'FAC-001' WHERE facility_id IS NULL;")
    # Backfill clinical_orders from parent patient or encounter facility
    op.execute(
        """
        UPDATE clinical_orders
        SET facility_id = COALESCE(patients.facility_id, 'FAC-001')
        FROM patients
        WHERE clinical_orders.patient_id = patients.id AND clinical_orders.facility_id IS NULL;
        """
    )
    op.execute("UPDATE clinical_orders SET facility_id = 'FAC-001' WHERE facility_id IS NULL;")
    # Backfill notes, documents, care_plans, imaging, media, alerts from parent patient
    op.execute("UPDATE clinical_notes SET facility_id = 'FAC-001' WHERE facility_id IS NULL;")
    op.execute("UPDATE medical_documents SET facility_id = 'FAC-001' WHERE facility_id IS NULL;")
    op.execute("UPDATE care_plans SET facility_id = 'FAC-001' WHERE facility_id IS NULL;")
    op.execute("UPDATE imaging_studies SET facility_id = 'FAC-001' WHERE facility_id IS NULL;")
    op.execute("UPDATE diagnostic_media SET facility_id = 'FAC-001' WHERE facility_id IS NULL;")
    op.execute("UPDATE clinical_alerts SET facility_id = 'FAC-001' WHERE facility_id IS NULL;")

    # -------------------------------------------------------------------------
    # 4. Create New Core Reliability & Enterprise Tables
    # -------------------------------------------------------------------------
    # 4.1 outbox_events
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.String(length=64), nullable=False),
        sa.Column("facility_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="5", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["facility_id"], ["clinical_facilities.facility_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_outbox_events_id"), "outbox_events", ["id"], unique=False)
    op.create_index(op.f("ix_outbox_events_event_id"), "outbox_events", ["event_id"], unique=True)
    op.create_index(op.f("ix_outbox_events_event_type"), "outbox_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_outbox_events_facility_id"), "outbox_events", ["facility_id"], unique=False)
    op.create_index(op.f("ix_outbox_events_status"), "outbox_events", ["status"], unique=False)
    op.create_index(op.f("ix_outbox_events_created_at"), "outbox_events", ["created_at"], unique=False)

    # 4.2 idempotency_records
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("endpoint", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("facility_id", sa.String(length=64), nullable=True),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(op.f("ix_idempotency_records_id"), "idempotency_records", ["id"], unique=False)
    op.create_index(op.f("ix_idempotency_records_idempotency_key"), "idempotency_records", ["idempotency_key"], unique=True)
    op.create_index(op.f("ix_idempotency_records_endpoint"), "idempotency_records", ["endpoint"], unique=False)
    op.create_index(op.f("ix_idempotency_records_user_id"), "idempotency_records", ["user_id"], unique=False)
    op.create_index(op.f("ix_idempotency_records_expires_at"), "idempotency_records", ["expires_at"], unique=False)

    # 4.3 mfa_credentials
    op.create_table(
        "mfa_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("secret_encrypted", sa.String(length=255), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("backup_codes_json", sa.JSON(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_mfa_credentials_id"), "mfa_credentials", ["id"], unique=False)
    op.create_index(op.f("ix_mfa_credentials_user_id"), "mfa_credentials", ["user_id"], unique=True)

    # 4.4 fhir_subscriptions
    op.create_table(
        "fhir_subscriptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("subscription_id", sa.String(length=64), nullable=False),
        sa.Column("facility_id", sa.String(length=64), nullable=True),
        sa.Column("topic", sa.String(length=128), nullable=False),
        sa.Column("criteria", sa.String(length=255), nullable=False),
        sa.Column("channel_type", sa.String(length=32), server_default="REST_HOOK", nullable=False),
        sa.Column("endpoint_url", sa.String(length=255), nullable=True),
        sa.Column("secret_token", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="REQUESTED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["facility_id"], ["clinical_facilities.facility_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subscription_id"),
    )
    op.create_index(op.f("ix_fhir_subscriptions_id"), "fhir_subscriptions", ["id"], unique=False)
    op.create_index(op.f("ix_fhir_subscriptions_subscription_id"), "fhir_subscriptions", ["subscription_id"], unique=True)
    op.create_index(op.f("ix_fhir_subscriptions_facility_id"), "fhir_subscriptions", ["facility_id"], unique=False)
    op.create_index(op.f("ix_fhir_subscriptions_topic"), "fhir_subscriptions", ["topic"], unique=False)
    op.create_index(op.f("ix_fhir_subscriptions_status"), "fhir_subscriptions", ["status"], unique=False)

    # 4.5 bulk_export_jobs
    op.create_table(
        "bulk_export_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("facility_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("export_type", sa.String(length=32), server_default="PATIENT", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="PENDING", nullable=False),
        sa.Column("output_urls_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["facility_id"], ["clinical_facilities.facility_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index(op.f("ix_bulk_export_jobs_id"), "bulk_export_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_bulk_export_jobs_job_id"), "bulk_export_jobs", ["job_id"], unique=True)
    op.create_index(op.f("ix_bulk_export_jobs_facility_id"), "bulk_export_jobs", ["facility_id"], unique=False)
    op.create_index(op.f("ix_bulk_export_jobs_status"), "bulk_export_jobs", ["status"], unique=False)


def downgrade() -> None:
    # 1. Drop new enterprise tables
    op.drop_table("bulk_export_jobs")
    op.drop_table("fhir_subscriptions")
    op.drop_table("mfa_credentials")
    op.drop_table("idempotency_records")
    op.drop_table("outbox_events")

    # 2. Remove columns from clinical tables
    op.drop_column("clinical_alerts", "escalation_notes")
    op.drop_column("clinical_alerts", "escalated_at")
    op.drop_column("clinical_alerts", "escalation_level")
    op.drop_column("clinical_alerts", "facility_id")

    op.drop_column("diagnostic_media", "facility_id")
    op.drop_column("imaging_studies", "facility_id")
    op.drop_column("discharge_protocols", "version")

    op.drop_column("care_plans", "version")
    op.drop_column("care_plans", "facility_id")

    op.drop_column("medical_documents", "facility_id")
    op.drop_column("clinical_notes", "facility_id")

    op.drop_column("clinical_orders", "version")
    op.drop_column("clinical_orders", "facility_id")

    op.drop_column("encounters", "facility_id")
    op.drop_column("patients", "facility_id")
    op.drop_column("users", "default_facility_id")
