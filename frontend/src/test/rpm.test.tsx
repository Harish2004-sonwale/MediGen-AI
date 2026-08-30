import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { RPMWorkspace } from '../components/rpm/RPMWorkspace';
import { rpmApi, patientsApi } from '../api/client';

vi.mock('../api/client', () => ({
  patientsApi: {
    list: vi.fn().mockResolvedValue([
      {
        id: 1,
        patient_id: 'PAT-RPM-001',
        first_name: 'Arthur',
        last_name: 'Dent',
        gender: 'male',
        date_of_birth: '1975-06-15',
        is_active: true,
      },
    ]),
  },
  rpmApi: {
    listPrograms: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          program_id: 'RPM-PROG-001',
          patient_id: 1,
          patient_identifier: 'PAT-RPM-001',
          patient_name: 'Arthur Dent',
          condition_name: 'Essential Hypertension',
          program_name: 'Longitudinal Cardiovascular RPM Protocol',
          target_cadence_days: 1,
          clinical_goals: ['Maintain BP < 130/80 mmHg'],
          status: 'active',
          enrolled_at: '2026-08-29T10:00:00Z',
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    listDevices: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          device_id: 'DEV-BP-001',
          patient_id: 1,
          patient_identifier: 'PAT-RPM-001',
          patient_name: 'Arthur Dent',
          device_type: 'blood_pressure_cuff',
          manufacturer: 'Omron Healthcare',
          model_number: 'BP-7000',
          serial_number: 'OMR-12345',
          status: 'active',
          supported_measurements: ['systolic_bp', 'diastolic_bp'],
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    listObservations: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          observation_id: 'OBS-RPM-001',
          patient_id: 1,
          patient_identifier: 'PAT-RPM-001',
          patient_name: 'Arthur Dent',
          observation_type: 'systolic_bp',
          numeric_value: 124.0,
          secondary_value: 82.0,
          unit_of_measure: 'mmHg',
          source_type: 'bluetooth_sync',
          classification: 'normal',
          recorded_at: '2026-08-29T11:00:00Z',
          created_at: '2026-08-29T11:00:00Z',
        },
      ],
    }),
    listAlerts: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          alert_id: 'ALT-RPM-001',
          patient_id: 1,
          patient_identifier: 'PAT-RPM-001',
          patient_name: 'Arthur Dent',
          severity: 'CRITICAL',
          status: 'open',
          escalation_reason: 'Hypertensive Crisis Telemetry: 195/125 mmHg',
          linked_care_task_id: 10,
          created_at: '2026-08-29T11:05:00Z',
          updated_at: '2026-08-29T11:05:00Z',
        },
      ],
    }),
    listTelehealthSessions: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          session_id: 'TELE-001',
          patient_id: 1,
          patient_identifier: 'PAT-RPM-001',
          patient_name: 'Arthur Dent',
          clinician_user_id: 2,
          clinician_name: 'Dr. Physician',
          status: 'scheduled',
          scheduled_start: '2026-08-30T14:00:00Z',
          visit_reason: 'Remote Telemetry Review',
          pre_visit_rpm_summary_json: {
            key_discussion_points: ['Review daily morning BP readings.'],
          },
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    listPromDefinitions: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          prom_id: 'PROM-PHQ9',
          title: 'Patient Health Questionnaire (PHQ-9)',
          domain: 'mental_health',
          version: '1.0.0',
          scoring_method: 'sum',
          questions_json: [
            {
              id: '1',
              prompt: 'Little interest or pleasure in doing things',
              options: [
                { value: 0, label: 'Not at all', score: 0 },
                { value: 1, label: 'Several days', score: 1 },
                { value: 2, label: 'More than half the days', score: 2 },
                { value: 3, label: 'Nearly every day', score: 3 },
              ],
            },
          ],
          interpretation_ranges_json: {},
          is_active: true,
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    listPromResponses: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          response_id: 'PRES-001',
          prom_id: 1,
          prom_identifier: 'PROM-PHQ9',
          prom_title: 'Patient Health Questionnaire (PHQ-9)',
          patient_id: 1,
          patient_identifier: 'PAT-RPM-001',
          patient_name: 'Arthur Dent',
          answers_json: { '1': 1 },
          calculated_score: 1.0,
          severity_interpretation: 'Minimal Depression',
          safety_flags_json: [],
          completed_at: '2026-08-29T10:30:00Z',
          created_at: '2026-08-29T10:30:00Z',
        },
      ],
    }),
    getPatientSummary: vi.fn().mockResolvedValue({
      patient_id: 'PAT-RPM-001',
      total_observations_count: 5,
      critical_observations_count: 1,
      abnormal_observations_count: 1,
      normal_observations_count: 3,
      average_systolic_bp: 126.0,
      average_diastolic_bp: 81.0,
      adherence_rate: 92.5,
      active_alerts_count: 1,
    }),
    enrollProgram: vi.fn(),
    registerDevice: vi.fn(),
    ingestObservation: vi.fn(),
    acknowledgeAlert: vi.fn().mockResolvedValue({ status: 'acknowledged' }),
    resolveAlert: vi.fn().mockResolvedValue({ status: 'resolved' }),
    submitPromResponse: vi.fn(),
    scheduleTelehealthSession: vi.fn(),
    updateTelehealthSession: vi.fn(),
  },
}));

