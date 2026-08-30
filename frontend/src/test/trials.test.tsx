import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { TrialsPrecisionWorkspace } from '../components/trials/TrialsPrecisionWorkspace';
import { trialsApi, patientsApi } from '../api/client';

vi.mock('../api/client', () => ({
  patientsApi: {
    list: vi.fn().mockResolvedValue([
      {
        id: 1,
        patient_id: 'PAT-PREC-001',
        first_name: 'Eleanor',
        last_name: 'Vance',
        gender: 'female',
        date_of_birth: '1968-05-20',
        status: 'active',
        is_active: true,
      },
    ]),
  },

  trialsApi: {
    listTrials: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          trial_id: 'TRIAL-LUNG-001',
          nct_number: 'NCT05123456',
          title: 'Phase 3 Trial of 3rd-Gen EGFR TKI in Advanced NSCLC',
          sponsor: 'Global Oncology Research Group',
          phase: 'phase_3',
          status: 'recruiting',
          disease_condition: 'Non-Small Cell Lung Cancer',
          intervention_name: 'Osimertinib Novel Formulation',
          intervention_type: 'targeted_therapy',
          target_gender: 'all',
          summary: 'Randomized phase 3 investigation for EGFR-mutant advanced NSCLC.',
          is_active: true,
          version: '1.0.0',
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    listPatientTrialMatches: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          match_id: 'TMATCH-TRIAL-LUNG-001-PAT-PREC-001',
          trial_id: 1,
          trial_identifier: 'TRIAL-LUNG-001',
          trial_title: 'Phase 3 Trial of 3rd-Gen EGFR TKI in Advanced NSCLC',
          trial_phase: 'phase_3',
          trial_sponsor: 'Global Oncology Research Group',
          disease_condition: 'Non-Small Cell Lung Cancer',
          intervention_name: 'Osimertinib Novel Formulation',
          patient_id: 1,
          patient_identifier: 'PAT-PREC-001',
          patient_name: 'Eleanor Vance',
          match_status: 'MATCHED',
          match_score: 100.0,
          matched_criteria_json: [
            {
              criterion_id: 'CRIT-1',
              category: 'diagnosis',
              criterion_type: 'inclusion',
              field_name: 'diagnosis',
              description: 'Primary Condition: Non-Small Cell Lung Cancer',
              status: 'PASS',
              evidence: 'Patient confirmed diagnosis: Metastatic NSCLC',
              reason: 'Condition matches expected Non-Small Cell Lung Cancer',
            },
            {
              criterion_id: 'CRIT-2',
              category: 'biomarker',
              criterion_type: 'inclusion',
              field_name: 'EGFR',
              description: 'Documented EGFR L858R mutation',
              status: 'PASS',
              evidence: 'Detected EGFR L858R',
              reason: 'Biomarker mutation confirmed',
            },
          ],
          failed_criteria_json: [],
          unknown_criteria_json: [],
          overall_explanation: 'Patient is FULLY MATCHED for trial. Satisfies 100.0% of evaluated eligibility criteria.',
          provenance_hash: 'a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0',
          algorithm_version: '2026.1-deterministic',
          clinician_review_status: 'pending_review',
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    listPatientGenomicProfiles: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          profile_id: 'GEN-PROF-001',
          patient_id: 1,
          patient_identifier: 'PAT-PREC-001',
          patient_name: 'Eleanor Vance',
          specimen_type: 'tumor_tissue_biopsy',
          test_name: 'Comprehensive Solid Tumor 500-Gene Panel',
          sequencing_platform: 'Illumina NovaSeq 6000',
          performing_lab: 'MediGen Precision Genomics Core',
          tumor_mutation_burden: 14.2,
          microsatellite_instability_status: 'MSI-H',
          overall_interpretation: 'Actionable EGFR L858R mutation with high TMB and MSI-High phenotype.',
          status: 'final',
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
          biomarkers: [
            {
              id: 1,
              observation_id: 'BM-001',
              profile_id: 1,
              patient_id: 1,
              gene_symbol: 'EGFR',
              variant_name: 'L858R',
              alteration_type: 'missense_mutation',
              pathogenicity: 'tier_1_strong_clinical',
              evidence_level: 'FDA_Level_A',
              variant_allele_fraction: 42.1,
              clinical_significance: 'Sensitizing mutation for Osimertinib therapy.',
              detected_at: '2026-08-29T10:00:00Z',
              created_at: '2026-08-29T10:00:00Z',
            },
          ],
        },
      ],
    }),
    listPatientPrecisionEligibility: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          eligibility_id: 'PREC-ELIG-001',
          patient_id: 1,
          patient_identifier: 'PAT-PREC-001',
          patient_name: 'Eleanor Vance',
          gene_symbol: 'EGFR',
          variant_name: 'L858R',
          recommended_intervention: 'Osimertinib (Tagrisso) 80mg Daily',
          drug_class: '3rd-Generation EGFR Tyrosine Kinase Inhibitor',
          indication: 'EGFR Exon 21 (L858R) Substituted Metastatic NSCLC',
          eligibility_status: 'ELIGIBLE',
          evidence_source: 'NCCN Guidelines v2026.1 / FDA Approved / Level 1A',
          supporting_observations_json: ['EGFR L858R detected (VAF 42.1%)'],
          contraindicating_observations_json: [],
          unknown_factors_json: [],
          provenance_hash: '9f8e7d6c5b4a3210987654321fedcba0987654321fedcba0987654321fedcba0',
          clinician_review_status: 'pending_review',
          created_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    batchMatchPatient: vi.fn().mockResolvedValue({
      patient_id: 'PAT-PREC-001',
      total_evaluated_trials: 1,
      matched_trials_count: 1,
      potential_trials_count: 0,
      ineligible_trials_count: 0,
      matches: [],
    }),
    evaluatePrecisionEligibility: vi.fn().mockResolvedValue({
      total: 1,
      items: [],
    }),
    reviewTrialMatch: vi.fn().mockResolvedValue({
      match_id: 'TMATCH-TRIAL-LUNG-001-PAT-PREC-001',
      trial_identifier: 'TRIAL-LUNG-001',
      trial_title: 'Phase 3 Trial of 3rd-Gen EGFR TKI in Advanced NSCLC',
      trial_phase: 'phase_3',
      match_status: 'MATCHED',
      match_score: 100.0,
      matched_criteria_json: [],
      failed_criteria_json: [],
      unknown_criteria_json: [],
      overall_explanation: 'Clinician confirmed eligibility.',
      provenance_hash: 'hash-123',
      algorithm_version: '2026.1',
      clinician_review_status: 'confirmed_eligible',
      review_notes: 'Eligible for screening trial.',
      reviewed_by_name: 'Dr. Oncologist',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    }),
  },
}));

