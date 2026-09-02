import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { CDSPGxOrderSetWorkspace } from '../components/cds/CDSPGxOrderSetWorkspace';
import * as apiClient from '../api/client';
import { PatientProvider } from '../context/PatientContext';
import { AuthProvider } from '../context/AuthContext';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof apiClient>('../api/client');
  return {
    ...actual,
    cdsPgxApi: {
      listOrderSets: vi.fn().mockResolvedValue({
        total: 1,
        order_sets: [
          {
            id: 1,
            order_set_id: 'ORDSET-SEPSIS-3H',
            code: 'SEPSIS_BUNDLE',
            title: 'Sepsis 3-Hour Resuscitation Bundle',
            description: 'Surviving Sepsis Campaign evidence bundle',
            category: 'critical_care',
            target_icd10: 'A41.9',
            version: '2.1.0',
            is_active: true,
            created_at: '2026-09-02T00:00:00Z',
            updated_at: '2026-09-02T00:00:00Z',
            items: [
              {
                id: 101,
                item_id: 'ITEM-SEP-01',
                order_set_id: 'ORDSET-SEPSIS-3H',
                item_type: 'laboratory',
                code: 'LAB-LACTATE',
                name: 'Serum Lactate Level STAT',
                default_frequency: 'STAT',
                is_required: true,
                sequence_order: 1,
                created_at: '2026-09-02T00:00:00Z',
              },
              {
                id: 102,
                item_id: 'ITEM-SEP-02',
                order_set_id: 'ORDSET-SEPSIS-3H',
                item_type: 'medication',
                code: 'MED-VANCO',
                name: 'Vancomycin IV 15mg/kg STAT',
                default_dosage: '15mg/kg',
                default_route: 'IV',
                default_frequency: 'STAT',
                is_required: true,
                sequence_order: 2,
                created_at: '2026-09-02T00:00:00Z',
              },
            ],
          },
        ],
      }),
      listRules: vi.fn().mockResolvedValue({
        total: 2,
        rules: [
          {
            id: 1,
            rule_id: 'PGX-CYP2D6-CODEINE-PM',
            cpic_level: 'A',
            gene_symbol: 'CYP2D6',
            phenotype: 'Poor Metabolizer',
            drug_code: 'RXNORM-2670',
            drug_name: 'Codeine',
            risk_severity: 'critical',
            clinical_implication: 'Greatly reduced morphine formation; lack of analgesia.',
            recommendation_text: 'Avoid codeine. Use alternative analgesics such as morphine or non-opioids.',
            alternative_drugs: ['Morphine', 'Acetaminophen', 'Hydromorphone'],
            is_active: true,
            created_at: '2026-09-02T00:00:00Z',
            updated_at: '2026-09-02T00:00:00Z',
          },
          {
            id: 2,
            rule_id: 'PGX-CYP2C19-CLOPIDOGREL-IM',
            cpic_level: 'A',
            gene_symbol: 'CYP2C19',
            phenotype: 'Intermediate Metabolizer',
            drug_code: 'RXNORM-32968',
            drug_name: 'Clopidogrel',
            risk_severity: 'high_risk',
            clinical_implication: 'Reduced active metabolite exposure and antiplatelet effect.',
            recommendation_text: 'Avoid clopidogrel at standard dose. Consider prasugrel or ticagrelor.',
            alternative_drugs: ['Ticagrelor', 'Prasugrel'],
            is_active: true,
            created_at: '2026-09-02T00:00:00Z',
            updated_at: '2026-09-02T00:00:00Z',
          },
        ],
      }),
      executeOrderSet: vi.fn().mockResolvedValue({
        execution_id: 'EXEC-TEST-001',
        order_set_id: 'ORDSET-SEPSIS-3H',
        patient_id: 'PAT-00101',
        facility_id: 'FAC-001',
        status: 'executed',
        executed_items_count: 2,
        generated_order_ids: ['ORD-001', 'ORD-002'],
        message: 'Order set executed successfully',
        created_at: '2026-09-02T00:00:00Z',
      }),
      evaluateCDS: vi.fn().mockResolvedValue({
        patient_id: 'PAT-00101',
        trigger_event: 'order_select',
        has_alerts: true,
        highest_severity: 'critical',
        patient_genotype_summary: {
          CYP2C19: 'Intermediate Metabolizer (*1/*2)',
        },
        cards: [
          {
            card_id: 'CARD-PGX-CYP2C19-CLOPIDOGREL',
            summary: 'CYP2C19 Intermediate Metabolizer: Reduced Antiplatelet Efficacy with Clopidogrel',
            detail: 'Patient has reduced active metabolite exposure and increased cardiovascular ischemic risk.',
            indicator: 'critical',
            rule_type: 'pgx_interaction',
            gene_symbol: 'CYP2C19',
            cpic_level: 'A',
            phenotype: 'Intermediate Metabolizer (*1/*2)',
            current_drug: 'Clopidogrel',
            alternative_drugs: ['Ticagrelor', 'Prasugrel'],
            links: [],
          },
        ],
        evaluated_at: '2026-09-02T00:00:00Z',
      }),
      recordOverride: vi.fn().mockResolvedValue({
        audit_id: 'CDS-OVR-TEST-001',
        patient_id: 'PAT-00101',
        is_overridden: true,
        override_reason: 'Patient previously tolerated clopidogrel without adverse events.',
        message: 'Clinician CDS override recorded with audit integrity trail.',
        created_at: '2026-09-02T00:00:00Z',
      }),
      listAudits: vi.fn().mockResolvedValue({
        total: 1,
        audits: [
          {
            id: 1,
            audit_id: 'CDS-OVR-TEST-001',
            patient_id: 'PAT-00101',
            rule_type: 'pgx_interaction',
            trigger_event: 'order_select',
            severity: 'critical',
            card_summary: 'CYP2C19 Intermediate Metabolizer: Reduced Antiplatelet Efficacy',
            card_detail: 'Reduced active metabolite exposure.',
            is_overridden: true,
            override_reason: 'Patient previously tolerated clopidogrel without adverse events.',
            clinician_id: 1,
            created_at: '2026-09-02T00:00:00Z',
          },
        ],
      }),
    },
  };
});

