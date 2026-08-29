import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { CohortWorkspace } from '../components/cohorts/CohortWorkspace';
import { cohortsApi } from '../api/client';
import { User } from '../types';


vi.mock('../api/client', () => ({
  cohortsApi: {
    list: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          cohort_id: 'COHORT-20260829-001',
          name: 'Geriatric Cardiac Registry',
          description: 'Longitudinal tracking of patients with chronic heart failure.',
          cohort_type: 'disease_registry',
          criteria_json: { min_age: 65, conditions: ['Heart Failure'] },
          is_dynamic: true,
          created_by_user_id: 1,
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
          member_count: 1,
        },
      ],
    }),
    listMembers: vi.fn().mockResolvedValue([
      {
        id: 1,
        cohort_id: 1,
        patient_id: 1,
        patient_identifier: 'PAT-001',
        patient_name: 'Eleanor Vance',
        enrolled_at: '2026-08-29T10:00:00Z',
        status: 'active',
        notes: 'Auto-enrolled',
        latest_risk_score: 78.5,
        latest_risk_tier: 'CRITICAL',
      },
    ]),
    getAnalytics: vi.fn().mockResolvedValue({
      cohort_id: 'COHORT-20260829-001',
      name: 'Geriatric Cardiac Registry',
      cohort_type: 'disease_registry',
      total_members: 1,
      risk_tier_distribution: { CRITICAL: 1, HIGH: 0, MODERATE: 0, LOW: 0 },
      mean_risk_score: 78.5,
      high_risk_patient_count: 1,
      active_alerts_count: 2,
      active_care_plans_count: 1,
      overdue_tasks_count: 1,
      generated_at: '2026-08-29T10:00:00Z',
    }),
    create: vi.fn().mockResolvedValue({
      id: 2,
      cohort_id: 'COHORT-20260829-002',
      name: 'Uncontrolled Diabetes Cohort',
      description: 'Patients with HbA1c elevation.',
      cohort_type: 'disease_registry',
      is_dynamic: true,
      member_count: 0,
    }),
    calculateRisk: vi.fn().mockResolvedValue({
      id: 1,
      assessment_id: 'RISK-20260829-001',
      patient_id: 1,
      risk_type: 'readmission_30d',
      risk_score: 78.5,
      risk_tier: 'CRITICAL',
      predicted_outcome: '78.5% estimated probability of hospital readmission within 30 days.',
      contributing_factors_json: [
        {
          factor_name: 'Geriatric Advanced Age (>=75)',
          category: 'demographics',
          severity: 'HIGH',
          observed_value: '76 years',
          clinical_rationale: 'Reduced physiological reserve.',
        },
      ],
      mitigation_recommendations_json: [
        {
          action_title: 'Care Coordinator Outreach & Task Reconciliation',
          priority: 'URGENT',
          suggested_task_type: 'patient_education',
          target_timeline_days: 3,
          rational: 'Re-engage patient to close open care gaps.',
        },
      ],
      is_ai_generated: true,
      assessed_at: '2026-08-29T10:00:00Z',
      created_at: '2026-08-29T10:00:00Z',
    }),
  },
}));

describe('Clinical Cohort Analytics & Population Risk Workspace', () => {
  const mockUser: User = {
    id: 1,
    name: 'Dr. Population Lead',
    email: 'lead@hospital.org',
    role: 'doctor',
    is_active: true,
    created_at: '2026-08-29T10:00:00Z',
    updated_at: '2026-08-29T10:00:00Z',
  };



  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders cohort overview, KPI analytics, and enrolled member roster', async () => {
    render(<CohortWorkspace currentUser={mockUser} currentPatientId="PAT-001" />);

    expect(await screen.findByText('Geriatric Cardiac Registry')).toBeInTheDocument();
    expect(await screen.findByText('Eleanor Vance')).toBeInTheDocument();
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
    expect(screen.getByText('78.5 / 100')).toBeInTheDocument();
    expect(screen.getByText('⚡ Dynamic Sync')).toBeInTheDocument();
  });


  it('opens new cohort creation modal and triggers registry creation', async () => {
    render(<CohortWorkspace currentUser={mockUser} currentPatientId="PAT-001" />);

    const newBtn = await screen.findByText('New Registry / Cohort');
    fireEvent.click(newBtn);

    expect(screen.getByText('➕ Create Disease Registry / Cohort')).toBeInTheDocument();
  });

  it('triggers clinical risk stratification and displays assessment breakdown modal', async () => {
    render(<CohortWorkspace currentUser={mockUser} currentPatientId="PAT-001" />);

    const scoreBtn = await screen.findByText('⚡ Score Risk');
    fireEvent.click(scoreBtn);

    expect(screen.getByText('⚡ Run Clinical Risk Stratification')).toBeInTheDocument();

    const calcBtn = screen.getByText('Calculate Score');
    fireEvent.click(calcBtn);

    await waitFor(() => {
      expect(cohortsApi.calculateRisk).toHaveBeenCalledWith('PAT-001', {
        risk_type: 'readmission_30d',
      });
    });

    expect(await screen.findByText('Clinical Risk Assessment Breakdown')).toBeInTheDocument();
    expect(screen.getByText('Contributing Clinical Factors')).toBeInTheDocument();
    expect(screen.getByText('Recommended Actionable Interventions')).toBeInTheDocument();
  });
});
