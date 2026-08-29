import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { TransitionsWorkspace } from '../components/transitions/TransitionsWorkspace';
import { transitionsApi } from '../api/client';
import { User } from '../types';

vi.mock('../api/client', () => ({
  transitionsApi: {
    listHandoffs: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          handoff_id: 'HDF-20260829-001',
          patient_id: 10,
          framework: 'ipass',
          handoff_type: 'shift_change',
          illness_severity: 'watcher',
          status: 'active',
          summary: 'Patient undergoing diuretic management. Stable BP and O2 saturations.',
          action_items_json: [
            {
              item_id: 'ACT-01',
              task_description: 'Check evening potassium level.',
              role_required: 'resident',
              priority: 'ROUTINE',
              is_completed: false,
            },
          ],
          situational_awareness_json: [
            {
              plan_id: 'CTG-01',
              trigger_condition: 'If systolic BP < 90 mmHg',
              immediate_action: 'Notify hospitalist and hold antihypertensives.',
              escalation_contact: 'Rapid response team',
            },
          ],
          is_ai_generated: true,
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    getHandoff: vi.fn(),
    createHandoff: vi.fn(),
    synthesizeHandoff: vi.fn().mockResolvedValue({
      id: 2,
      handoff_id: 'HDF-20260829-002',
      patient_id: 10,
      framework: 'sbar',
      handoff_type: 'shift_change',
      illness_severity: 'stable',
      status: 'draft',
      summary: 'SITUATION: Beatrice Holloway. BACKGROUND: HF. ASSESSMENT: Stable. RECOMMENDATION: Routine care.',
      action_items_json: [],
      situational_awareness_json: [],
      is_ai_generated: true,
      created_at: '2026-08-29T10:05:00Z',
      updated_at: '2026-08-29T10:05:00Z',
    }),
    updateHandoff: vi.fn(),
    acknowledgeHandoff: vi.fn().mockResolvedValue({
      id: 1,
      handoff_id: 'HDF-20260829-001',
      patient_id: 10,
      framework: 'ipass',
      handoff_type: 'shift_change',
      illness_severity: 'watcher',
      status: 'acknowledged',
      summary: 'Patient undergoing diuretic management.',
      synthesis_notes: 'Read-back verified and accepted.',
      is_ai_generated: true,
      acknowledged_at: '2026-08-29T10:10:00Z',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:10:00Z',
    }),
    listDischargeProtocols: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          discharge_id: 'DIS-20260829-001',
          patient_id: 10,
          status: 'under_review',
          disposition: 'home_self_care',
          hospital_course_summary: 'Inpatient stay completed with successful diuresis and symptom control.',
          primary_discharge_diagnosis: 'Acute on Chronic Systolic Heart Failure',
          secondary_diagnoses_json: ['Hypertension'],
          medication_reconciliation_json: [
            {
              medication_name: 'Lisinopril',
              dose: '20 mg',
              route: 'oral',
              frequency: 'daily',
              reconciliation_status: 'continued',
              clinical_rationale: 'Blood pressure control',
            },
          ],
          followup_instructions_json: [
            {
              provider_or_specialty: 'Cardiology Clinic',
              timeframe: '10 days',
              purpose: 'Post-discharge review',
            },
          ],
          pending_tests_json: [],
          warning_symptoms_json: [
            {
              symptom_title: 'Sudden chest pain or shortness of breath',
              urgency_level: 'EMERGENCY_911',
              action_instructions: 'Call 911 immediately.',
            },
          ],
          activity_and_diet_instructions: 'Low sodium diet < 2g/day.',
          is_ai_generated: true,
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    getDischargeProtocol: vi.fn(),
    createDischargeProtocol: vi.fn(),
    synthesizeDischargeProtocol: vi.fn().mockResolvedValue({
      id: 2,
      discharge_id: 'DIS-20260829-002',
      patient_id: 10,
      status: 'draft',
      disposition: 'home_health_services',
      hospital_course_summary: 'Synthesized discharge summary package.',
      primary_discharge_diagnosis: 'Hypertensive Heart Disease',
      medication_reconciliation_json: [],
      is_ai_generated: true,
      created_at: '2026-08-29T10:05:00Z',
      updated_at: '2026-08-29T10:05:00Z',
    }),
    updateDischargeProtocol: vi.fn(),
    signoffDischargeProtocol: vi.fn().mockResolvedValue({
      id: 1,
      discharge_id: 'DIS-20260829-001',
      patient_id: 10,
      status: 'ready_for_discharge',
      disposition: 'home_self_care',
      hospital_course_summary: 'Inpatient stay completed.',
      primary_discharge_diagnosis: 'Acute on Chronic Systolic Heart Failure',
      signed_off_at: '2026-08-29T10:15:00Z',
      is_ai_generated: true,
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:15:00Z',
    }),
  },
}));

const mockDoctorUser: User = {
  id: 1,
  name: 'Dr. Gregory House',
  email: 'house@hospital.org',
  role: 'doctor' as any,
  is_active: true,
  created_at: '2026-08-29T10:00:00Z',
  updated_at: '2026-08-29T10:00:00Z',
};


describe('TransitionsWorkspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders clinical handoffs tab and displays handoff summary and action items', async () => {
    render(<TransitionsWorkspace patientId="PAT-001" currentUser={mockDoctorUser} />);

    await waitFor(() => {
      expect(screen.getByText(/Clinical Transitions of Care & Discharge/i)).toBeInTheDocument();
      expect(screen.getByText(/IPASS Handoff Protocol/i)).toBeInTheDocument();
      expect(screen.getByText(/Check evening potassium level./i)).toBeInTheDocument();
      expect(screen.getByText(/If systolic BP < 90 mmHg/i)).toBeInTheDocument();
    });
  });

  it('opens synthesize handoff modal and triggers AI handoff synthesis', async () => {
    render(<TransitionsWorkspace patientId="PAT-001" currentUser={mockDoctorUser} />);

    await waitFor(() => {
      expect(screen.getByText(/Synthesize AI Handoff/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Synthesize AI Handoff/i));
    expect(screen.getByText(/Synthesize Clinical Shift Handoff/i)).toBeInTheDocument();

    const generateBtn = screen.getByText(/Generate Handoff/i);
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(transitionsApi.synthesizeHandoff).toHaveBeenCalledWith('PAT-001', {
        framework: 'ipass',
        handoff_type: 'shift_change',
        custom_context: undefined,
      });
    });
  });

  it('switches to discharge tab and displays medication reconciliation and warning signs', async () => {
    render(<TransitionsWorkspace patientId="PAT-001" currentUser={mockDoctorUser} />);

    await waitFor(() => {
      expect(screen.getByText(/Discharge Protocols/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/Discharge Protocols/i));

    await waitFor(() => {
      expect(screen.getAllByText(/Acute on Chronic Systolic Heart Failure/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Lisinopril/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/CONTINUED/i)).toBeInTheDocument();
      expect(screen.getByText(/Sudden chest pain or shortness of breath/i)).toBeInTheDocument();
    });


  });
});