vi.mock('../context/PatientContext', () => ({
  usePatient: () => ({
    selectedPatient: {
      id: 1,
      patient_id: 'PAT-00101',
      first_name: 'Eleanor',
      last_name: 'Vance',
      date_of_birth: '1980-05-12',
      gender: 'Female',
      is_active: true,
      created_at: '2026-08-30T00:00:00Z',
    },
    patients: [
      {
        id: 1,
        patient_id: 'PAT-00101',
        first_name: 'Eleanor',
        last_name: 'Vance',
        date_of_birth: '1980-05-12',
        gender: 'Female',
        is_active: true,
        created_at: '2026-08-30T00:00:00Z',
      },
    ],
    selectPatient: vi.fn(),
    selectPatientById: vi.fn(),
    refreshPatients: vi.fn(),
    isLoading: false,
    error: null,
  }),
  PatientProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      name: 'Dr. Gregory House',
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
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe('CDSPGxOrderSetWorkspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = () =>
    render(<CDSPGxOrderSetWorkspace />);

  it('renders workspace title and order sets checklist', async () => {
    renderComponent();

    expect(
      screen.getByText(/Clinical Decision Support & Pharmacogenomics/i)
    ).toBeInTheDocument();

    await waitFor(() => {
      const titles = screen.getAllByText(/Sepsis 3-Hour Resuscitation Bundle/i);
      expect(titles.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Serum Lactate Level STAT/i)).toBeInTheDocument();
      expect(screen.getByText(/Vancomycin IV 15mg\/kg STAT/i)).toBeInTheDocument();
    });
  });

  it('switches to Real-Time CDS tab and evaluates proposed drug interaction', async () => {
    renderComponent();

    const realtimeTab = screen.getByRole('button', { name: /Real-Time CDS & PGx Check/i });
    fireEvent.click(realtimeTab);

    expect(screen.getByText(/Pre-Flight Medication Order CDS & PGx Evaluation/i)).toBeInTheDocument();

    const evalBtn = screen.getByRole('button', { name: /Evaluate CDS & PGx/i });
    fireEvent.click(evalBtn);

    await waitFor(() => {
      expect(screen.getByText(/CYP2C19 Intermediate Metabolizer/i)).toBeInTheDocument();
      expect(screen.getByText(/Ticagrelor/i)).toBeInTheDocument();
      expect(screen.getByText(/Prasugrel/i)).toBeInTheDocument();
    });
  });

  it('switches to CPIC Knowledge Base tab and displays CPIC guidelines', async () => {
    renderComponent();

    const cpicTab = screen.getByRole('button', { name: /CPIC Knowledge Base/i });
    fireEvent.click(cpicTab);

    await waitFor(() => {
      expect(screen.getByText(/CYP2D6 • Poor Metabolizer/i)).toBeInTheDocument();
      expect(screen.getByText(/CYP2C19 • Intermediate Metabolizer/i)).toBeInTheDocument();
    });
  });
});
