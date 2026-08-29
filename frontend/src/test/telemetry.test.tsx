import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { VitalTelemetryWorkspace } from '../components/telemetry/VitalTelemetryWorkspace';
import { vitalsApi } from '../api/client';

vi.mock('../api/client', () => ({
  vitalsApi: {
    getLatest: vi.fn().mockResolvedValue({
      id: 1,
      reading_id: 'VIT-20260829-001',
      patient_id: 1,
      heart_rate: 108,
      systolic_bp: 130,
      diastolic_bp: 85,
      respiratory_rate: 26,
      temperature_c: 37.2,
      spo2_percent: 86.0,
      weight_kg: 72.0,
      device_id: 'bedside_01',
      source: 'monitor',
      measured_at: '2026-08-29T10:00:00Z',
      created_at: '2026-08-29T10:00:00Z',
    }),
    list: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          reading_id: 'VIT-20260829-001',
          patient_id: 1,
          heart_rate: 108,
          systolic_bp: 130,
          diastolic_bp: 85,
          respiratory_rate: 26,
          temperature_c: 37.2,
          spo2_percent: 86.0,
          weight_kg: 72.0,
          device_id: 'bedside_01',
          source: 'monitor',
          measured_at: '2026-08-29T10:00:00Z',
          created_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    listAlerts: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          alert_id: 'ALT-20260829-001',
          patient_id: 1,
          reading_id: 1,
          alert_type: 'vital_hypoxia',
          severity: 'CRITICAL',
          status: 'active',
          title: 'Critical Hypoxia Alert (SpO2 86%)',
          explanation: 'SpO2 reading of 86% is below critical threshold (<90%).',
          parameters_json: { spo2_percent: 86.0 },
          recurrence_count: 1,
          last_triggered_at: '2026-08-29T10:00:00Z',
          created_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    simulate: vi.fn().mockResolvedValue({
      id: 2,
      reading_id: 'VIT-20260829-002',
      patient_id: 1,
      heart_rate: 72,
      systolic_bp: 120,
      diastolic_bp: 80,
      respiratory_rate: 16,
      temperature_c: 37.0,
      spo2_percent: 98.0,
      source: 'simulator',
      measured_at: '2026-08-29T10:05:00Z',
      created_at: '2026-08-29T10:05:00Z',
    }),
    acknowledgeAlert: vi.fn().mockResolvedValue({
      id: 1,
      alert_id: 'ALT-20260829-001',
      status: 'acknowledged',
    }),
    dismissAlert: vi.fn().mockResolvedValue({
      id: 1,
      alert_id: 'ALT-20260829-001',
      status: 'dismissed',
      dismissal_reason: 'Patient oxygen mask was briefly off; rechecked and normal.',
    }),
  },
}));

describe('Vital Telemetry & CDS Alerting Workspace', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders physiological vital snapshot cards and critical CDS alert', async () => {
    render(<VitalTelemetryWorkspace patientId="PAT-001" />);

    const spo2Values = await screen.findAllByText('86%');
    expect(spo2Values.length).toBeGreaterThan(0);

    const alertTitles = await screen.findAllByText(/Critical Hypoxia Alert/i);
    expect(alertTitles.length).toBeGreaterThan(0);

    const alertSeverity = await screen.findByText('CRITICAL');
    expect(alertSeverity).toBeInTheDocument();
  });

  it('acknowledges an active clinical alert', async () => {
    render(<VitalTelemetryWorkspace patientId="PAT-001" />);

    await screen.findAllByText(/Critical Hypoxia Alert/i);

    const ackBtn = screen.getByText('✓ Acknowledge');
    fireEvent.click(ackBtn);

    expect(vitalsApi.acknowledgeAlert).toHaveBeenCalledWith('ALT-20260829-001');
  });

  it('dismisses a clinical alert with clinical reason', async () => {
    render(<VitalTelemetryWorkspace patientId="PAT-001" />);

    await screen.findAllByText(/Critical Hypoxia Alert/i);

    const dismissBtn = screen.getByText('✕ Dismiss');
    fireEvent.click(dismissBtn);

    const reasonInput = screen.getByPlaceholderText(/Mandatory clinical justification/i);
    fireEvent.change(reasonInput, {
      target: { value: 'Patient oxygen mask was briefly off; rechecked and normal.' },
    });

    const confirmBtn = screen.getByText('Confirm Dismissal');
    fireEvent.click(confirmBtn);

    expect(vitalsApi.dismissAlert).toHaveBeenCalledWith(
      'ALT-20260829-001',
      'Patient oxygen mask was briefly off; rechecked and normal.'
    );
  });
});
