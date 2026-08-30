import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { QualityMeasuresWorkspace } from '../components/quality/QualityMeasuresWorkspace';
import { qualityApi, patientsApi } from '../api/client';

vi.mock('../api/client', () => ({
  patientsApi: {
    list: vi.fn().mockResolvedValue([
      {
        id: 1,
        patient_id: 'PAT-CQM-001',
        first_name: 'Eleanor',
        last_name: 'Vance',
        gender: 'female',
        date_of_birth: '1958-04-12',
        is_active: true,
      },
    ]),
  },


  qualityApi: {
    listMeasures: vi.fn().mockResolvedValue({
      total: 2,
      items: [
        {
          id: 1,
          measure_id: 'CQM-001-DM-HBA1C',
          title: 'Diabetes Glycemic Control (HbA1c < 8.0%)',
          description: 'Percentage of patients 18-75 with diabetes who had HbA1c < 8.0%.',
          domain: 'chronic_disease_management',
          standard_framework: 'HEDIS HBD / CMS MIPS #001',
          steward: 'NCQA',
          version: '2026.1.0',
          target_rate: 0.85,
          initial_population_criteria: 'Patients 18-75 with Type 1 or Type 2 diabetes.',
          denominator_criteria: 'Active diabetic patients.',
          numerator_criteria: 'Latest HbA1c value < 8.0%.',
          is_active: true,
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
        {
          id: 2,
          measure_id: 'CQM-002-HTN-BP',
          title: 'Controlling High Blood Pressure (<140/90 mmHg)',
          description: 'Percentage of patients 18-85 with hypertension whose BP was adequately controlled.',
          domain: 'chronic_disease_management',
          standard_framework: 'HEDIS CBP / CMS MIPS #236',
          steward: 'NCQA',
          version: '2026.1.0',
          target_rate: 0.8,
          initial_population_criteria: 'Patients 18-85 with essential hypertension.',
          denominator_criteria: 'Active hypertensive patients.',
          numerator_criteria: 'Blood pressure < 140/90 mmHg.',
          is_active: true,
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),

    getPatientResults: vi.fn().mockResolvedValue({
      total: 2,
      items: [
        {
          id: 1,
          result_id: 'RES-001',
          measure_id: 1,
          measure_code: 'CQM-001-DM-HBA1C',
          measure_title: 'Diabetes Glycemic Control (HbA1c < 8.0%)',
          is_eligible: true,
          is_denominator_eligible: true,
          is_numerator_compliant: true,
          compliance_status: 'compliant',
          evidence_json: { latest_hba1c_value: 7.2 },
          calculated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),

    evaluatePatient: vi.fn().mockResolvedValue({
      total: 2,
      items: [
        {
          id: 1,
          result_id: 'RES-001',
          measure_id: 1,
          measure_code: 'CQM-001-DM-HBA1C',
          measure_title: 'Diabetes Glycemic Control (HbA1c < 8.0%)',
          is_eligible: true,
          is_denominator_eligible: true,
          is_numerator_compliant: true,
          compliance_status: 'compliant',
          evidence_json: { latest_hba1c_value: 7.2 },
          calculated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),

    listGaps: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          gap_id: 'QMG-20260829-001',
          measure_id: 2,
          measure_code: 'CQM-002-HTN-BP',
          measure_title: 'Controlling High Blood Pressure (<140/90 mmHg)',
          patient_id: 1,
          patient_identifier: 'PAT-CQM-001',
          patient_name: 'Eleanor Vance',
          severity: 'HIGH',
          status: 'open',
          missing_data_summary: 'Latest blood pressure measurement (155/95 mmHg) exceeds target (<140/90 mmHg).',
          recommended_action: 'Titrate antihypertensive regimen or repeat clinical telemetry check.',
          identified_at: '2026-08-29T10:00:00Z',
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),

    createCareTaskForGap: vi.fn().mockResolvedValue({
      id: 1,
      gap_id: 'QMG-20260829-001',
      measure_id: 2,
      measure_code: 'CQM-002-HTN-BP',
      measure_title: 'Controlling High Blood Pressure (<140/90 mmHg)',
      patient_id: 1,
      patient_identifier: 'PAT-CQM-001',
      patient_name: 'Eleanor Vance',
      severity: 'HIGH',
      status: 'in_remediation',
      missing_data_summary: 'Latest blood pressure measurement (155/95 mmHg) exceeds target (<140/90 mmHg).',
      recommended_action: 'Titrate antihypertensive regimen or repeat clinical telemetry check.',
      linked_care_task_id: 10,
      identified_at: '2026-08-29T10:00:00Z',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    }),

    listReports: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          report_id: 'QRP-20260829-001',
          title: 'Q3 2026 Executive Quality Compliance Audit',
          report_scope: 'organization',
          overall_performance_rate: 87.5,
          total_eligible_population: 40,
          total_compliant_population: 35,
          measure_summaries_json: [
            {
              measure_id: 'CQM-001-DM-HBA1C',
              title: 'Diabetes Glycemic Control (HbA1c < 8.0%)',
              domain: 'chronic_disease_management',
              standard_framework: 'HEDIS HBD',
              target_rate: 0.85,
              performance_rate: 0.9,
              eligible_population: 20,
              compliant_population: 18,
              gap_count: 2,
            },
          ],
          audit_metadata_json: {
            provenance_hash: '3f5a89b9e11c7820a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0',
            total_measures_evaluated: 5,
          },
          is_published: true,
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),

    generateReport: vi.fn().mockResolvedValue({
      id: 2,
      report_id: 'QRP-20260829-002',
      title: 'New Synthesized Audit Report',
      report_scope: 'organization',
      overall_performance_rate: 90.0,
      total_eligible_population: 50,
      total_compliant_population: 45,
      measure_summaries_json: [],
      audit_metadata_json: {
        provenance_hash: 'abcdef01234567893f5a89b9e11c7820a1b2c3d4e5f60718293a4b5c6d7e8f90',
      },
      is_published: true,
      created_at: '2026-08-29T11:00:00Z',
      updated_at: '2026-08-29T11:00:00Z',
    }),
  },
}));

describe('QualityMeasuresWorkspace', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders quality workspace with KPI cards and measure scorecard', async () => {
    render(<QualityMeasuresWorkspace />);

    expect(
      screen.getByText('Clinical Quality Measures (CQMs) & Compliance Engine')
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Diabetes Glycemic Control (HbA1c < 8.0%)')).toBeInTheDocument();
      expect(screen.getByText('Controlling High Blood Pressure (<140/90 mmHg)')).toBeInTheDocument();
      expect(screen.getByText('HEDIS HBD / CMS MIPS #001')).toBeInTheDocument();
    });
  });

  it('filters measures by domain', async () => {
    render(<QualityMeasuresWorkspace />);

    await waitFor(() => {
      expect(screen.getByText('Diabetes Glycemic Control (HbA1c < 8.0%)')).toBeInTheDocument();
    });

    const domainSelect = document.querySelector('#quality-domain-filter') as HTMLSelectElement;
    expect(domainSelect).toBeInTheDocument();
    fireEvent.change(domainSelect, { target: { value: 'chronic_disease_management' } });
    await waitFor(() => {
      expect(qualityApi.listMeasures).toHaveBeenCalled();
    });
  });


  it('navigates to gaps feed and creates a care task for remediation', async () => {
    render(<QualityMeasuresWorkspace />);

    const gapsTab = screen.getByRole('button', { name: /Gaps-in-Care Feed/i });
    fireEvent.click(gapsTab);

    await waitFor(() => {
      expect(screen.getByText('HIGH')).toBeInTheDocument();
      expect(screen.getByText('Eleanor Vance (PAT-CQM-001)')).toBeInTheDocument();
      expect(screen.getByText('Create Care Task')).toBeInTheDocument();
    });

    const createBtn = screen.getByText('Create Care Task');
    fireEvent.click(createBtn);

    await waitFor(() => {
      expect(qualityApi.createCareTaskForGap).toHaveBeenCalledWith('QMG-20260829-001');
      expect(screen.getByText(/Care task successfully created/i)).toBeInTheDocument();
    });
  });

  it('renders compliance & audit reports tab with provenance hash', async () => {
    render(<QualityMeasuresWorkspace />);

    const reportsTab = screen.getByRole('button', { name: /Compliance & Audit Reports/i });
    fireEvent.click(reportsTab);

    await waitFor(() => {
      expect(screen.getByText('Q3 2026 Executive Quality Compliance Audit')).toBeInTheDocument();
      expect(screen.getByText('QRP-20260829-001')).toBeInTheDocument();
      expect(screen.getByText(/3f5a89b9e11c7820a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0/i)).toBeInTheDocument();
    });
  });
});