describe('RPMWorkspace Component (Phase 9.0.15)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Clinician Dashboard with telemetry and programs', async () => {
    render(
      <RPMWorkspace
        currentUser={{ id: 1, email: 'doc@hospital.org', name: 'Dr. Physician', role: 'doctor' as any, is_active: true, created_at: '', updated_at: '' }}
        activePatient={{ id: 1, patient_id: 'PAT-RPM-001', first_name: 'Arthur', last_name: 'Dent', email: 'arthur@hospital.org', gender: 'male' as any, date_of_birth: '1975-06-15', is_active: true, created_at: '' }}

      />
    );

    await waitFor(() => {
      expect(screen.getByText('Remote Patient Monitoring (RPM) & Telehealth')).toBeInTheDocument();
    });

    expect(screen.getByText(/Clinician Hub/i)).toBeInTheDocument();
    expect(screen.getByText(/Continuous Physiological Telemetry/i)).toBeInTheDocument();
    expect(screen.getByText(/Virtual Care Consultations/i)).toBeInTheDocument();
  });

  it('displays urgent escalation alerts with acknowledge button', async () => {
    render(
      <RPMWorkspace
        currentUser={{ id: 1, email: 'doc@hospital.org', name: 'Dr. Physician', role: 'doctor' as any, is_active: true, created_at: '', updated_at: '' }}
        activePatient={{ id: 1, patient_id: 'PAT-RPM-001', first_name: 'Arthur', last_name: 'Dent', email: 'arthur@hospital.org', gender: 'male' as any, date_of_birth: '1975-06-15', is_active: true, created_at: '' }}

      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Urgent RPM Telemetry Escalations/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Hypertensive Crisis Telemetry: 195\/125 mmHg/i)).toBeInTheDocument();

    const ackBtn = screen.getByText('Acknowledge');
    fireEvent.click(ackBtn);

    await waitFor(() => {
      expect(rpmApi.acknowledgeAlert).toHaveBeenCalledWith('ALT-RPM-001', expect.any(String));
    });
  });

  it('switches to Patient & PROMs View and renders completed surveys', async () => {
    render(
      <RPMWorkspace
        currentUser={{ id: 2, email: 'arthur@hospital.org', name: 'Arthur Dent', role: 'patient' as any, is_active: true, created_at: '', updated_at: '' }}
        activePatient={{ id: 1, patient_id: 'PAT-RPM-001', first_name: 'Arthur', last_name: 'Dent', email: 'arthur@hospital.org', gender: 'male' as any, date_of_birth: '1975-06-15', is_active: true, created_at: '' }}

      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Outcome Questionnaires/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Completed Outcome Assessments/i)).toBeInTheDocument();
    expect(screen.getByText(/Minimal Depression/i)).toBeInTheDocument();
  });

  it('allows opening standardized PROM questionnaire survey modal', async () => {
    render(
      <RPMWorkspace
        currentUser={{ id: 2, email: 'arthur@hospital.org', name: 'Arthur Dent', role: 'patient' as any, is_active: true, created_at: '', updated_at: '' }}
        activePatient={{ id: 1, patient_id: 'PAT-RPM-001', first_name: 'Arthur', last_name: 'Dent', email: 'arthur@hospital.org', gender: 'male' as any, date_of_birth: '1975-06-15', is_active: true, created_at: '' }}

      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Start/i)).toBeInTheDocument();
    });

    const startBtn = screen.getByText(/Start/i);
    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(screen.getByText(/Over the last 2 weeks/i)).toBeInTheDocument();
    });
  });
});
