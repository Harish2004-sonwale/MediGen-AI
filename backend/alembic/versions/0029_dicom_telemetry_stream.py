"""Phase 9.0.29: Advanced Multi-Modal Medical Vision, DICOM PACS Viewer & Real-Time Waveforms

Revision ID: 0029_dicom_telemetry_stream
Revises: 0028_emar_bcma_administration
Create Date: 2026-09-02 11:32:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0029_dicom_telemetry_stream'
down_revision = '0028_emar_bcma_administration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. DICOM Study Records Table
    op.create_table(
        'dicom_study_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('study_instance_uid', sa.String(length=128), nullable=False),
        sa.Column('study_id', sa.String(length=64), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('facility_id', sa.String(length=64), server_default='FAC-METRO-MAIN', nullable=False),
        sa.Column('accession_number', sa.String(length=64), nullable=False),
        sa.Column('study_description', sa.String(length=255), nullable=False),
        sa.Column('modality', sa.String(length=32), nullable=False),
        sa.Column('body_site', sa.String(length=64), server_default='CHEST', nullable=False),
        sa.Column('study_datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('referring_physician', sa.String(length=150), nullable=True),
        sa.Column('performing_institution', sa.String(length=150), server_default='MetroHealth Diagnostic Imaging Center', nullable=False),
        sa.Column('number_of_series', sa.Integer(), server_default='1', nullable=False),
        sa.Column('number_of_instances', sa.Integer(), server_default='1', nullable=False),
        sa.Column('dicom_attributes_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['facility_id'], ['clinical_facilities.facility_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_dicom_study_records_study_instance_uid'), 'dicom_study_records', ['study_instance_uid'], unique=True)
    op.create_index(op.f('ix_dicom_study_records_study_id'), 'dicom_study_records', ['study_id'], unique=True)
    op.create_index(op.f('ix_dicom_study_records_accession_number'), 'dicom_study_records', ['accession_number'], unique=True)
    op.create_index(op.f('ix_dicom_study_records_patient_id'), 'dicom_study_records', ['patient_id'], unique=False)
    op.create_index(op.f('ix_dicom_study_records_modality'), 'dicom_study_records', ['modality'], unique=False)
    op.create_index(op.f('ix_dicom_study_records_study_datetime'), 'dicom_study_records', ['study_datetime'], unique=False)

    # 2. DICOM Series Records Table
    op.create_table(
        'dicom_series_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('series_instance_uid', sa.String(length=128), nullable=False),
        sa.Column('study_id', sa.Integer(), nullable=False),
        sa.Column('series_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('series_description', sa.String(length=255), nullable=False),
        sa.Column('modality', sa.String(length=32), nullable=False),
        sa.Column('body_part_examined', sa.String(length=64), server_default='CHEST', nullable=False),
        sa.Column('patient_position', sa.String(length=32), server_default='HFS', nullable=False),
        sa.Column('slice_thickness_mm', sa.Float(), nullable=True),
        sa.Column('pixel_spacing_row_mm', sa.Float(), server_default='0.7', nullable=True),
        sa.Column('pixel_spacing_col_mm', sa.Float(), server_default='0.7', nullable=True),
        sa.Column('window_center_default', sa.Float(), server_default='40.0', nullable=False),
        sa.Column('window_width_default', sa.Float(), server_default='400.0', nullable=False),
        sa.Column('rescale_intercept', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('rescale_slope', sa.Float(), server_default='1.0', nullable=False),
        sa.Column('number_of_instances', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['study_id'], ['dicom_study_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_dicom_series_records_series_instance_uid'), 'dicom_series_records', ['series_instance_uid'], unique=True)
    op.create_index(op.f('ix_dicom_series_records_study_id'), 'dicom_series_records', ['study_id'], unique=False)

    # 3. DICOM SOP Instance Records Table
    op.create_table(
        'dicom_instance_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sop_instance_uid', sa.String(length=128), nullable=False),
        sa.Column('series_id', sa.Integer(), nullable=False),
        sa.Column('sop_class_uid', sa.String(length=128), server_default='1.2.840.10008.5.1.4.1.1.2', nullable=False),
        sa.Column('instance_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('rows', sa.Integer(), server_default='512', nullable=False),
        sa.Column('columns', sa.Integer(), server_default='512', nullable=False),
        sa.Column('bits_allocated', sa.Integer(), server_default='16', nullable=False),
        sa.Column('bits_stored', sa.Integer(), server_default='12', nullable=False),
        sa.Column('high_bit', sa.Integer(), server_default='11', nullable=False),
        sa.Column('pixel_representation', sa.Integer(), server_default='0', nullable=False),
        sa.Column('photometric_interpretation', sa.String(length=32), server_default='MONOCHROME2', nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('thumbnail_path', sa.String(length=500), nullable=True),
        sa.Column('pixel_data_preview_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['series_id'], ['dicom_series_records.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_dicom_instance_records_sop_instance_uid'), 'dicom_instance_records', ['sop_instance_uid'], unique=True)
    op.create_index(op.f('ix_dicom_instance_records_series_id'), 'dicom_instance_records', ['series_id'], unique=False)

    # 4. AI Isolated Lesion Findings Table
    op.create_table(
        'ai_isolated_lesion_findings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('finding_id', sa.String(length=64), nullable=False),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('lesion_type', sa.String(length=64), nullable=False),
        sa.Column('anatomical_location', sa.String(length=128), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('severity', sa.String(length=32), server_default='MODERATE', nullable=False),
        sa.Column('geometry_type', sa.String(length=32), server_default='BOUNDING_BOX', nullable=False),
        sa.Column('coordinates_json', sa.JSON(), nullable=False),
        sa.Column('heatmap_matrix_json', sa.JSON(), nullable=True),
        sa.Column('model_name', sa.String(length=100), server_default='MediGen-VisionTransformer-v2.1', nullable=False),
        sa.Column('model_version', sa.String(length=32), server_default='2.1.0', nullable=False),
        sa.Column('clinician_review_status', sa.String(length=32), server_default='pending_review', nullable=False),
        sa.Column('reviewed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['dicom_instance_records.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_isolated_lesion_findings_finding_id'), 'ai_isolated_lesion_findings', ['finding_id'], unique=True)
    op.create_index(op.f('ix_ai_isolated_lesion_findings_instance_id'), 'ai_isolated_lesion_findings', ['instance_id'], unique=False)
    op.create_index(op.f('ix_ai_isolated_lesion_findings_lesion_type'), 'ai_isolated_lesion_findings', ['lesion_type'], unique=False)
    op.create_index(op.f('ix_ai_isolated_lesion_findings_clinician_review_status'), 'ai_isolated_lesion_findings', ['clinician_review_status'], unique=False)

    # 5. ECG Waveform Telemetry Sessions Table
    op.create_table(
        'ecg_waveform_sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('facility_id', sa.String(length=64), server_default='FAC-METRO-MAIN', nullable=False),
        sa.Column('encounter_id', sa.Integer(), nullable=True),
        sa.Column('device_id', sa.String(length=64), server_default='ICU-MONITOR-BED-04', nullable=False),
        sa.Column('lead_configuration', sa.String(length=32), server_default='12_LEAD', nullable=False),
        sa.Column('sample_rate_hz', sa.Integer(), server_default='250', nullable=False),
        sa.Column('amplitude_unit', sa.String(length=16), server_default='mV', nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), server_default='60', nullable=False),
        sa.Column('current_rhythm_state', sa.String(length=64), server_default='normal_sinus_rhythm', nullable=False),
        sa.Column('heart_rate_bpm', sa.Integer(), server_default='75', nullable=False),
        sa.Column('multi_lead_samples_json', sa.JSON(), nullable=False),
        sa.Column('is_active_streaming', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['facility_id'], ['clinical_facilities.facility_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['encounter_id'], ['encounters.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ecg_waveform_sessions_session_id'), 'ecg_waveform_sessions', ['session_id'], unique=True)
    op.create_index(op.f('ix_ecg_waveform_sessions_patient_id'), 'ecg_waveform_sessions', ['patient_id'], unique=False)
    op.create_index(op.f('ix_ecg_waveform_sessions_start_time'), 'ecg_waveform_sessions', ['start_time'], unique=False)

    # 6. Arrhythmia Alert Events Table
    op.create_table(
        'arrhythmia_alert_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_id', sa.String(length=64), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=32), server_default='critical', nullable=False),
        sa.Column('lead_involved', sa.String(length=32), server_default='II', nullable=False),
        sa.Column('heart_rate_bpm', sa.Integer(), nullable=False),
        sa.Column('st_elevation_mm', sa.Float(), nullable=True),
        sa.Column('alert_description', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('cooldown_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('acknowledged_by_user_id', sa.Integer(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clinician_action_taken', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['ecg_waveform_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['acknowledged_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_arrhythmia_alert_events_alert_id'), 'arrhythmia_alert_events', ['alert_id'], unique=True)
    op.create_index(op.f('ix_arrhythmia_alert_events_session_id'), 'arrhythmia_alert_events', ['session_id'], unique=False)
    op.create_index(op.f('ix_arrhythmia_alert_events_patient_id'), 'arrhythmia_alert_events', ['patient_id'], unique=False)
    op.create_index(op.f('ix_arrhythmia_alert_events_event_type'), 'arrhythmia_alert_events', ['event_type'], unique=False)
    op.create_index(op.f('ix_arrhythmia_alert_events_status'), 'arrhythmia_alert_events', ['status'], unique=False)
    op.create_index(op.f('ix_arrhythmia_alert_events_triggered_at'), 'arrhythmia_alert_events', ['triggered_at'], unique=False)


def downgrade() -> None:
    op.drop_table('arrhythmia_alert_events')
    op.drop_table('ecg_waveform_sessions')
    op.drop_table('ai_isolated_lesion_findings')
    op.drop_table('dicom_instance_records')
    op.drop_table('dicom_series_records')
    op.drop_table('dicom_study_records')
