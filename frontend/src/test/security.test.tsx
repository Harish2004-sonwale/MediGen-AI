import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { SecurityComplianceWorkspace } from '../components/security/SecurityComplianceWorkspace';
import { securityApi, fhirApi } from '../api/client';
import { Patient } from '../types';

vi.mock('../api/client', () => ({
  securityApi: {
    getComplianceSummary: vi.fn().mockResolvedValue({
      generated_at: '2026-08-30T10:00:00Z',
      total_audit_events: 142,
      recent_audit_events_24h: 35,
      audit_tamper_integrity_status: 'VALID',
      total_active_consents: 12,
      total_revoked_consents: 2,
      open_security_incidents: 1,
      critical_security_incidents: 0,
      active_legal_holds: 2,
      active_retention_policies: 5,
      compliance_score_percent: 98.5,
      status: 'COMPLIANT',
    }),
    verifyAuditIntegrity: vi.fn().mockResolvedValue({
      verified_at: '2026-08-30T10:05:00Z',
      total_records_checked: 142,
      tamper_detected: false,
      broken_links_count: 0,
      tampered_event_ids: [],
      chain_head_hash: 'a1b2c3d4e5f678901234567890abcdef1234567890abcdef1234567890abcdef',
      status: 'VALID',
    }),
    getAuditEvents: vi.fn().mockResolvedValue({
      events: [
        {
          id: 1,
          event_id: 'AUD-20260830-1001',
          timestamp: '2026-08-30T09:30:00Z',
          user_id: 10,
          user_role: 'DOCTOR',
          patient_id: 'PAT-SEC-001',
          action: 'READ',
          resource_type: 'Patient',
          resource_id: 'PAT-SEC-001',
          ip_address: '192.168.1.50',
          purpose_of_use: 'TREATMENT',
          outcome: 'SUCCESS',
          metadata_json: { action_detail: 'Chart review' },
          prev_record_hash: '0000000000000000000000000000000000000000000000000000000000000000',
          record_hash: '1111111111111111111111111111111111111111111111111111111111111111',
        },
      ],
      total_count: 1,
      page: 1,
      page_size: 20,
    }),
    getPatientConsents: vi.fn().mockResolvedValue([
      {
        id: 1,
        consent_id: 'CNS-20260830-9901',
        patient_id: 'PAT-SEC-001',
        status: 'ACTIVE',
        scope: 'RESEARCH_ONLY',
        policy_rule: 'PERMIT',
        purpose_of_use: 'RESEARCH',
        data_category: 'GENOMICS',
        valid_from: '2026-08-30T00:00:00Z',
        signed_by_patient: true,
        signer_name: 'Eleanor Vance',
        signer_relationship: 'SELF',
        digital_signature_hash: 'c8f498b3f2e1a0d786543210abcdef9876543210abcdef9876543210abcdef98',
        created_at: '2026-08-30T00:00:00Z',
      },
    ]),
    grantConsent: vi.fn().mockResolvedValue({
      id: 2,
      consent_id: 'CNS-20260830-9902',
      patient_id: 'PAT-SEC-001',
      status: 'ACTIVE',
      scope: 'GENOMICS_ONLY',
      policy_rule: 'DENY',
      purpose_of_use: 'RESEARCH',
      data_category: 'GENOMICS',
      valid_from: '2026-08-30T00:00:00Z',
      signed_by_patient: true,
      signer_name: 'Eleanor Vance',
      signer_relationship: 'SELF',
      digital_signature_hash: 'signature_hash_test_123',
      created_at: '2026-08-30T00:00:00Z',
    }),
    revokeConsent: vi.fn().mockResolvedValue({
      id: 1,
      consent_id: 'CNS-20260830-9901',
      status: 'REVOKED',
      revocation_reason: 'Patient withdrew consent',
    }),
    verifyConsent: vi.fn().mockResolvedValue({
      patient_id: 'PAT-SEC-001',
      resource_type: 'GenomicProfile',
      action: 'READ',
      purpose_of_use: 'RESEARCH',
      is_permitted: true,
      reason: 'Permitted by active explicit patient research/disclosure consent directive',
      matched_consent_id: 'CNS-20260830-9901',
      is_emergency_override: false,
    }),
    listIncidents: vi.fn().mockResolvedValue([
      {
        id: 1,
        incident_id: 'SEC-20260830-4001',
        detected_at: '2026-08-30T08:00:00Z',
        severity: 'HIGH',
        status: 'OPEN',
        event_type: 'CROSS_PATIENT_ACCESS_ATTEMPT',
        description: 'User accessed 4 distinct patient records within 5 minutes',
        evidence_metadata: { patient_count: 4 },
        created_at: '2026-08-30T08:00:00Z',
        updated_at: '2026-08-30T08:00:00Z',
      },
    ]),
    updateIncident: vi.fn().mockResolvedValue({
      id: 1,
      incident_id: 'SEC-20260830-4001',
      status: 'RESOLVED',
      resolution_notes: 'Investigated and authorized by attending physician.',
    }),
    runSecurityScan: vi.fn().mockResolvedValue({
      scanned_at: '2026-08-30T10:10:00Z',
      events_analyzed: 50,
      anomalies_detected: 0,
      new_incidents_created: 0,
      incident_ids: [],
    }),
    getRetentionPolicies: vi.fn().mockResolvedValue([
      {
        id: 1,
        policy_code: 'ADULT_EHR_7YR',
        data_category: 'CLINICAL_ENCOUNTERS',
        retention_period_days: 2555,
        action_on_expiry: 'ARCHIVE',
        description: 'Adult medical records retention policy (7 years)',
        is_active: true,
        created_at: '2026-08-30T00:00:00Z',
        updated_at: '2026-08-30T00:00:00Z',
      },
    ]),
    listLegalHolds: vi.fn().mockResolvedValue([
      {
        id: 1,
        hold_id: 'HLD-20260830-5001',
        patient_id: 'PAT-SEC-001',
        scope_category: 'ALL_RECORDS',
        reason: 'Active Clinical Trial Follow-Up',
        status: 'ACTIVE',
        placed_by_user_id: 1,
        placed_at: '2026-08-30T00:00:00Z',
        notes: 'Clinical trial hold',
        created_at: '2026-08-30T00:00:00Z',
        updated_at: '2026-08-30T00:00:00Z',
      },
    ]),
    placeLegalHold: vi.fn().mockResolvedValue({
      id: 2,
      hold_id: 'HLD-20260830-5002',
      patient_id: 'PAT-SEC-001',
      scope_category: 'GENOMICS',
      reason: 'Audit inspection',
      status: 'ACTIVE',
      placed_by_user_id: 1,
      placed_at: '2026-08-30T10:00:00Z',
    }),
    releaseLegalHold: vi.fn().mockResolvedValue({
      id: 1,
      hold_id: 'HLD-20260830-5001',
      status: 'RELEASED',
    }),
  },
  fhirApi: {
    exportConsent: vi.fn().mockResolvedValue({
      resourceType: 'Consent',
      id: 'CNS-20260830-9901',
      status: 'active',
    }),
    exportAuditEvent: vi.fn().mockResolvedValue({
      resourceType: 'AuditEvent',
      id: 'AUD-20260830-1001',
      type: { code: 'rest' },
    }),
    exportPatientConsentsBundle: vi.fn().mockResolvedValue({
      resourceType: 'Bundle',
      type: 'collection',
      entry: [],
    }),
  },
}));

