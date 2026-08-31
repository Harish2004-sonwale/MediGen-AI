import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SmartFhirEhrWorkspace } from '../components/interop/SmartFhirEhrWorkspace';
import * as apiClient from '../api/client';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof apiClient>('../api/client');
  return {
    ...actual,
    smartApi: {
      getSmartConfig: vi.fn().mockResolvedValue({
        authorization_endpoint: 'https://api.medigen.ai/api/v1/smart/authorize',
        token_endpoint: 'https://api.medigen.ai/api/v1/smart/token',
        jwks_uri: 'https://api.medigen.ai/.well-known/jwks.json',
        grant_types_supported: ['authorization_code'],
        code_challenge_methods_supported: ['S256'],
        scopes_supported: ['launch/patient', 'patient/Patient.read'],
        response_types_supported: ['code'],
        capabilities: ['launch-ehr', 'client-public'],
      }),
      getJwks: vi.fn().mockResolvedValue({ keys: [] }),
      authorize: vi.fn().mockResolvedValue({ code: 'auth-code-123', state: 'state-123' }),
      exchangeToken: vi.fn().mockResolvedValue({ access_token: 'smart-jwt-token-123', token_type: 'Bearer', expires_in: 3600 }),
      introspectToken: vi.fn().mockResolvedValue({ active: true }),
    },
    cdsApi: {
      discoverServices: vi.fn().mockResolvedValue({
        services: [
          {
            hook: 'patient-view',
            name: 'medigen-patient-risk-advisor',
            id: 'medigen-patient-risk-advisor',
            title: 'MediGen Patient Risk & Care Gap Advisor',
            description: 'Evaluates patient clinical timeline',
          },
        ],
      }),
      invokePatientView: vi.fn().mockResolvedValue({
        cards: [
          {
            summary: 'Active Vital Alert: HYPOXIA (CRITICAL)',
            detail: 'Patient SpO2 dropped to 84% on room air.',
            indicator: 'critical',
            source: { label: 'MediGen AI Clinical Decision Support' },
            suggestions: [
              {
                label: 'Initiate supplemental oxygen',
                actions: [{ type: 'create', description: 'Oxygen order' }],
              },
            ],
          },
        ],
      }),
      invokeOrderSelect: vi.fn().mockResolvedValue({ cards: [] }),
    },
    terminologyApi: {
      normalizeConcept: vi.fn().mockResolvedValue({
        query: 'Serum Potassium',
        normalized: {
          system: 'LOINC',
          code: '6298-4',
          display: 'Potassium [Moles/volume] in Blood',
          confidence: 0.98,
          match_type: 'EXACT',
          source: 'LOCAL_DICTIONARY',
        },
        alternatives: [],
        semantic_distance: 0.02,
        status: 'SUCCESS',
      }),
      crosswalkCode: vi.fn(),
    },
  };
});

describe('SmartFhirEhrWorkspace', () => {
  it('renders workspace with title and tabs', async () => {
    render(<SmartFhirEhrWorkspace selectedPatientId="PAT-001" />);
    expect(screen.getByText(/Enterprise EHR Integration & SMART on FHIR 2.0 Hub/i)).toBeInTheDocument();
    expect(screen.getAllByText(/CDS Hooks 2.0/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/SMART Launch/i)).toBeInTheDocument();
    expect(screen.getByText(/Terminology Normalizer/i)).toBeInTheDocument();
  });

  it('invokes patient-view CDS Hook and displays critical card', async () => {
    render(<SmartFhirEhrWorkspace selectedPatientId="PAT-001" />);

    const simBtn = await screen.findByText(/Simulate 'patient-view' Hook/i);
    await waitFor(() => expect(simBtn).not.toBeDisabled());
    fireEvent.click(simBtn);

    await waitFor(() => {
      expect(screen.getByTestId('cds-card-summary')).toHaveTextContent(/Active Vital Alert: HYPOXIA/i);
      expect(screen.getByText(/Patient SpO2 dropped to 84%/i)).toBeInTheDocument();
      expect(screen.getByText(/Initiate supplemental oxygen/i)).toBeInTheDocument();
    });
  });

  it('normalizes clinical concept to standard LOINC code', async () => {
    render(<SmartFhirEhrWorkspace selectedPatientId="PAT-001" />);

    // Switch to terminology tab
    const termTab = screen.getByText(/Terminology Normalizer/i);
    fireEvent.click(termTab);

    const normBtn = await screen.findByText(/Normalize Concept/i);
    await waitFor(() => expect(normBtn).not.toBeDisabled());
    fireEvent.click(normBtn);

    await waitFor(() => {
      expect(screen.getByTestId('norm-code')).toHaveTextContent('6298-4');
      expect(screen.getByTestId('norm-display')).toHaveTextContent(/Potassium/i);
    });
  });
});
