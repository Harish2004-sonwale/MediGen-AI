import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SmartFhirEhrWorkspace } from '../components/interop/SmartFhirEhrWorkspace';
import { SystemDiagnosticsWorkspace } from '../components/operations/SystemDiagnosticsWorkspace';
import { SecurityComplianceWorkspace } from '../components/security/SecurityComplianceWorkspace';
import { Header } from '../components/layout/Header';
import { AuthProvider } from '../context/AuthContext';
import * as client from '../api/client';

// Mock the API client
vi.mock('../api/client', () => ({
  smartApi: {
    getSmartConfig: vi.fn().mockResolvedValue({
      issuer: 'https://app.medigen.ai/fhir',
      authorization_endpoint: 'https://app.medigen.ai/smart/auth',
      token_endpoint: 'https://app.medigen.ai/smart/token',
      capabilities: ['launch-standalone'],
    }),
    authorize: vi.fn(),
    exchangeToken: vi.fn(),
  },
  cdsApi: {
    discoverServices: vi.fn().mockResolvedValue({ services: [] }),
    invokePatientView: vi.fn().mockResolvedValue({ cards: [] }),
    invokeOrderSelect: vi.fn().mockResolvedValue({ cards: [] }),
  },
  terminologyApi: {
    normalizeConcept: vi.fn().mockResolvedValue({}),
  },
  fhirApi: {
    listSubscriptions: vi.fn().mockResolvedValue([]),
    createSubscription: vi.fn(),
    deleteSubscription: vi.fn(),
    getCapabilityStatement: vi.fn().mockResolvedValue({ fhirVersion: '4.0.1', rest: [{ resource: [] }] }),
    exportConsent: vi.fn(),
    exportAuditEvent: vi.fn(),
  },
  systemApi: {
    getLiveness: vi.fn().mockResolvedValue({ status: 'alive' }),
    getReadiness: vi.fn().mockResolvedValue({ status: 'ready', components: { database: { healthy: true } } }),
    getMetrics: vi.fn().mockResolvedValue({
      process: { memory_rss_mb: 120, cpu_percent: 2.5 },
      db_pool: { checked_out: 1, available: 9, total: 10 },
      redis: { connected: true },
      system: { cpu_count: 8, memory_total_gb: 16 },
      http: { total_requests: 100, requests_per_second: 1.5, error_rate_percent: 0.0 },
    }),
  },
  outboxApi: {
    getMetrics: vi.fn().mockResolvedValue({ pending: 0, published: 5, failed: 0, dead_letter: 0, total: 5 }),
    listEvents: vi.fn().mockResolvedValue([]),
    replayDeadLetter: vi.fn(),
  },
  mfaApi: {
    getStatus: vi.fn().mockResolvedValue({ is_enabled: false, last_used_at: null }),
    setup: vi.fn().mockResolvedValue({ provisioning_uri: 'otpauth://totp/test', secret_masked: 'ABCD****' }),
    verify: vi.fn(),
    disable: vi.fn(),
  },
  securityApi: {
    getComplianceSummary: vi.fn().mockResolvedValue({
      total_audit_events: 100,
      verified_integrity: true,
      active_consents: 5,
      open_security_incidents: 0,
      active_legal_holds: 0,
      compliance_score_percent: 98.5,
    }),
    getAuditEvents: vi.fn().mockResolvedValue({ events: [], total_count: 0, page: 1 }),
    getPatientConsents: vi.fn().mockResolvedValue({ consents: [] }),
    getIncidents: vi.fn().mockResolvedValue([]),
    getDataRetentionPolicies: vi.fn().mockResolvedValue([]),
    getLegalHolds: vi.fn().mockResolvedValue([]),
  },
  bulkExportApi: {
    initExport: vi.fn(),
    getExportJob: vi.fn(),
    deleteExportJob: vi.fn(),
  },
}));

describe('Phase 9.0.23 Enterprise UI Orchestration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('SmartFhirEhrWorkspace navigates to Topic Subscriptions tab and launches Bulk Export modal', async () => {
    render(<SmartFhirEhrWorkspace selectedPatientId="PAT-001" />);

    // 1. Check Topic Subscriptions tab button exists and click it
    const subTabBtn = screen.getByRole('button', { name: /topic subscriptions/i });
    expect(subTabBtn).toBeDefined();
    fireEvent.click(subTabBtn);

    // Verify subscriptions console panel is mounted
    await waitFor(() => {
      expect(screen.getByTestId('fhir-subscriptions-tab-panel')).toBeDefined();
    });

    // 2. Check Bulk Export button exists and click it
    const bulkBtn = screen.getByRole('button', { name: /bulk fhir export/i });
    expect(bulkBtn).toBeDefined();
    fireEvent.click(bulkBtn);

    // Verify bulk export modal is visible
    await waitFor(() => {
      expect(screen.getByText(/FHIR R4 Bulk Data Export \(\$export\)/i)).toBeDefined();
    });
  });

  it('SystemDiagnosticsWorkspace navigates to Outbox & DLQ Monitor subtab', async () => {
    render(<SystemDiagnosticsWorkspace />);

    // Check Outbox & DLQ tab button exists
    const outboxTabBtn = screen.getByRole('button', { name: /outbox & dlq monitor/i });
    expect(outboxTabBtn).toBeDefined();
    fireEvent.click(outboxTabBtn);

    // Verify outbox DLQ panel is mounted
    await waitFor(() => {
      expect(screen.getByTestId('outbox-dlq-tab-panel')).toBeDefined();
      expect(screen.getByText(/Transactional Outbox & Dead-Letter Queue/i)).toBeDefined();
    });
  });

  it('SecurityComplianceWorkspace opens MFA Configuration Modal', async () => {
    const dummyPatient = {
      id: 1,
      patient_id: 'PAT-001',
      first_name: 'John',
      last_name: 'Doe',
      gender: 'male',
      status: 'active',
      created_at: '2026-01-01',
      updated_at: '2026-01-01',
    };

    render(
      <SecurityComplianceWorkspace
        patients={[dummyPatient as any]}
        selectedPatient={dummyPatient as any}
        onSelectPatient={() => {}}
      />
    );

    // Find and click MFA Configuration button
    const mfaBtn = screen.getByTestId('mfa-settings-btn');
    expect(mfaBtn).toBeDefined();
    fireEvent.click(mfaBtn);

    // Verify MFA Management modal appears
    await waitFor(() => {
      expect(screen.getByText(/Multi-Factor Authentication/i)).toBeDefined();
    });
  });
});
