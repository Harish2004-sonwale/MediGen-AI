"""create multi-tenant facilities, ehr integrations, smart auth sessions and terminology tables

Revision ID: 0022_multi_tenant_facilities_and_ehr_integrations
Revises: 0021_clinical_security_audit_consent_and_compliance
Create Date: 2026-08-30 22:55:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0022_multi_tenant_facilities_and_ehr_integrations"
down_revision: Union[str, None] = "0021_clinical_security_audit_consent_and_compliance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create health_organizations table
    op.create_table(
        "health_organizations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("org_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("org_type", sa.String(length=32), server_default="HOSPITAL_NETWORK", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id"),
    )
    op.create_index(op.f("ix_health_organizations_id"), "health_organizations", ["id"], unique=False)
    op.create_index(op.f("ix_health_organizations_org_id"), "health_organizations", ["org_id"], unique=True)
    op.create_index(op.f("ix_health_organizations_name"), "health_organizations", ["name"], unique=False)

    # 2. Create clinical_facilities table
    op.create_table(
        "clinical_facilities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("facility_id", sa.String(length=64), nullable=False),
        sa.Column("org_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("facility_code", sa.String(length=32), nullable=False),
        sa.Column("address_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["health_organizations.org_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("facility_id"),
        sa.UniqueConstraint("facility_code"),
    )
    op.create_index(op.f("ix_clinical_facilities_id"), "clinical_facilities", ["id"], unique=False)
    op.create_index(op.f("ix_clinical_facilities_facility_id"), "clinical_facilities", ["facility_id"], unique=True)
    op.create_index(op.f("ix_clinical_facilities_org_id"), "clinical_facilities", ["org_id"], unique=False)
    op.create_index(op.f("ix_clinical_facilities_facility_code"), "clinical_facilities", ["facility_code"], unique=True)

    # 3. Create department_units table
    op.create_table(
        "department_units",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("department_id", sa.String(length=64), nullable=False),
        sa.Column("facility_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("dept_code", sa.String(length=32), nullable=False),
        sa.Column("floor_or_wing", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["facility_id"], ["clinical_facilities.facility_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("department_id"),
    )
    op.create_index(op.f("ix_department_units_id"), "department_units", ["id"], unique=False)
    op.create_index(op.f("ix_department_units_department_id"), "department_units", ["department_id"], unique=True)
    op.create_index(op.f("ix_department_units_facility_id"), "department_units", ["facility_id"], unique=False)

    # 4. Create ehr_integration_configs table
    op.create_table(
        "ehr_integration_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("config_id", sa.String(length=64), nullable=False),
        sa.Column("facility_id", sa.String(length=64), nullable=False),
        sa.Column("ehr_vendor", sa.String(length=32), server_default="EPIC", nullable=False),
        sa.Column("fhir_base_url", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("smart_auth_url", sa.String(length=255), nullable=True),
        sa.Column("smart_token_url", sa.String(length=255), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["facility_id"], ["clinical_facilities.facility_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("config_id"),
    )
    op.create_index(op.f("ix_ehr_integration_configs_id"), "ehr_integration_configs", ["id"], unique=False)
    op.create_index(op.f("ix_ehr_integration_configs_config_id"), "ehr_integration_configs", ["config_id"], unique=True)
    op.create_index(op.f("ix_ehr_integration_configs_facility_id"), "ehr_integration_configs", ["facility_id"], unique=False)

    # 5. Create smart_auth_sessions table
    op.create_table(
        "smart_auth_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("patient_id", sa.String(length=64), nullable=True),
        sa.Column("encounter_id", sa.String(length=64), nullable=True),
        sa.Column("facility_id", sa.String(length=64), nullable=True),
        sa.Column("scope", sa.String(length=500), nullable=False),
        sa.Column("code_challenge", sa.String(length=128), nullable=True),
        sa.Column("code_challenge_method", sa.String(length=16), server_default="S256", nullable=False),
        sa.Column("auth_code", sa.String(length=128), nullable=True),
        sa.Column("access_token_hash", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(op.f("ix_smart_auth_sessions_id"), "smart_auth_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_smart_auth_sessions_session_id"), "smart_auth_sessions", ["session_id"], unique=True)
    op.create_index(op.f("ix_smart_auth_sessions_client_id"), "smart_auth_sessions", ["client_id"], unique=False)
    op.create_index(op.f("ix_smart_auth_sessions_auth_code"), "smart_auth_sessions", ["auth_code"], unique=True)

    # 6. Create terminology_mappings table
    op.create_table(
        "terminology_mappings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mapping_id", sa.String(length=64), nullable=False),
        sa.Column("source_system", sa.String(length=64), nullable=False),
        sa.Column("source_code", sa.String(length=64), nullable=False),
        sa.Column("source_display", sa.String(length=255), nullable=False),
        sa.Column("target_system", sa.String(length=64), nullable=False),
        sa.Column("target_code", sa.String(length=64), nullable=False),
        sa.Column("target_display", sa.String(length=255), nullable=False),
        sa.Column("confidence_score", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mapping_id"),
    )
    op.create_index(op.f("ix_terminology_mappings_id"), "terminology_mappings", ["id"], unique=False)
    op.create_index(op.f("ix_terminology_mappings_mapping_id"), "terminology_mappings", ["mapping_id"], unique=True)
    op.create_index(op.f("ix_terminology_mappings_source_code"), "terminology_mappings", ["source_code"], unique=False)
    op.create_index(op.f("ix_terminology_mappings_target_code"), "terminology_mappings", ["target_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_terminology_mappings_target_code"), table_name="terminology_mappings")
    op.drop_index(op.f("ix_terminology_mappings_source_code"), table_name="terminology_mappings")
    op.drop_index(op.f("ix_terminology_mappings_mapping_id"), table_name="terminology_mappings")
    op.drop_index(op.f("ix_terminology_mappings_id"), table_name="terminology_mappings")
    op.drop_table("terminology_mappings")

    op.drop_index(op.f("ix_smart_auth_sessions_auth_code"), table_name="smart_auth_sessions")
    op.drop_index(op.f("ix_smart_auth_sessions_client_id"), table_name="smart_auth_sessions")
    op.drop_index(op.f("ix_smart_auth_sessions_session_id"), table_name="smart_auth_sessions")
    op.drop_index(op.f("ix_smart_auth_sessions_id"), table_name="smart_auth_sessions")
    op.drop_table("smart_auth_sessions")

    op.drop_index(op.f("ix_ehr_integration_configs_facility_id"), table_name="ehr_integration_configs")
    op.drop_index(op.f("ix_ehr_integration_configs_config_id"), table_name="ehr_integration_configs")
    op.drop_index(op.f("ix_ehr_integration_configs_id"), table_name="ehr_integration_configs")
    op.drop_table("ehr_integration_configs")

    op.drop_index(op.f("ix_department_units_facility_id"), table_name="department_units")
    op.drop_index(op.f("ix_department_units_department_id"), table_name="department_units")
    op.drop_index(op.f("ix_department_units_id"), table_name="department_units")
    op.drop_table("department_units")

    op.drop_index(op.f("ix_clinical_facilities_facility_code"), table_name="clinical_facilities")
    op.drop_index(op.f("ix_clinical_facilities_org_id"), table_name="clinical_facilities")
    op.drop_index(op.f("ix_clinical_facilities_facility_id"), table_name="clinical_facilities")
    op.drop_index(op.f("ix_clinical_facilities_id"), table_name="clinical_facilities")
    op.drop_table("clinical_facilities")

    op.drop_index(op.f("ix_health_organizations_name"), table_name="health_organizations")
    op.drop_index(op.f("ix_health_organizations_org_id"), table_name="health_organizations")
    op.drop_index(op.f("ix_health_organizations_id"), table_name="health_organizations")
    op.drop_table("health_organizations")
