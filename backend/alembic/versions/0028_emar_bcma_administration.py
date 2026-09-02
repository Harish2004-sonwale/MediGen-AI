"""Phase 9.0.28: Closed-Loop Medication Administration (eMAR) & Barcode Verification (BCMA)

Revision ID: 0028_emar_bcma_administration
Revises: 0027_clinical_trials_governance
Create Date: 2026-09-02 10:38:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0028_emar_bcma_administration'
down_revision = '0027_clinical_trials_governance'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Medication Barcode Directory Table
    op.create_table(
        'medication_barcode_directory',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('barcode', sa.String(length=128), nullable=False),
        sa.Column('medication_name', sa.String(length=255), nullable=False),
        sa.Column('rxnorm_code', sa.String(length=64), nullable=False),
        sa.Column('ndc_code', sa.String(length=64), nullable=True),
        sa.Column('standard_dose', sa.String(length=64), nullable=False),
        sa.Column('dosage_form', sa.String(length=64), server_default='tablet', nullable=False),
        sa.Column('route', sa.String(length=64), server_default='oral', nullable=False),
        sa.Column('is_high_alert', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('high_alert_category', sa.String(length=64), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_medication_barcode_directory_barcode'), 'medication_barcode_directory', ['barcode'], unique=True)
    op.create_index(op.f('ix_medication_barcode_directory_medication_name'), 'medication_barcode_directory', ['medication_name'], unique=False)
    op.create_index(op.f('ix_medication_barcode_directory_rxnorm_code'), 'medication_barcode_directory', ['rxnorm_code'], unique=False)
    op.create_index(op.f('ix_medication_barcode_directory_is_high_alert'), 'medication_barcode_directory', ['is_high_alert'], unique=False)

    # 2. Medication Administration Records Table
    op.create_table(
        'medication_administration_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mar_id', sa.String(length=64), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('facility_id', sa.String(length=64), server_default='FAC-METRO-MAIN', nullable=False),
        sa.Column('medication_name', sa.String(length=255), nullable=False),
        sa.Column('medication_code', sa.String(length=64), nullable=False),
        sa.Column('prescribed_dose', sa.String(length=64), nullable=False),
        sa.Column('prescribed_route', sa.String(length=64), nullable=False),
        sa.Column('prescribed_frequency', sa.String(length=64), server_default='daily', nullable=False),
        sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actual_admin_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='scheduled', nullable=False),
        sa.Column('administering_nurse_id', sa.Integer(), nullable=True),
        sa.Column('administered_dose', sa.String(length=64), nullable=True),
        sa.Column('administered_route', sa.String(length=64), nullable=True),
        sa.Column('site_of_administration', sa.String(length=100), nullable=True),
        sa.Column('is_high_alert', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('requires_dual_witness', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('dual_witness_user_id', sa.Integer(), nullable=True),
        sa.Column('dual_witness_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('variance_reason', sa.Text(), nullable=True),
        sa.Column('patient_response_notes', sa.Text(), nullable=True),
        sa.Column('vital_signs_pre_admin_json', sa.JSON(), nullable=True),
        sa.Column('barcode_scanned_patient_id', sa.String(length=64), nullable=True),
        sa.Column('barcode_scanned_med_id', sa.String(length=128), nullable=True),
        sa.Column('verification_passed', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['clinical_orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['facility_id'], ['clinical_facilities.facility_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['administering_nurse_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['dual_witness_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_medication_administration_records_mar_id'), 'medication_administration_records', ['mar_id'], unique=True)
    op.create_index(op.f('ix_medication_administration_records_patient_id'), 'medication_administration_records', ['patient_id'], unique=False)
    op.create_index(op.f('ix_medication_administration_records_facility_id'), 'medication_administration_records', ['facility_id'], unique=False)
    op.create_index(op.f('ix_medication_administration_records_medication_name'), 'medication_administration_records', ['medication_name'], unique=False)
    op.create_index(op.f('ix_medication_administration_records_scheduled_time'), 'medication_administration_records', ['scheduled_time'], unique=False)
    op.create_index(op.f('ix_medication_administration_records_status'), 'medication_administration_records', ['status'], unique=False)
    op.create_index(op.f('ix_medication_administration_records_is_high_alert'), 'medication_administration_records', ['is_high_alert'], unique=False)

    # 3. BCMA Bedside Verification Logs Table
    op.create_table(
        'bcma_verification_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('verification_id', sa.String(length=64), nullable=False),
        sa.Column('mar_id', sa.Integer(), nullable=True),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('scanned_patient_barcode', sa.String(length=128), nullable=False),
        sa.Column('scanned_med_barcode', sa.String(length=128), nullable=False),
        sa.Column('patient_matched', sa.Boolean(), nullable=False),
        sa.Column('medication_matched', sa.Boolean(), nullable=False),
        sa.Column('dose_matched', sa.Boolean(), nullable=False),
        sa.Column('route_matched', sa.Boolean(), nullable=False),
        sa.Column('time_matched', sa.Boolean(), nullable=False),
        sa.Column('verification_status', sa.String(length=32), nullable=False),
        sa.Column('mismatch_details_json', sa.JSON(), nullable=True),
        sa.Column('override_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['mar_id'], ['medication_administration_records.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bcma_verification_logs_verification_id'), 'bcma_verification_logs', ['verification_id'], unique=True)
    op.create_index(op.f('ix_bcma_verification_logs_patient_id'), 'bcma_verification_logs', ['patient_id'], unique=False)
    op.create_index(op.f('ix_bcma_verification_logs_verification_status'), 'bcma_verification_logs', ['verification_status'], unique=False)


def downgrade() -> None:
    op.drop_table('bcma_verification_logs')
    op.drop_table('medication_administration_records')
    op.drop_table('medication_barcode_directory')
