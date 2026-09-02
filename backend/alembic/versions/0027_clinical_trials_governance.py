"""Phase 9.0.27: Enterprise Clinical Trial Auto-Enrollment, Protocol Deviations & Multi-Center Regulatory Auditing

Revision ID: 0027_clinical_trials_governance
Revises: 0026_cds_pgx_order_sets
Create Date: 2026-09-02 10:20:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0027_clinical_trials_governance'
down_revision = '0026_cds_pgx_order_sets'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Multi-Center Study Sites Table
    op.create_table(
        'multi_center_study_sites',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('site_id', sa.String(length=64), nullable=False),
        sa.Column('trial_id', sa.Integer(), nullable=False),
        sa.Column('facility_id', sa.String(length=64), nullable=True),
        sa.Column('principal_investigator_user_id', sa.Integer(), nullable=True),
        sa.Column('site_name', sa.String(length=255), nullable=False),
        sa.Column('target_accrual', sa.Integer(), server_default='20', nullable=False),
        sa.Column('current_enrolled', sa.Integer(), server_default='0', nullable=False),
        sa.Column('site_status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('irb_approval_number', sa.String(length=64), nullable=True),
        sa.Column('irb_approval_date', sa.Date(), nullable=True),
        sa.Column('irb_expiry_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['trial_id'], ['clinical_trials.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['facility_id'], ['clinical_facilities.facility_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['principal_investigator_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_multi_center_study_sites_site_id'), 'multi_center_study_sites', ['site_id'], unique=True)
    op.create_index(op.f('ix_multi_center_study_sites_trial_id'), 'multi_center_study_sites', ['trial_id'], unique=False)
    op.create_index(op.f('ix_multi_center_study_sites_facility_id'), 'multi_center_study_sites', ['facility_id'], unique=False)
    op.create_index(op.f('ix_multi_center_study_sites_site_status'), 'multi_center_study_sites', ['site_status'], unique=False)

    # 2. Trial Protocol Deviations Table
    op.create_table(
        'trial_protocol_deviations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('deviation_id', sa.String(length=64), nullable=False),
        sa.Column('trial_id', sa.Integer(), nullable=False),
        sa.Column('site_id', sa.Integer(), nullable=True),
        sa.Column('patient_id', sa.Integer(), nullable=True),
        sa.Column('reported_by_user_id', sa.Integer(), nullable=False),
        sa.Column('deviation_category', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=32), server_default='minor', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='open', nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('discovered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('impact_on_patient_safety', sa.Text(), nullable=True),
        sa.Column('impact_on_data_integrity', sa.Text(), nullable=True),
        sa.Column('requires_irb_submission', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('irb_submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['trial_id'], ['clinical_trials.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['site_id'], ['multi_center_study_sites.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reported_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trial_protocol_deviations_deviation_id'), 'trial_protocol_deviations', ['deviation_id'], unique=True)
    op.create_index(op.f('ix_trial_protocol_deviations_trial_id'), 'trial_protocol_deviations', ['trial_id'], unique=False)
    op.create_index(op.f('ix_trial_protocol_deviations_site_id'), 'trial_protocol_deviations', ['site_id'], unique=False)
    op.create_index(op.f('ix_trial_protocol_deviations_patient_id'), 'trial_protocol_deviations', ['patient_id'], unique=False)
    op.create_index(op.f('ix_trial_protocol_deviations_deviation_category'), 'trial_protocol_deviations', ['deviation_category'], unique=False)
    op.create_index(op.f('ix_trial_protocol_deviations_severity'), 'trial_protocol_deviations', ['severity'], unique=False)
    op.create_index(op.f('ix_trial_protocol_deviations_status'), 'trial_protocol_deviations', ['status'], unique=False)

    # 3. Trial CAPA Records Table
    op.create_table(
        'trial_capa_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('capa_id', sa.String(length=64), nullable=False),
        sa.Column('deviation_id', sa.Integer(), nullable=False),
        sa.Column('root_cause_category', sa.String(length=64), server_default='investigator_oversight', nullable=False),
        sa.Column('root_cause_analysis', sa.Text(), nullable=False),
        sa.Column('corrective_action', sa.Text(), nullable=False),
        sa.Column('preventive_action', sa.Text(), nullable=False),
        sa.Column('assigned_owner_user_id', sa.Integer(), nullable=False),
        sa.Column('target_resolution_date', sa.Date(), nullable=False),
        sa.Column('actual_resolution_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='in_progress', nullable=False),
        sa.Column('effectiveness_check_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['deviation_id'], ['trial_protocol_deviations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_owner_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trial_capa_records_capa_id'), 'trial_capa_records', ['capa_id'], unique=True)
    op.create_index(op.f('ix_trial_capa_records_deviation_id'), 'trial_capa_records', ['deviation_id'], unique=False)
    op.create_index(op.f('ix_trial_capa_records_status'), 'trial_capa_records', ['status'], unique=False)

    # 4. Trial IRB Notifications Table
    op.create_table(
        'trial_irb_notifications',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('notification_id', sa.String(length=64), nullable=False),
        sa.Column('deviation_id', sa.Integer(), nullable=False),
        sa.Column('irb_committee_name', sa.String(length=150), nullable=False),
        sa.Column('submission_type', sa.String(length=64), nullable=False),
        sa.Column('document_content_json', sa.JSON(), nullable=False),
        sa.Column('submitted_by_user_id', sa.Integer(), nullable=False),
        sa.Column('submission_timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('acknowledgement_reference', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['deviation_id'], ['trial_protocol_deviations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submitted_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_trial_irb_notifications_notification_id'), 'trial_irb_notifications', ['notification_id'], unique=True)
    op.create_index(op.f('ix_trial_irb_notifications_deviation_id'), 'trial_irb_notifications', ['deviation_id'], unique=False)
    op.create_index(op.f('ix_trial_irb_notifications_submission_type'), 'trial_irb_notifications', ['submission_type'], unique=False)


def downgrade() -> None:
    op.drop_table('trial_irb_notifications')
    op.drop_table('trial_capa_records')
    op.drop_table('trial_protocol_deviations')
    op.drop_table('multi_center_study_sites')
