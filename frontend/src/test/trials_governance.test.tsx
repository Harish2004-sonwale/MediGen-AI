import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { TrialsGovernanceWorkspace } from '../components/trials/TrialsGovernanceWorkspace';
import * as apiClient from '../api/client';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof apiClient>('../api/client');
  return {
    ...actual,
    trialsGovernanceApi: {
      getPrescreening: vi.fn().mockResolvedValue({
        patient_id: 'PAT-00101',
        evaluated_at: '2026-09-02T00:00:00Z',
        total_trials_screened: 1,
        eligible_trials_count: 1,
        evaluations: [
          {
            trial_id: 1,
            nct_number: 'NCT05988102',
            title: 'Phase II Targeted EGFR/MET Bispecific Monoclonal Antibody in Advanced NSCLC',
            phase: 'phase_2',
            disease_condition: 'Non-Small Cell Lung Cancer',
            eligibility_score: 100.0,
            is_eligible: true,
            matched_criteria_count: 3,
            total_criteria_count: 3,
            disqualifying_reasons: [],
            criteria_results: [
              {
                criterion_id: 'CRIT-EGFR-01',
                category: 'genomics',
                criterion_type: 'inclusion',
                description: 'Documented EGFR activating mutation (Exon 19 del or L858R)',
                is_met: true,
                patient_value: 'Exon 19 del (Detected)',
                required: true,
              },
              {
                criterion_id: 'CRIT-AGE-01',
                category: 'demographics',
                criterion_type: 'inclusion',
                description: 'Adult patient aged 18 years or older',
                is_met: true,
                patient_value: '45 years',
                required: true,
              },
              {
                criterion_id: 'CRIT-METS-01',
                category: 'clinical_history',
                criterion_type: 'exclusion',
                description: 'Active untreated leptomeningeal disease or CNS metastasis',
                is_met: true,
                patient_value: 'Negative / Absent',
                required: true,
              },
            ],
          },
        ],
      }),
      listDeviations: vi.fn().mockResolvedValue({
        total: 1,
        deviations: [
          {
            id: 1,
            deviation_id: 'DEV-2026-0001',
            trial_id: 1,
            reported_by_user_id: 1,
            deviation_category: 'investigational_product_dosing_error',
            severity: 'critical',
            status: 'open',
            description: 'Patient administered 200mg instead of 100mg of investigational kinase inhibitor.',
            occurred_at: '2026-09-02T00:00:00Z',
            discovered_at: '2026-09-02T00:00:00Z',
            impact_on_patient_safety: 'Vitals stable on telemetry.',
            impact_on_data_integrity: 'Cycle 1 PK sample compromised.',
            requires_irb_submission: true,
            created_at: '2026-09-02T00:00:00Z',
            updated_at: '2026-09-02T00:00:00Z',
          },
        ],
      }),
      reportDeviation: vi.fn().mockResolvedValue({
        id: 2,
        deviation_id: 'DEV-2026-0002',
        trial_id: 1,
        reported_by_user_id: 1,
        deviation_category: 'informed_consent_variance',
        severity: 'major',
        status: 'open',
        description: 'Re-consent form delayed by 48 hours.',
        occurred_at: '2026-09-02T00:00:00Z',
        discovered_at: '2026-09-02T00:00:00Z',
        requires_irb_submission: true,
        created_at: '2026-09-02T00:00:00Z',
        updated_at: '2026-09-02T00:00:00Z',
      }),
      createCAPA: vi.fn().mockResolvedValue({
        id: 1,
        capa_id: 'CAPA-2026-0001',
        deviation_id: 1,
        root_cause_category: 'staff_training_gap',
        root_cause_analysis: 'Staff unfamiliar with dosing adjustment schedule.',
        corrective_action: 'Telemetry observation completed.',
        preventive_action: 'Staff retrained on dosing protocols.',
        assigned_owner_user_id: 1,
        target_resolution_date: '2026-09-30',
        status: 'in_progress',
        created_at: '2026-09-02T00:00:00Z',
        updated_at: '2026-09-02T00:00:00Z',
      }),
      submitIRB: vi.fn().mockResolvedValue({
        id: 1,
        notification_id: 'IRB-NOTIF-2026-0001',
        deviation_id: 1,
        irb_committee_name: 'Western Institutional Review Board (WIRB)',
        submission_type: 'prompt_safety_report_ind',
        document_content_json: { filing: 'ok' },
        submitted_by_user_id: 1,
        submission_timestamp: '2026-09-02T00:00:00Z',
        acknowledgement_reference: 'ACK-WIRB-998811',
        created_at: '2026-09-02T00:00:00Z',
      }),
      listSites: vi.fn().mockResolvedValue({
        total: 2,
        sites: [
          {
            id: 1,
            site_id: 'SITE-METRO-MAIN',
            trial_id: 1,
            facility_id: 'FAC-METRO-MAIN',
            site_name: 'MetroHealth Cancer Center - Main Campus',
            target_accrual: 35,
            current_enrolled: 18,
            site_status: 'active',
            irb_approval_number: 'IRB-MH-2026-081',
            created_at: '2026-09-02T00:00:00Z',
            updated_at: '2026-09-02T00:00:00Z',
          },
          {
            id: 2,
            site_id: 'SITE-METRO-WEST',
            trial_id: 1,
            facility_id: 'FAC-METRO-WEST',
            site_name: 'MetroHealth West Pavilion Oncology Clinic',
            target_accrual: 25,
            current_enrolled: 12,
            site_status: 'active',
            irb_approval_number: 'IRB-MH-2026-082',
            created_at: '2026-09-02T00:00:00Z',
            updated_at: '2026-09-02T00:00:00Z',
          },
        ],
      }),
      getTrialSummary: vi.fn().mockResolvedValue({
        trial_id: 1,
        trial_title: 'Phase II Targeted EGFR/MET Bispecific Monoclonal Antibody in Advanced NSCLC',
        total_target_accrual: 60,
        total_enrolled: 30,
        overall_accrual_rate: 50.0,
        active_sites_count: 2,
        total_deviations_count: 1,
        open_capas_count: 1,
        sites_metrics: [],
      }),
    },
  };
});

