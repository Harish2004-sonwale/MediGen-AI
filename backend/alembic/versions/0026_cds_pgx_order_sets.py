"""Phase 9.0.26: Enterprise CDS Rules, Pharmacogenomics (PGx) and Clinical Order Sets

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0026_cds_pgx_order_sets'
down_revision = '0025_empi_ccda_regional_pathways'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. pgx_rule_definitions
    op.create_table(
        'pgx_rule_definitions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('rule_id', sa.String(length=64), nullable=False),
        sa.Column('cpic_level', sa.Enum('LEVEL_A', 'LEVEL_B', 'LEVEL_C', 'LEVEL_D', name='cpiclevel'), nullable=False),
        sa.Column('gene_symbol', sa.String(length=32), nullable=False),
        sa.Column('phenotype', sa.String(length=64), nullable=False),
        sa.Column('drug_code', sa.String(length=64), nullable=False),
        sa.Column('drug_name', sa.String(length=128), nullable=False),
        sa.Column('risk_severity', sa.Enum('CONTRAINDICATED', 'HIGH_RISK', 'MODERATE_RISK', 'INFORMATIONAL', name='pgxriskseverity'), nullable=False),
        sa.Column('clinical_implication', sa.Text(), nullable=False),
        sa.Column('recommendation_text', sa.Text(), nullable=False),
        sa.Column('alternative_drugs', sa.JSON(), nullable=True),
        sa.Column('evidence_source', sa.String(length=128), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_pgx_rule_definitions_rule_id', 'pgx_rule_definitions', ['rule_id'], unique=True)
    op.create_index('ix_pgx_rule_definitions_gene_symbol', 'pgx_rule_definitions', ['gene_symbol'])
    op.create_index('ix_pgx_rule_definitions_phenotype', 'pgx_rule_definitions', ['phenotype'])
    op.create_index('ix_pgx_rule_definitions_drug_code', 'pgx_rule_definitions', ['drug_code'])

    # 2. clinical_order_sets
    op.create_table(
        'clinical_order_sets',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('order_set_id', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.Enum('CRITICAL_CARE', 'CARDIOLOGY', 'ENDOCRINOLOGY', 'NEUROLOGY', 'ONCOLOGY', 'INFECTIOUS_DISEASE', 'GENERAL_MEDICINE', name='ordersetcategory'), nullable=False),
        sa.Column('target_icd10', sa.String(length=32), nullable=True),
        sa.Column('facility_id', sa.String(length=64), nullable=True),
        sa.Column('version', sa.String(length=16), nullable=False, server_default='1.0.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_clinical_order_sets_order_set_id', 'clinical_order_sets', ['order_set_id'], unique=True)
    op.create_index('ix_clinical_order_sets_code', 'clinical_order_sets', ['code'], unique=True)
    op.create_index('ix_clinical_order_sets_facility_id', 'clinical_order_sets', ['facility_id'])

    # 3. clinical_order_set_items
    op.create_table(
        'clinical_order_set_items',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('item_id', sa.String(length=64), nullable=False),
        sa.Column('order_set_id', sa.String(length=64), nullable=False),
        sa.Column('item_type', sa.Enum('MEDICATION', 'LAB', 'RADIOLOGY', 'NURSING', 'CONSULT', name='ordersetitemtype'), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('default_dosage', sa.String(length=64), nullable=True),
        sa.Column('default_route', sa.String(length=32), nullable=True),
        sa.Column('default_frequency', sa.String(length=32), nullable=True),
        sa.Column('clinical_instructions', sa.Text(), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('sequence_order', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['order_set_id'], ['clinical_order_sets.order_set_id'], ondelete='CASCADE'),
    )
    op.create_index('ix_clinical_order_set_items_item_id', 'clinical_order_set_items', ['item_id'], unique=True)
    op.create_index('ix_clinical_order_set_items_order_set_id', 'clinical_order_set_items', ['order_set_id'])

    # 4. order_set_executions
    op.create_table(
        'order_set_executions',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('execution_id', sa.String(length=64), nullable=False),
        sa.Column('order_set_id', sa.String(length=64), nullable=False),
        sa.Column('patient_id', sa.String(length=64), nullable=False),
        sa.Column('facility_id', sa.String(length=64), nullable=False),
        sa.Column('ordering_provider_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'EXECUTED', 'PARTIALLY_EXECUTED', 'CANCELLED', name='ordersetexecutionstatus'), nullable=False),
        sa.Column('executed_items_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('generated_order_ids', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['order_set_id'], ['clinical_order_sets.order_set_id']),
        sa.ForeignKeyConstraint(['ordering_provider_id'], ['users.id']),
    )
    op.create_index('ix_order_set_executions_execution_id', 'order_set_executions', ['execution_id'], unique=True)
    op.create_index('ix_order_set_executions_order_set_id', 'order_set_executions', ['order_set_id'])
    op.create_index('ix_order_set_executions_patient_id', 'order_set_executions', ['patient_id'])
    op.create_index('ix_order_set_executions_facility_id', 'order_set_executions', ['facility_id'])

    # 5. cds_rule_evaluation_audits
    op.create_table(
        'cds_rule_evaluation_audits',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('audit_id', sa.String(length=64), nullable=False),
        sa.Column('patient_id', sa.String(length=64), nullable=False),
        sa.Column('facility_id', sa.String(length=64), nullable=True),
        sa.Column('rule_type', sa.String(length=32), nullable=False),
        sa.Column('trigger_event', sa.Enum('PATIENT_VIEW', 'ORDER_SELECT', 'ORDER_SIGN', 'APPOINTMENT_BOOK', name='cdsruletriggerevent'), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False, server_default='warning'),
        sa.Column('card_summary', sa.String(length=255), nullable=False),
        sa.Column('card_detail', sa.Text(), nullable=False),
        sa.Column('is_overridden', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('clinician_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['clinician_id'], ['users.id']),
    )
    op.create_index('ix_cds_rule_evaluation_audits_audit_id', 'cds_rule_evaluation_audits', ['audit_id'], unique=True)
    op.create_index('ix_cds_rule_evaluation_audits_patient_id', 'cds_rule_evaluation_audits', ['patient_id'])
    op.create_index('ix_cds_rule_evaluation_audits_facility_id', 'cds_rule_evaluation_audits', ['facility_id'])


def downgrade() -> None:
    op.drop_table('cds_rule_evaluation_audits')
    op.drop_table('order_set_executions')
    op.drop_table('clinical_order_set_items')
    op.drop_table('clinical_order_sets')
    op.drop_table('pgx_rule_definitions')
