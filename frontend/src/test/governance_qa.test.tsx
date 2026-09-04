import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { RegionalInteroperabilityWorkspace } from '../components/interop/RegionalInteroperabilityWorkspace';
import { QualityMeasuresWorkspace } from '../components/quality/QualityMeasuresWorkspace';
import { SystemDiagnosticsWorkspace } from '../components/operations/SystemDiagnosticsWorkspace';
import { empiApi, pathwaysApi, ccdaApi, patientsApi, qualityApi, systemApi, fhirApi } from '../api/client';

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>();
  return {
    ...actual,
    patientsApi: {
      list: vi.fn().mockResolvedValue([
        {
          patient_id: 'PAT-20260903-E4EB',
          first_name: 'Harish',
          last_name: 'Sonwale',
          date_of_birth: '2004-08-04',
          gender: 'male',
          facility_id: 'FAC-001',
        },
      ]),
    },
    empiApi: {
      findCandidateMatches: vi.fn().mockResolvedValue({
        query_patient_id: 'PAT-20260903-E4EB',
        total_candidates: 0,
        candidates: [],
      }),
      // Mock backend returning object envelope { total, items } which caused reviews.map is not a function
      listReviews: vi.fn().mockResolvedValue({
        total: 1,
        items: [
          {
            id: 1,
            review_id: 'REV-001',
            patient_id_a: 'PAT-20260903-E4EB',
            patient_id_b: 'PAT-20260903-9999',
            facility_id_a: 'FAC-001',
            facility_id_b: 'FAC-002',
            match_score: 0.78,
            feature_breakdown: { name: 0.8 },
            status: 'pending_review',
            created_at: '2026-09-04T10:00:00Z',
            updated_at: '2026-09-04T10:00:00Z',
          },
        ],
      }),
      linkPatient: vi.fn().mockResolvedValue({ enterprise_id: 'EUID-001', patient_id: 'PAT-20260903-9999' }),
      unlinkPatient: vi.fn().mockResolvedValue({ success: true, message: 'Unlinked' }),
      mergeIdentities: vi.fn().mockResolvedValue({ merge_id: 'MRG-001', message: 'Merged' }),
      resolveReview: vi.fn().mockResolvedValue({ success: true, message: 'Resolved' }),
    },
    pathwaysApi: {
      listPathways: vi.fn().mockResolvedValue({ total: 0, items: [], pathways: [] }),
      getPatientEnrollments: vi.fn().mockResolvedValue([]),
    },
    ccdaApi: {
      listDocuments: vi.fn().mockResolvedValue({ total: 0, items: [], documents: [] }),
    },
    qualityApi: {
      listMeasures: vi.fn().mockResolvedValue({ total: 0, items: [] }),
      getPatientResults: vi.fn().mockResolvedValue({ total: 0, items: [] }),
      listGaps: vi.fn().mockResolvedValue({ total: 0, items: [] }),
      listReports: vi.fn().mockResolvedValue({ total: 0, items: [] }),
      evaluatePatient: vi.fn().mockRejectedValue({
        detail: [{ loc: ['body', 'patient_id'], msg: 'Clinical data required for evaluation' }],
      }),
    },
    systemApi: {
      getLiveness: vi.fn().mockResolvedValue({ status: 'healthy', timestamp: '2026-09-04T12:00:00Z' }),
      getReadiness: vi.fn().mockResolvedValue({
        status: 'ready',
        components: { task_worker: { status: 'Ready', provider: 'celery' } },
      }),
      // Test missing metrics.tasks object to ensure no TypeError: reading queued
      getMetrics: vi.fn().mockResolvedValue({
        http: { requests_by_status: { '200': 15 }, avg_duration_ms: 12.5, uptime_seconds: 3600 },
        tasks: undefined,
      }),
      getPrometheusMetricsText: vi.fn().mockResolvedValue('# Prometheus metrics mock'),
    },
    fhirApi: {
      getCapabilityStatement: vi.fn().mockResolvedValue({
        resourceType: 'CapabilityStatement',
        status: 'active',
        fhirVersion: '4.0.1',
        rest: [{ resource: [{ type: 'Patient', interaction: [{ code: 'read' }, { code: 'search-type' }] }] }],
      }),
    },
  };
});

describe('Governance & Infrastructure QA Regression Tests', () => {
  it('RegionalInteroperabilityWorkspace renders EMPI reviews queue from envelope without throwing reviews.map is not a function', async () => {
    render(<RegionalInteroperabilityWorkspace />);

    // Wait for the review item to render
    await waitFor(() => {
      expect(screen.getByText(/REV-001/i)).toBeInTheDocument();
    });
    expect(screen.getAllByText(/PAT-20260903-E4EB/i).length).toBeGreaterThan(0);
  });

  it('QualityMeasuresWorkspace renders patient dropdown with Indian demo patient and handles error without [object Object]', async () => {
    render(<QualityMeasuresWorkspace />);

    // Patient dropdown should render patient Harish Sonwale
    await waitFor(() => {
      expect(screen.getByText(/Harish Sonwale/i)).toBeInTheDocument();
    });

    // Verify [object Object] is nowhere in document body
    expect(document.body.innerHTML).not.toContain('[object Object]');
  });

  it('SystemDiagnosticsWorkspace renders safely when metrics.tasks is undefined without throwing reading queued', async () => {
    render(<SystemDiagnosticsWorkspace />);

    await waitFor(() => {
      expect(screen.getByTestId('system-diagnostics-workspace')).toBeInTheDocument();
    });
    expect(screen.getByText(/0 queued, 0 running/i)).toBeInTheDocument();
  });
});