const mockPatients: Patient[] = [
  {
    id: 1,
    patient_id: 'PAT-SEC-001',
    first_name: 'Eleanor',
    last_name: 'Vance',
    gender: 'female',
    date_of_birth: '1988-04-12',
    is_active: true,
    created_at: '2026-08-30T00:00:00Z',
    phone: '+1-555-0199',
    email: 'eleanor.vance@example.org',
    address: '742 Evergreen Terrace',
  },
];

describe('SecurityComplianceWorkspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders workspace banner, compliance health score, and metrics', async () => {
    render(
      <SecurityComplianceWorkspace
        patients={mockPatients}
        selectedPatient={mockPatients[0]}
        onSelectPatient={vi.fn()}
      />
    );

    expect(screen.getByTestId('security-compliance-workspace')).toBeInTheDocument();
    expect(screen.getByText('Clinical Security & Compliance Governance')).toBeInTheDocument();

    await waitFor(() => {
      expect(securityApi.getComplianceSummary).toHaveBeenCalledTimes(1);
    });

    expect(screen.getByText('98.5%')).toBeInTheDocument();
    expect(screen.getByText('COMPLIANT')).toBeInTheDocument();
    expect(screen.getByText('142')).toBeInTheDocument(); // total audit logs
  });

  it('triggers cryptographic hash chain integrity verification', async () => {
    render(
      <SecurityComplianceWorkspace
        patients={mockPatients}
        selectedPatient={mockPatients[0]}
        onSelectPatient={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('98.5%')).toBeInTheDocument();
    });

    const verifyBtn = screen.getByTestId('verify-integrity-btn');
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(securityApi.verifyAuditIntegrity).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      expect(screen.getByText(/Audit Trail Integrity: VALID/i)).toBeInTheDocument();
    });
  });

  it('triggers proactive threat and anomaly scan', async () => {
    render(
      <SecurityComplianceWorkspace
        patients={mockPatients}
        selectedPatient={mockPatients[0]}
        onSelectPatient={vi.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('98.5%')).toBeInTheDocument();
    });

    const scanBtn = screen.getByTestId('run-scan-btn');
    fireEvent.click(scanBtn);

    await waitFor(() => {
      expect(securityApi.runSecurityScan).toHaveBeenCalledWith(60);
    });

    await waitFor(() => {
      expect(screen.getByText(/Security scan complete/i)).toBeInTheDocument();
    });
  });

  it('navigates to Patient Consent tab and evaluates policy simulation', async () => {
    render(
      <SecurityComplianceWorkspace
        patients={mockPatients}
        selectedPatient={mockPatients[0]}
        onSelectPatient={vi.fn()}
      />
    );

    const consentTabBtn = screen.getByTestId('tab-consent');
    fireEvent.click(consentTabBtn);

    await waitFor(() => {
      expect(securityApi.getPatientConsents).toHaveBeenCalledWith('PAT-SEC-001');
    });

    expect(screen.getByText('Active Consent Directives')).toBeInTheDocument();
    expect(screen.getByText('CNS-20260830-9901')).toBeInTheDocument();

    // Test simulator
    const evalBtn = screen.getByTestId('verify-policy-btn');
    fireEvent.click(evalBtn);

    await waitFor(() => {
      expect(securityApi.verifyConsent).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('✅ ACCESS PERMITTED')).toBeInTheDocument();
    });
  });

  it('navigates to Security Incidents tab and triages incident', async () => {
    render(
      <SecurityComplianceWorkspace
        patients={mockPatients}
        selectedPatient={mockPatients[0]}
        onSelectPatient={vi.fn()}
      />
    );

    const incidentTabBtn = screen.getByTestId('tab-incidents');
    fireEvent.click(incidentTabBtn);

    await waitFor(() => {
      expect(securityApi.listIncidents).toHaveBeenCalled();
    });

    expect(screen.getByText('SEC-20260830-4001')).toBeInTheDocument();
    expect(screen.getByText('CROSS_PATIENT_ACCESS_ATTEMPT')).toBeInTheDocument();
  });

  it('navigates to Retention & Legal Holds tab and displays policies and holds', async () => {
    render(
      <SecurityComplianceWorkspace
        patients={mockPatients}
        selectedPatient={mockPatients[0]}
        onSelectPatient={vi.fn()}
      />
    );

    const govTabBtn = screen.getByTestId('tab-governance');
    fireEvent.click(govTabBtn);

    await waitFor(() => {
      expect(securityApi.getRetentionPolicies).toHaveBeenCalled();
      expect(securityApi.listLegalHolds).toHaveBeenCalled();
    });

    expect(screen.getByText('ADULT_EHR_7YR')).toBeInTheDocument();
    expect(screen.getByText('HLD-20260830-5001')).toBeInTheDocument();
  });
});
