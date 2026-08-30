import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { SystemDiagnosticsWorkspace } from '../components/operations/SystemDiagnosticsWorkspace';
import * as apiClient from '../api/client';

// Mock systemApi and fhirApi
vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof apiClient>('../api/client');
  return {
    ...actual,
    systemApi: {
      getLiveness: vi.fn(),
      getReadiness: vi.fn(),
      getMetrics: vi.fn(),
      getPrometheusMetricsText: vi.fn(),
    },
    fhirApi: {
      getCapabilityStatement: vi.fn(),
    },
  };
});

describe('SystemDiagnosticsWorkspace Component', () => {
  const mockLiveness = {
    status: 'alive',
    service: 'MediGen AI - Clinical Intelligence Platform',
    version: '0.1.0',
    environment: 'production',
    correlation_id: 'corr-live-123',
  };

  const mockReadiness = {
    status: 'ready',
    ready: true,
    service: 'MediGen AI',
    version: '0.1.0',
    components: {
      database: { status: 'connected', healthy: true },
      cache: { status: 'connected', healthy: true, provider: 'RedisCache' },
      vector_store: { status: 'available', healthy: true, provider: 'text-embedding-3-small', collection: 'medical_documents' },
      task_worker: { status: 'ready', healthy: true, provider: 'celery', metrics: { queued: 0, running: 1 } },
      drug_knowledge: { provider: 'mock', healthy: true },
    },
    correlation_id: 'corr-ready-123',
  };

  const mockMetrics = {
    service: 'MediGen AI',
    version: '0.1.0',
    environment: 'production',
    http: {
      total_requests: 1250,
      uptime_seconds: 7200,
      requests_by_status: { '200': 1200, '404': 45, '500': 5 },
      avg_duration_ms: 42.5,
      recent_latencies_ms: [40.1, 45.2, 42.0],
    },
    tasks: {
      queued: 2,
      running: 1,
      completed: 140,
      failed: 3,
    },
    correlation_id: 'corr-metrics-123',
  };

  const mockFhirCapability = {
    resourceType: 'CapabilityStatement' as const,
    id: 'medigen-ai-capability-statement',
    status: 'active',
    date: '2026-08-30T00:00:00Z',
    publisher: 'MediGen AI Clinical Intelligence Platform',
    kind: 'instance',
    fhirVersion: '4.0.1',
    format: ['application/fhir+json', 'application/json'],
    rest: [
      {
        mode: 'server',
        documentation: 'MediGen AI FHIR R4 Interoperability Gateway',
        resource: [
          { type: 'Patient', interaction: [{ code: 'read' }, { code: 'search-type' }] },
          { type: 'Encounter', interaction: [{ code: 'read' }] },
          { type: 'Condition', interaction: [{ code: 'read' }] },
          { type: 'Consent', interaction: [{ code: 'read' }] },
          { type: 'AuditEvent', interaction: [{ code: 'read' }] },
        ],
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.systemApi.getLiveness).mockResolvedValue(mockLiveness);
    vi.mocked(apiClient.systemApi.getReadiness).mockResolvedValue(mockReadiness);
    vi.mocked(apiClient.systemApi.getMetrics).mockResolvedValue(mockMetrics);
    vi.mocked(apiClient.fhirApi.getCapabilityStatement).mockResolvedValue(mockFhirCapability);
    vi.mocked(apiClient.systemApi.getPrometheusMetricsText).mockResolvedValue(
      '# HELP medigen_http_requests_total\nmedigen_http_requests_total{status_code="200"} 1200\nmedigen_uptime_seconds 7200'
    );
  });

  it('renders executive infrastructure diagnostics header and KPI badges', async () => {
    render(<SystemDiagnosticsWorkspace />);

    expect(screen.getByText('Enterprise Infrastructure & Diagnostics')).toBeInTheDocument();
    expect(screen.getByText('Production Hardened')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('ALIVE')).toBeInTheDocument();
      expect(screen.getByText('READY')).toBeInTheDocument();
      expect(screen.getByText('1250 reqs')).toBeInTheDocument();
      expect(screen.getByText('4.0.1')).toBeInTheDocument();
    });
  });

  it('renders component readiness matrix cards', async () => {
    render(<SystemDiagnosticsWorkspace />);

    await waitFor(() => {
      expect(screen.getByText('PostgreSQL Engine')).toBeInTheDocument();
      expect(screen.getByText('Redis Distributed Cache')).toBeInTheDocument();
      expect(screen.getByText('Clinical Vector Store')).toBeInTheDocument();
      expect(screen.getByText('Background Task Workers')).toBeInTheDocument();
      expect(screen.getByText('Abuse Protection & Rate Limits')).toBeInTheDocument();
    });
  });

  it('switches between tabs: Request Telemetry, FHIR Statement, and Prometheus Exposition', async () => {
    render(<SystemDiagnosticsWorkspace />);

    await waitFor(() => {
      expect(screen.getByText(/Component Readiness Matrix/i)).toBeInTheDocument();
    });

    // 1. Switch to Request & Worker Telemetry
    fireEvent.click(screen.getByText(/Request & Worker Telemetry/i));
    await waitFor(() => {
      expect(screen.getByText('HTTP Requests by Status')).toBeInTheDocument();
      expect(screen.getByText('42.5')).toBeInTheDocument();
      expect(screen.getByText('Task Execution Counters')).toBeInTheDocument();
      expect(screen.getByText('140')).toBeInTheDocument();
    });

    // 2. Switch to FHIR CapabilityStatement
    fireEvent.click(screen.getByText(/FHIR CapabilityStatement/i));
    await waitFor(() => {
      expect(screen.getByText('FHIR R4 CapabilityStatement')).toBeInTheDocument();
      expect(screen.getByText('Patient')).toBeInTheDocument();
      expect(screen.getByText('Encounter')).toBeInTheDocument();
      expect(screen.getByText('AuditEvent')).toBeInTheDocument();
    });

    // 3. Switch to Prometheus Exposition
    fireEvent.click(screen.getByText(/Prometheus Exposition/i));
    await waitFor(() => {
      expect(screen.getByText(/medigen_http_requests_total/)).toBeInTheDocument();
    });
  });

  it('handles refresh button click correctly', async () => {
    render(<SystemDiagnosticsWorkspace />);

    await waitFor(() => {
      expect(screen.getByText('Enterprise Infrastructure & Diagnostics')).toBeInTheDocument();
    });

    const refreshBtn = screen.getByText(/Refresh Diagnostics/i);
    fireEvent.click(refreshBtn);

    await waitFor(() => {
      expect(apiClient.systemApi.getLiveness).toHaveBeenCalledTimes(2);
      expect(apiClient.systemApi.getReadiness).toHaveBeenCalledTimes(2);
    });
  });
});