describe('Phase 9.0.16: TrialsPrecisionWorkspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders workspace banner, active patient context, and sub-navigation tabs', async () => {
    render(<TrialsPrecisionWorkspace initialPatientId="PAT-PREC-001" />);

    expect(screen.getByTestId('trials-precision-workspace')).toBeInTheDocument();
    expect(screen.getByText(/Clinical Trials Matching & Biomarker Precision Oncology/i)).toBeInTheDocument();
    expect(screen.getByText(/Clinical Decision Support Disclaimer:/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId('tab-matching')).toBeInTheDocument();
      expect(screen.getByTestId('tab-genomics')).toBeInTheDocument();
      expect(screen.getByTestId('tab-precision')).toBeInTheDocument();
      expect(screen.getByTestId('tab-registry')).toBeInTheDocument();
    });
  });

  it('renders clinical trial match scorecard with criteria breakdown and score', async () => {
    render(<TrialsPrecisionWorkspace initialPatientId="PAT-PREC-001" />);

    await waitFor(() => {
      expect(screen.getByTestId('match-card-TRIAL-LUNG-001')).toBeInTheDocument();
      expect(screen.getByText(/Phase 3 Trial of 3rd-Gen EGFR TKI in Advanced NSCLC/i)).toBeInTheDocument();
      expect(screen.getByText(/MATCHED \(100%\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Documented EGFR L858R mutation/i)).toBeInTheDocument();
    });
  });

  it('opens explainability modal and displays cryptographic SHA-256 audit provenance hash', async () => {
    render(<TrialsPrecisionWorkspace initialPatientId="PAT-PREC-001" />);

    await waitFor(() => {
      expect(screen.getByTestId('btn-evidence-TRIAL-LUNG-001')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('btn-evidence-TRIAL-LUNG-001'));

    await waitFor(() => {
      expect(screen.getByTestId('evidence-modal')).toBeInTheDocument();
      expect(screen.getByText(/Audit Trail & Criterion Explainability/i)).toBeInTheDocument();
      expect(screen.getByText(/a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0/i)).toBeInTheDocument();
    });
  });

  it('opens clinician trial match review modal and records sign-off determination', async () => {
    render(<TrialsPrecisionWorkspace initialPatientId="PAT-PREC-001" />);

    await waitFor(() => {
      expect(screen.getByTestId('btn-review-TRIAL-LUNG-001')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('btn-review-TRIAL-LUNG-001'));

    await waitFor(() => {
      expect(screen.getByTestId('review-modal')).toBeInTheDocument();
      expect(screen.getByTestId('select-review-status')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId('select-review-status'), {
      target: { value: 'confirmed_eligible' },
    });
    fireEvent.change(screen.getByTestId('textarea-review-notes'), {
      target: { value: 'Verified Level 1A criteria. Approved for screening enrollment.' },
    });

    fireEvent.click(screen.getByTestId('btn-submit-review'));

    await waitFor(() => {
      expect(trialsApi.reviewTrialMatch).toHaveBeenCalledWith(
        'TMATCH-TRIAL-LUNG-001-PAT-PREC-001',
        expect.objectContaining({
          clinician_review_status: 'confirmed_eligible',
          review_notes: 'Verified Level 1A criteria. Approved for screening enrollment.',
        })
      );
    });
  });

  it('navigates to Genomic Profiles tab and displays NGS panels and biomarkers', async () => {
    render(<TrialsPrecisionWorkspace initialPatientId="PAT-PREC-001" />);

    await waitFor(() => {
      expect(screen.getByTestId('tab-genomics')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('tab-genomics'));

    await waitFor(() => {
      expect(screen.getByTestId('genomics-tab')).toBeInTheDocument();
      expect(screen.getByText(/Comprehensive Solid Tumor 500-Gene Panel/i)).toBeInTheDocument();
      expect(screen.getByText(/TMB: 14.2 mut\/Mb/i)).toBeInTheDocument();
      expect(screen.getByText(/MSI: MSI-H/i)).toBeInTheDocument();
      expect(screen.getByText('L858R')).toBeInTheDocument();
    });
  });

  it('navigates to Precision Oncology tab and renders targeted therapy recommendations', async () => {
    render(<TrialsPrecisionWorkspace initialPatientId="PAT-PREC-001" />);

    await waitFor(() => {
      expect(screen.getByTestId('tab-precision')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('tab-precision'));

    await waitFor(() => {
      expect(screen.getByTestId('precision-tab')).toBeInTheDocument();
      expect(screen.getByText(/Osimertinib \(Tagrisso\) 80mg Daily/i)).toBeInTheDocument();
      expect(screen.getByText(/3rd-Generation EGFR Tyrosine Kinase Inhibitor/i)).toBeInTheDocument();
      expect(screen.getByText(/NCCN Guidelines v2026.1 \/ FDA Approved \/ Level 1A/i)).toBeInTheDocument();
    });
  });
});