vi.mock('../context/PatientContext', () => ({
  usePatient: () => ({
    selectedPatient: {
      id: 1,
      patient_id: 'PAT-00101',
      first_name: 'Victor',
      last_name: 'Stone',
      date_of_birth: '1985-04-12',
      gender: 'Male',
      is_active: true,
      created_at: '2026-08-30T00:00:00Z',
    },
    patients: [],
    selectPatient: vi.fn(),
    selectPatientById: vi.fn(),
    refreshPatients: vi.fn(),
    isLoading: false,
    error: null,
  }),
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      name: 'Dr. Trial Coordinator',
      email: 'doctor@hospital.org',
      role: 'doctor',
      is_active: true,
      created_at: '2026-08-30T00:00:00Z',
      updated_at: '2026-08-30T00:00:00Z',
    },
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    token: 'mock-token',
  }),
}));

describe('TrialsGovernanceWorkspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders patient prescreening results with eligibility score and criteria matrix', async () => {
    render(<TrialsGovernanceWorkspace />);

    expect(
      screen.getByText(/Clinical Trials Governance, Precision Auto-Enrollment & Regulatory Auditing/i)
    ).toBeInTheDocument();

    await waitFor(() => {
      const titles = screen.getAllByText(/Phase II Targeted EGFR\/MET/i);
      expect(titles.length).toBeGreaterThanOrEqual(1);
      const scores = screen.getAllByText(/100%/i);
      expect(scores.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Documented EGFR activating mutation/i)).toBeInTheDocument();
    });
  });

  it('switches to Protocol Deviations tab and inspects deviation details', async () => {
    render(<TrialsGovernanceWorkspace />);

    const deviationsTab = screen.getByRole('button', { name: /Protocol Deviations/i });
    fireEvent.click(deviationsTab);

    await waitFor(() => {
      const devIds = screen.getAllByText(/DEV-2026-0001/i);
      expect(devIds.length).toBeGreaterThanOrEqual(1);
      const devCats = screen.getAllByText(/INVESTIGATIONAL PRODUCT DOSING ERROR/i);
      expect(devCats.length).toBeGreaterThanOrEqual(1);
      const descriptions = screen.getAllByText(/Patient administered 200mg instead of 100mg/i);
      expect(descriptions.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('switches to Multi-Center Network Accrual tab and verifies sites', async () => {
    render(<TrialsGovernanceWorkspace />);

    const networkTab = screen.getByRole('button', { name: /Multi-Center Network Accrual/i });
    fireEvent.click(networkTab);

    await waitFor(() => {
      expect(screen.getByText(/MetroHealth Cancer Center - Main Campus/i)).toBeInTheDocument();
      expect(screen.getByText(/MetroHealth West Pavilion Oncology Clinic/i)).toBeInTheDocument();
      expect(screen.getByText(/60 Subjects/i)).toBeInTheDocument();
    });
  });
});
