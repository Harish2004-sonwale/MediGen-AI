import React, { useEffect, useState } from 'react';
import { fhirApi, securityApi } from '../../api/client';
import {
  AuditIntegrityVerificationResponse,
  ClinicalAuditEvent,
  ComplianceSummaryResponse,
  ConsentPolicyRule,
  ConsentScope,
  DataRetentionPolicy,
  IncidentSeverity,
  IncidentStatus,
  LegalClinicalHold,
  Patient,
  PatientConsent,
  SecurityIncident,
  SecurityScanResult,
} from '../../types';

interface SecurityComplianceWorkspaceProps {
  patients: Patient[];
  selectedPatient: Patient | null;
  onSelectPatient: (patient: Patient) => void;
}

export const SecurityComplianceWorkspace: React.FC<SecurityComplianceWorkspaceProps> = ({
  patients,
  selectedPatient,
  onSelectPatient,
}) => {
  const [activeTab, setActiveTab] = useState<'audit' | 'consent' | 'incidents' | 'governance'>('audit');
  const [loading, setLoading] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Data states
  const [complianceSummary, setComplianceSummary] = useState<ComplianceSummaryResponse | null>(null);
  const [integrityStatus, setIntegrityStatus] = useState<AuditIntegrityVerificationResponse | null>(null);
  const [auditEvents, setAuditEvents] = useState<ClinicalAuditEvent[]>([]);
  const [auditPage, setAuditPage] = useState<number>(1);
  const [auditTotal, setAuditTotal] = useState<number>(0);
  const [selectedAuditEvent, setSelectedAuditEvent] = useState<ClinicalAuditEvent | null>(null);

  // Consent states
  const [patientConsents, setPatientConsents] = useState<PatientConsent[]>([]);
  const [grantModalOpen, setGrantModalOpen] = useState<boolean>(false);
  const [newConsentScope, setNewConsentScope] = useState<ConsentScope>('RESEARCH_ONLY');
  const [newConsentRule, setNewConsentRule] = useState<ConsentPolicyRule>('PERMIT');
  const [newConsentPurpose, setNewConsentPurpose] = useState<string>('RESEARCH');
  const [newConsentCategory, setNewConsentCategory] = useState<string>('GENOMICS');
  const [newConsentSigner, setNewConsentSigner] = useState<string>('');
  const [newConsentRelationship, setNewConsentRelationship] = useState<string>('SELF');

  // Consent test simulator
  const [testResourceType, setTestResourceType] = useState<string>('GenomicProfile');
  const [testAction, setTestAction] = useState<string>('READ');
  const [testPurpose, setTestPurpose] = useState<string>('RESEARCH');
  const [testCategory, setTestCategory] = useState<string>('GENOMICS');
  const [verificationResult, setVerificationResult] = useState<any>(null);

  // Incidents states
  const [incidents, setIncidents] = useState<SecurityIncident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<SecurityIncident | null>(null);
  const [triageStatus, setTriageStatus] = useState<IncidentStatus>('INVESTIGATING');
  const [triageNotes, setTriageNotes] = useState<string>('');
  const [lastScanResult, setLastScanResult] = useState<SecurityScanResult | null>(null);

  // Governance & Holds states
  const [retentionPolicies, setRetentionPolicies] = useState<DataRetentionPolicy[]>([]);
  const [legalHolds, setLegalHolds] = useState<LegalClinicalHold[]>([]);
  const [newHoldReason, setNewHoldReason] = useState<string>('');
  const [newHoldScope, setNewHoldScope] = useState<string>('ALL_RECORDS');
  const [newHoldNotes, setNewHoldNotes] = useState<string>('');
  const [holdModalOpen, setHoldModalOpen] = useState<boolean>(false);

  // Fetch initial summary
  const loadComplianceSummary = async () => {
    try {
      setLoading(true);
      const summary = await securityApi.getComplianceSummary();
      setComplianceSummary(summary);
    } catch (err: any) {
      console.error('Failed to load compliance summary:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch audit events
  const loadAuditEvents = async (page = 1) => {
    try {
      setLoading(true);
      const res = await securityApi.getAuditEvents({
        patient_id: selectedPatient?.patient_id,
        page,
        page_size: 20,
      });
      setAuditEvents(res.events);
      setAuditTotal(res.total_count);
      setAuditPage(res.page);
    } catch (err: any) {
      console.error('Failed to load audit events:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch patient consents
  const loadPatientConsents = async () => {
    if (!selectedPatient) return;
    try {
      setLoading(true);
      const res = await securityApi.getPatientConsents(selectedPatient.patient_id);
      setPatientConsents(res);
    } catch (err: any) {
      console.error('Failed to load patient consents:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch incidents
  const loadIncidents = async () => {
    try {
      setLoading(true);
      const res = await securityApi.listIncidents();
      setIncidents(res);
    } catch (err: any) {
      console.error('Failed to load incidents:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch retention & holds
  const loadGovernanceData = async () => {
    try {
      setLoading(true);
      const [policies, holds] = await Promise.all([
        securityApi.getRetentionPolicies(),
        securityApi.listLegalHolds(),
      ]);
      setRetentionPolicies(policies);
      setLegalHolds(holds);
    } catch (err: any) {
      console.error('Failed to load governance data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadComplianceSummary();
    if (activeTab === 'audit') loadAuditEvents(1);
    if (activeTab === 'consent' && selectedPatient) loadPatientConsents();
    if (activeTab === 'incidents') loadIncidents();
    if (activeTab === 'governance') loadGovernanceData();
  }, [activeTab, selectedPatient]);

  // Actions
  const handleVerifyIntegrity = async () => {
    try {
      setLoading(true);
      const res = await securityApi.verifyAuditIntegrity();
      setIntegrityStatus(res);
      setActionMessage({
        type: res.tamper_detected ? 'error' : 'success',
        text: `Audit Trail Integrity: ${res.status} (${res.total_records_checked} events checked, ${res.broken_links_count} broken links detected).`,
      });
      loadComplianceSummary();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Verification failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleRunSecurityScan = async () => {
    try {
      setLoading(true);
      const res = await securityApi.runSecurityScan(60);
      setLastScanResult(res);
      setActionMessage({
        type: 'success',
        text: `Security scan complete: Analyzed ${res.events_analyzed} events, detected ${res.anomalies_detected} anomalies.`,
      });
      loadIncidents();
      loadComplianceSummary();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Security scan failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleGrantConsent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatient) return;
    try {
      setLoading(true);
      await securityApi.grantConsent(selectedPatient.patient_id, {
        scope: newConsentScope,
        policy_rule: newConsentRule,
        purpose_of_use: newConsentPurpose,
        data_category: newConsentCategory,
        signed_by_patient: true,
        signer_name: newConsentSigner || `${selectedPatient.first_name} ${selectedPatient.last_name}`,
        signer_relationship: newConsentRelationship,
      });
      setGrantModalOpen(false);
      setActionMessage({ type: 'success', text: 'Patient consent directive registered with cryptographic signature.' });
      loadPatientConsents();
      loadComplianceSummary();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to grant consent.' });
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeConsent = async (consentId: string) => {
    const reason = window.prompt('Enter reason for consent revocation:');
    if (!reason) return;
    try {
      setLoading(true);
      await securityApi.revokeConsent(consentId, { revocation_reason: reason });
      setActionMessage({ type: 'success', text: 'Consent directive revoked immediately.' });
      loadPatientConsents();
      loadComplianceSummary();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to revoke consent.' });
    } finally {
      setLoading(false);
    }
  };

  const handleTestConsentVerification = async () => {
    if (!selectedPatient) return;
    try {
      setLoading(true);
      const res = await securityApi.verifyConsent({
        patient_id: selectedPatient.patient_id,
        resource_type: testResourceType,
        action: testAction,
        purpose_of_use: testPurpose,
        data_category: testCategory,
      });
      setVerificationResult(res);
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Verification test failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedIncident) return;
    try {
      setLoading(true);
      await securityApi.updateIncident(selectedIncident.incident_id, {
        status: triageStatus,
        resolution_notes: triageNotes,
      });
      setActionMessage({ type: 'success', text: `Incident ${selectedIncident.incident_id} updated.` });
      setSelectedIncident(null);
      loadIncidents();
      loadComplianceSummary();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to update incident.' });
    } finally {
      setLoading(false);
    }
  };

  const handlePlaceLegalHold = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await securityApi.placeLegalHold({
        patient_id: selectedPatient?.patient_id,
        scope_category: newHoldScope,
        reason: newHoldReason,
        notes: newHoldNotes,
      });
      setHoldModalOpen(false);
      setNewHoldReason('');
      setNewHoldNotes('');
      setActionMessage({ type: 'success', text: 'Legal/Clinical hold successfully placed.' });
      loadGovernanceData();
      loadComplianceSummary();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to place legal hold.' });
    } finally {
      setLoading(false);
    }
  };

  const handleReleaseLegalHold = async (holdId: string) => {
    const notes = window.prompt('Enter release notes:');
    if (notes === null) return;
    try {
      setLoading(true);
      await securityApi.releaseLegalHold(holdId, { notes });
      setActionMessage({ type: 'success', text: 'Legal hold released.' });
      loadGovernanceData();
      loadComplianceSummary();
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to release legal hold.' });
    } finally {
      setLoading(false);
    }
  };

  const handleExportFHIRConsent = async (consentId: string) => {
    try {
      setLoading(true);
      const res = await fhirApi.exportConsent(consentId);
      const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `FHIR_Consent_${consentId}.json`;
      a.click();
      setActionMessage({ type: 'success', text: `Exported FHIR Consent resource ${consentId}.` });
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'FHIR export failed.' });
    } finally {
      setLoading(false);
    }
  };

  const handleExportFHIRAuditEvent = async (eventId: string) => {
    try {
      setLoading(true);
      const res = await fhirApi.exportAuditEvent(eventId);
      const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `FHIR_AuditEvent_${eventId}.json`;
      a.click();
      setActionMessage({ type: 'success', text: `Exported FHIR AuditEvent resource ${eventId}.` });
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'FHIR export failed.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="security-compliance-workspace">
      {/* Top Banner & Metrics */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-indigo-800/40 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-3xl">🛡️</span>
              <div>
                <h1 className="text-2xl font-bold text-white">Clinical Security & Compliance Governance</h1>
                <p className="text-sm text-indigo-200/80">
                  Immutable cryptographic audit trails, patient consent sovereignty & proactive threat monitoring
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleVerifyIntegrity}
              disabled={loading}
              className="px-4 py-2 bg-emerald-600/80 hover:bg-emerald-600 text-white rounded-xl font-medium text-xs shadow-md transition-all flex items-center gap-2"
              data-testid="verify-integrity-btn"
            >
              <span>🔗</span> Verify Hash Chain
            </button>
            <button
              onClick={handleRunSecurityScan}
              disabled={loading}
              className="px-4 py-2 bg-amber-600/80 hover:bg-amber-600 text-white rounded-xl font-medium text-xs shadow-md transition-all flex items-center gap-2"
              data-testid="run-scan-btn"
            >
              <span>🔍</span> Proactive Threat Scan
            </button>
            <button
              onClick={loadComplianceSummary}
              disabled={loading}
              className="px-4 py-2 bg-indigo-600/80 hover:bg-indigo-600 text-white rounded-xl font-medium text-xs shadow-md transition-all flex items-center gap-2"
            >
              <span>🔄</span> Refresh Posture
            </button>
          </div>
        </div>

        {/* Real-Time Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-6">
          <div className="bg-slate-800/60 backdrop-blur-md border border-slate-700/50 rounded-xl p-3 text-center">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Compliance Score</div>
            <div className="text-2xl font-black text-emerald-400 mt-1">
              {complianceSummary?.compliance_score_percent ?? 100}%
            </div>
            <div className="text-[10px] text-emerald-300/80 mt-0.5">
              {complianceSummary?.status ?? 'COMPLIANT'}
            </div>
          </div>

          <div className="bg-slate-800/60 backdrop-blur-md border border-slate-700/50 rounded-xl p-3 text-center">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Audit Integrity</div>
            <div className={`text-xl font-bold mt-1.5 ${
              (integrityStatus?.status || complianceSummary?.audit_tamper_integrity_status) === 'COMPROMISED'
                ? 'text-rose-400'
                : 'text-emerald-400'
            }`}>
              {integrityStatus?.status || complianceSummary?.audit_tamper_integrity_status || 'VALID'}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">SHA-256 Chain</div>
          </div>

          <div className="bg-slate-800/60 backdrop-blur-md border border-slate-700/50 rounded-xl p-3 text-center">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Audit Logs</div>
            <div className="text-2xl font-bold text-white mt-1">
              {complianceSummary?.total_audit_events ?? 0}
            </div>
            <div className="text-[10px] text-indigo-300 mt-0.5">
              +{complianceSummary?.recent_audit_events_24h ?? 0} in 24h
            </div>
          </div>

          <div className="bg-slate-800/60 backdrop-blur-md border border-slate-700/50 rounded-xl p-3 text-center">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Consents</div>
            <div className="text-2xl font-bold text-sky-400 mt-1">
              {complianceSummary?.total_active_consents ?? 0}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              {complianceSummary?.total_revoked_consents ?? 0} Revoked
            </div>
          </div>

          <div className="bg-slate-800/60 backdrop-blur-md border border-slate-700/50 rounded-xl p-3 text-center">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Security Incidents</div>
            <div className="text-2xl font-bold text-amber-400 mt-1">
              {complianceSummary?.open_security_incidents ?? 0}
            </div>
            <div className="text-[10px] text-rose-400 mt-0.5">
              {complianceSummary?.critical_security_incidents ?? 0} Critical
            </div>
          </div>

          <div className="bg-slate-800/60 backdrop-blur-md border border-slate-700/50 rounded-xl p-3 text-center">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Legal Holds</div>
            <div className="text-2xl font-bold text-purple-400 mt-1">
              {complianceSummary?.active_legal_holds ?? 0}
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">Active Holds</div>
          </div>
        </div>
      </div>

      {/* Action Notification */}
      {actionMessage && (
        <div className={`p-4 rounded-xl text-sm flex items-center justify-between shadow-lg ${
          actionMessage.type === 'success'
            ? 'bg-emerald-950/80 border border-emerald-500/50 text-emerald-200'
            : 'bg-rose-950/80 border border-rose-500/50 text-rose-200'
        }`}>
          <span>{actionMessage.text}</span>
          <button onClick={() => setActionMessage(null)} className="text-xs font-bold underline ml-4">Dismiss</button>
        </div>
      )}

      {/* Patient Selection Bar */}
      <div className="bg-slate-800/80 border border-slate-700 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-slate-400 text-sm font-semibold">Active Patient Context:</span>
          <select
            value={selectedPatient?.patient_id || ''}
            onChange={(e) => {
              const p = patients.find((pat) => pat.patient_id === e.target.value);
              if (p) onSelectPatient(p);
            }}
            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white focus:ring-2 focus:ring-indigo-500"
            data-testid="patient-selector"
          >
            <option value="">-- All Patients (Audit Global) --</option>
            {patients.map((p) => (
              <option key={p.patient_id} value={p.patient_id}>
                {p.first_name} {p.last_name} ({p.patient_id})
              </option>
            ))}
          </select>
        </div>

        {selectedPatient && (
          <div className="text-xs text-slate-400 flex items-center gap-2">
            <span>DOB: {selectedPatient.date_of_birth}</span>
            <span>•</span>
            <span>Gender: {selectedPatient.gender}</span>
            <span>•</span>
            <span className="text-emerald-400 font-medium">Status: {selectedPatient.is_active ? 'Active' : 'Inactive'}</span>
          </div>
        )}
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex border-b border-slate-700 space-x-1">
        <button
          onClick={() => setActiveTab('audit')}
          className={`px-5 py-2.5 text-sm font-medium rounded-t-xl transition-all ${
            activeTab === 'audit'
              ? 'bg-slate-800 text-indigo-400 border-t-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          data-testid="tab-audit"
        >
          📜 Immutable Audit Trail
        </button>
        <button
          onClick={() => setActiveTab('consent')}
          className={`px-5 py-2.5 text-sm font-medium rounded-t-xl transition-all ${
            activeTab === 'consent'
              ? 'bg-slate-800 text-indigo-400 border-t-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          data-testid="tab-consent"
        >
          ✍️ Patient Consent Sovereignty
        </button>
        <button
          onClick={() => setActiveTab('incidents')}
          className={`px-5 py-2.5 text-sm font-medium rounded-t-xl transition-all ${
            activeTab === 'incidents'
              ? 'bg-slate-800 text-indigo-400 border-t-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          data-testid="tab-incidents"
        >
          🚨 Security Threat & Incident Triage
        </button>
        <button
          onClick={() => setActiveTab('governance')}
          className={`px-5 py-2.5 text-sm font-medium rounded-t-xl transition-all ${
            activeTab === 'governance'
              ? 'bg-slate-800 text-indigo-400 border-t-2 border-indigo-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
          data-testid="tab-governance"
        >
          ⚖️ Retention Schedules & Legal Holds
        </button>
      </div>

      {/* TAB 1: IMMUTABLE AUDIT TRAIL */}
      {activeTab === 'audit' && (
        <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-white">Immutable Clinical Audit Stream</h2>
              <p className="text-xs text-slate-400">Cryptographically linked SHA-256 audit blocks with non-PHI metadata</p>
            </div>
            <div className="text-xs text-slate-400">
              Showing {auditEvents.length} of {auditTotal} total records
            </div>
          </div>

          {/* Audit Events Table */}
          <div className="overflow-x-auto rounded-xl border border-slate-700">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/80 text-xs uppercase font-semibold text-slate-400">
                <tr>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Event ID</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Resource</th>
                  <th className="px-4 py-3">User Role</th>
                  <th className="px-4 py-3">Patient</th>
                  <th className="px-4 py-3">Outcome</th>
                  <th className="px-4 py-3">SHA-256 Hash</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/60 bg-slate-800/40">
                {auditEvents.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="px-4 py-8 text-center text-slate-500">
                      No audit events recorded for current filter criteria.
                    </td>
                  </tr>
                ) : (
                  auditEvents.map((ev) => (
                    <tr key={ev.event_id} className="hover:bg-slate-700/40 transition-colors">
                      <td className="px-4 py-3 text-xs whitespace-nowrap text-slate-400">
                        {new Date(ev.timestamp).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-indigo-300">{ev.event_id}</td>
                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-700 text-slate-200">
                          {ev.action}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-200">
                        {ev.resource_type} {ev.resource_id ? `(${ev.resource_id})` : ''}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400">{ev.user_role}</td>
                      <td className="px-4 py-3 text-xs text-slate-400">{ev.patient_id || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          ev.outcome === 'SUCCESS'
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                            : 'bg-rose-950 text-rose-300 border border-rose-800'
                        }`}>
                          {ev.outcome}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-[11px] text-slate-400" title={ev.record_hash}>
                        {ev.record_hash.substring(0, 10)}...{ev.record_hash.substring(ev.record_hash.length - 6)}
                      </td>
                      <td className="px-4 py-3 text-xs whitespace-nowrap space-x-2">
                        <button
                          onClick={() => setSelectedAuditEvent(ev)}
                          className="text-indigo-400 hover:text-indigo-300 font-medium"
                        >
                          Inspect
                        </button>
                        <button
                          onClick={() => handleExportFHIRAuditEvent(ev.event_id)}
                          className="text-emerald-400 hover:text-emerald-300 font-medium"
                          title="Export as FHIR R4 AuditEvent"
                        >
                          FHIR
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Audit Event Detail Drawer */}
          {selectedAuditEvent && (
            <div className="bg-slate-900 border border-indigo-500/40 rounded-xl p-5 mt-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>🔎</span> Audit Record Deep Inspection ({selectedAuditEvent.event_id})
                </h3>
                <button
                  onClick={() => setSelectedAuditEvent(null)}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Close ✕
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-slate-400 block">Previous Record Hash (Chain Link):</span>
                  <span className="font-mono text-slate-300 break-all">{selectedAuditEvent.prev_record_hash}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Cryptographic Record Hash:</span>
                  <span className="font-mono text-emerald-400 break-all">{selectedAuditEvent.record_hash}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Client IP / User Agent:</span>
                  <span className="text-slate-300">{selectedAuditEvent.ip_address || '127.0.0.1'} ({selectedAuditEvent.user_agent || 'Standard Client'})</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Purpose of Use:</span>
                  <span className="text-indigo-300 font-semibold">{selectedAuditEvent.purpose_of_use}</span>
                </div>
              </div>
              <div>
                <span className="text-slate-400 text-xs block mb-1">Sanitized Non-PHI Metadata:</span>
                <pre className="bg-slate-950 p-3 rounded-lg text-xs font-mono text-slate-300 overflow-x-auto">
                  {JSON.stringify(selectedAuditEvent.metadata_json, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: PATIENT CONSENT SOVEREIGNTY */}
      {activeTab === 'consent' && (
        <div className="space-y-6">
          {!selectedPatient ? (
            <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-8 text-center text-slate-400">
              Please select a patient context above to view and manage active consent directives.
            </div>
          ) : (
            <>
              {/* Header & New Consent Trigger */}
              <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-6 shadow-xl space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h2 className="text-lg font-bold text-white">Active Consent Directives</h2>
                    <p className="text-xs text-slate-400">
                      Granular patient sovereignty for {selectedPatient.first_name} {selectedPatient.last_name} ({selectedPatient.patient_id})
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setGrantModalOpen(true)}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-md transition-all flex items-center gap-1.5"
                      data-testid="grant-consent-btn"
                    >
                      <span>➕</span> Grant Consent Directive
                    </button>
                    <button
                      onClick={() => fhirApi.exportPatientConsentsBundle(selectedPatient.patient_id)}
                      className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-xl text-xs font-semibold shadow-md transition-all"
                    >
                      FHIR Bundle
                    </button>
                  </div>
                </div>

                {/* Consent List */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {patientConsents.length === 0 ? (
                    <div className="col-span-2 text-center py-6 text-slate-500 text-xs">
                      No active or revoked consent directives registered for this patient. Standard treatment care team authorization applies.
                    </div>
                  ) : (
                    patientConsents.map((c) => (
                      <div
                        key={c.consent_id}
                        className={`border rounded-xl p-4 transition-all ${
                          c.status === 'ACTIVE'
                            ? c.policy_rule === 'PERMIT'
                              ? 'bg-emerald-950/20 border-emerald-800/60'
                              : 'bg-amber-950/20 border-amber-800/60'
                            : 'bg-slate-900/50 border-slate-800 opacity-60'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs text-indigo-300 font-bold">{c.consent_id}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            c.status === 'ACTIVE'
                              ? 'bg-emerald-900/80 text-emerald-200'
                              : 'bg-rose-900/80 text-rose-200'
                          }`}>
                            {c.status}
                          </span>
                        </div>
                        <div className="mt-2 space-y-1 text-xs">
                          <div className="flex justify-between">
                            <span className="text-slate-400">Policy Rule:</span>
                            <span className={`font-bold ${c.policy_rule === 'PERMIT' ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {c.policy_rule}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-400">Scope:</span>
                            <span className="text-white font-medium">{c.scope}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-400">Purpose / Category:</span>
                            <span className="text-slate-300">{c.purpose_of_use} {c.data_category ? `(${c.data_category})` : ''}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-400">Signer:</span>
                            <span className="text-slate-300">{c.signer_name} ({c.signer_relationship})</span>
                          </div>
                          <div className="pt-1">
                            <span className="text-[10px] text-slate-500 font-mono block break-all">
                              Digital Signature: {c.digital_signature_hash.substring(0, 16)}...
                            </span>
                          </div>
                        </div>

                        <div className="mt-3 pt-2 border-t border-slate-700/60 flex items-center justify-between text-xs">
                          <button
                            onClick={() => handleExportFHIRConsent(c.consent_id)}
                            className="text-indigo-400 hover:text-indigo-300 font-medium"
                          >
                            FHIR R4 Consent
                          </button>
                          {c.status === 'ACTIVE' && (
                            <button
                              onClick={() => handleRevokeConsent(c.consent_id)}
                              className="text-rose-400 hover:text-rose-300 font-medium"
                            >
                              Revoke Directive
                            </button>
                          )}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Consent Policy Simulator */}
              <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-6 shadow-xl space-y-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>🧪</span> Interactive Consent Enforcement Simulator
                </h3>
                <p className="text-xs text-slate-400">Test how active patient directives evaluate against prospective clinical actions or data exports.</p>

                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <label className="text-slate-400 block mb-1">Resource Type</label>
                    <input
                      type="text"
                      value={testResourceType}
                      onChange={(e) => setTestResourceType(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Action</label>
                    <select
                      value={testAction}
                      onChange={(e) => setTestAction(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white"
                    >
                      <option value="READ">READ</option>
                      <option value="EXPORT">EXPORT</option>
                      <option value="UPDATE">UPDATE</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Purpose of Use</label>
                    <select
                      value={testPurpose}
                      onChange={(e) => setTestPurpose(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white"
                    >
                      <option value="TREATMENT">TREATMENT</option>
                      <option value="RESEARCH">RESEARCH</option>
                      <option value="THIRD_PARTY_SHARING">THIRD_PARTY_SHARING</option>
                      <option value="EMERGENCY_OVERRIDE">EMERGENCY_OVERRIDE</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Data Category</label>
                    <input
                      type="text"
                      value={testCategory}
                      onChange={(e) => setTestCategory(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                </div>

                <button
                  onClick={handleTestConsentVerification}
                  disabled={loading}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold shadow-md transition-all"
                  data-testid="verify-policy-btn"
                >
                  Evaluate Policy
                </button>

                {verificationResult && (
                  <div className={`p-4 rounded-xl text-xs border ${
                    verificationResult.is_permitted
                      ? 'bg-emerald-950/40 border-emerald-700 text-emerald-200'
                      : 'bg-rose-950/40 border-rose-700 text-rose-200'
                  }`}>
                    <div className="font-bold text-sm">
                      {verificationResult.is_permitted ? '✅ ACCESS PERMITTED' : '⛔ ACCESS DENIED / BLOCKED'}
                    </div>
                    <div className="mt-1">{verificationResult.reason}</div>
                    {verificationResult.matched_consent_id && (
                      <div className="mt-1 font-mono text-[11px]">Matched Directive: {verificationResult.matched_consent_id}</div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}

          {/* Grant Consent Modal */}
          {grantModalOpen && selectedPatient && (
            <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
                <h3 className="text-base font-bold text-white">Grant Patient Consent Directive</h3>
                <form onSubmit={handleGrantConsent} className="space-y-3 text-xs">
                  <div>
                    <label className="text-slate-400 block mb-1">Scope</label>
                    <select
                      value={newConsentScope}
                      onChange={(e) => setNewConsentScope(e.target.value as ConsentScope)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                    >
                      <option value="ALL_RECORDS">ALL_RECORDS</option>
                      <option value="RESEARCH_ONLY">RESEARCH_ONLY</option>
                      <option value="GENOMICS_ONLY">GENOMICS_ONLY</option>
                      <option value="BEHAVIORAL_HEALTH">BEHAVIORAL_HEALTH</option>
                      <option value="THIRD_PARTY_SHARING">THIRD_PARTY_SHARING</option>
                      <option value="RESTRICT_EXPORT">RESTRICT_EXPORT</option>
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-slate-400 block mb-1">Policy Rule</label>
                      <select
                        value={newConsentRule}
                        onChange={(e) => setNewConsentRule(e.target.value as ConsentPolicyRule)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                      >
                        <option value="PERMIT">PERMIT (Opt-In)</option>
                        <option value="DENY">DENY (Opt-Out)</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-1">Purpose of Use</label>
                      <input
                        type="text"
                        value={newConsentPurpose}
                        onChange={(e) => setNewConsentPurpose(e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-slate-400 block mb-1">Data Category</label>
                    <input
                      type="text"
                      value={newConsentCategory}
                      onChange={(e) => setNewConsentCategory(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-slate-400 block mb-1">Signer Name</label>
                      <input
                        type="text"
                        value={newConsentSigner}
                        placeholder={`${selectedPatient.first_name} ${selectedPatient.last_name}`}
                        onChange={(e) => setNewConsentSigner(e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                      />
                    </div>
                    <div>
                      <label className="text-slate-400 block mb-1">Signer Relationship</label>
                      <select
                        value={newConsentRelationship}
                        onChange={(e) => setNewConsentRelationship(e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                      >
                        <option value="SELF">SELF (Patient)</option>
                        <option value="GUARDIAN">GUARDIAN</option>
                        <option value="HEALTHCARE_PROXY">HEALTHCARE_PROXY</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex justify-end gap-2 pt-4">
                    <button
                      type="button"
                      onClick={() => setGrantModalOpen(false)}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={loading}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold"
                    >
                      Sign & Register
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: SECURITY THREAT & INCIDENT TRIAGE */}
      {activeTab === 'incidents' && (
        <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-white">Security Incidents & Anomaly Detections</h2>
              <p className="text-xs text-slate-400">Automated threat monitoring for cross-patient scanning, repeated auth errors, and abnormal exports</p>
            </div>
            <button
              onClick={handleRunSecurityScan}
              disabled={loading}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-xs font-semibold shadow-md transition-all flex items-center gap-1.5"
            >
              <span>⚡</span> Trigger Immediate Threat Scan
            </button>
          </div>

          {/* Incidents Table */}
          <div className="overflow-x-auto rounded-xl border border-slate-700">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/80 text-xs uppercase font-semibold text-slate-400">
                <tr>
                  <th className="px-4 py-3">Detected At</th>
                  <th className="px-4 py-3">Incident ID</th>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Event Type</th>
                  <th className="px-4 py-3">Description</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/60 bg-slate-800/40">
                {incidents.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                      No security incidents detected. System operating under normal parameters.
                    </td>
                  </tr>
                ) : (
                  incidents.map((inc) => (
                    <tr key={inc.incident_id} className="hover:bg-slate-700/40 transition-colors">
                      <td className="px-4 py-3 text-xs whitespace-nowrap text-slate-400">
                        {new Date(inc.detected_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-amber-300">{inc.incident_id}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          inc.severity === 'CRITICAL'
                            ? 'bg-rose-950 text-rose-300 border border-rose-800'
                            : inc.severity === 'HIGH'
                            ? 'bg-amber-950 text-amber-300 border border-amber-800'
                            : 'bg-sky-950 text-sky-300 border border-sky-800'
                        }`}>
                          {inc.severity}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                          inc.status === 'OPEN'
                            ? 'bg-rose-900/60 text-rose-200'
                            : inc.status === 'INVESTIGATING'
                            ? 'bg-amber-900/60 text-amber-200'
                            : 'bg-emerald-900/60 text-emerald-200'
                        }`}>
                          {inc.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-300 font-mono">{inc.event_type}</td>
                      <td className="px-4 py-3 text-xs text-slate-300 max-w-xs truncate">{inc.description}</td>
                      <td className="px-4 py-3 text-xs">
                        <button
                          onClick={() => {
                            setSelectedIncident(inc);
                            setTriageStatus(inc.status as IncidentStatus);
                            setTriageNotes(inc.resolution_notes || '');
                          }}
                          className="text-indigo-400 hover:text-indigo-300 font-medium"
                        >
                          Triage
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Incident Triage Modal */}
          {selectedIncident && (
            <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
                <h3 className="text-base font-bold text-white">Triage Security Incident ({selectedIncident.incident_id})</h3>
                <div className="text-xs space-y-2 text-slate-300 bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div><strong>Description:</strong> {selectedIncident.description}</div>
                  <div><strong>Event Type:</strong> {selectedIncident.event_type}</div>
                  <div><strong>Evidence:</strong> {JSON.stringify(selectedIncident.evidence_metadata)}</div>
                </div>

                <form onSubmit={handleUpdateIncident} className="space-y-3 text-xs">
                  <div>
                    <label className="text-slate-400 block mb-1">Status</label>
                    <select
                      value={triageStatus}
                      onChange={(e) => setTriageStatus(e.target.value as IncidentStatus)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                    >
                      <option value="OPEN">OPEN</option>
                      <option value="INVESTIGATING">INVESTIGATING</option>
                      <option value="RESOLVED">RESOLVED</option>
                      <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Resolution / Investigation Notes</label>
                    <textarea
                      rows={3}
                      value={triageNotes}
                      onChange={(e) => setTriageNotes(e.target.value)}
                      placeholder="Detail findings, interviews, or corrective actions taken..."
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setSelectedIncident(null)}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={loading}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold"
                    >
                      Save Triage
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: RETENTION SCHEDULES & LEGAL HOLDS */}
      {activeTab === 'governance' && (
        <div className="space-y-6">
          {/* Active Legal Holds */}
          <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-6 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-white">Active Legal & Clinical Holds</h2>
                <p className="text-xs text-slate-400">Strict retention overrides safeguarding clinical records from routine disposition</p>
              </div>
              <button
                onClick={() => setHoldModalOpen(true)}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-xs font-semibold shadow-md transition-all flex items-center gap-1.5"
                data-testid="place-hold-btn"
              >
                <span>🔒</span> Place Legal Hold
              </button>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-700">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-900/80 text-xs uppercase font-semibold text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Hold ID</th>
                    <th className="px-4 py-3">Patient Context</th>
                    <th className="px-4 py-3">Scope</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Reason</th>
                    <th className="px-4 py-3">Placed At</th>
                    <th className="px-4 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/60 bg-slate-800/40">
                  {legalHolds.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                        No active or historical legal holds on file.
                      </td>
                    </tr>
                  ) : (
                    legalHolds.map((h) => (
                      <tr key={h.hold_id} className="hover:bg-slate-700/40 transition-colors">
                        <td className="px-4 py-3 font-mono text-xs text-purple-300 font-bold">{h.hold_id}</td>
                        <td className="px-4 py-3 text-xs text-slate-300">{h.patient_id || 'Institutional Global'}</td>
                        <td className="px-4 py-3 text-xs text-slate-300">{h.scope_category}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            h.status === 'ACTIVE'
                              ? 'bg-purple-950 text-purple-300 border border-purple-800'
                              : 'bg-slate-900 text-slate-400'
                          }`}>
                            {h.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-300 max-w-xs truncate">{h.reason}</td>
                        <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">
                          {new Date(h.placed_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-3 text-xs">
                          {h.status === 'ACTIVE' && (
                            <button
                              onClick={() => handleReleaseLegalHold(h.hold_id)}
                              className="text-rose-400 hover:text-rose-300 font-medium"
                            >
                              Release Hold
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Retention Policies Schedule */}
          <div className="bg-slate-800/80 border border-slate-700 rounded-2xl p-6 shadow-xl space-y-4">
            <h2 className="text-lg font-bold text-white">Regulatory Data Retention Schedules</h2>
            <p className="text-xs text-slate-400">Statutory record retention policies enforced across clinical domains</p>

            <div className="overflow-x-auto rounded-xl border border-slate-700">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-900/80 text-xs uppercase font-semibold text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Policy Code</th>
                    <th className="px-4 py-3">Data Category</th>
                    <th className="px-4 py-3">Retention Period</th>
                    <th className="px-4 py-3">Expiry Action</th>
                    <th className="px-4 py-3">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/60 bg-slate-800/40">
                  {retentionPolicies.map((p) => (
                    <tr key={p.policy_code} className="hover:bg-slate-700/40 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs text-indigo-300 font-bold">{p.policy_code}</td>
                      <td className="px-4 py-3 text-xs text-slate-200">{p.data_category}</td>
                      <td className="px-4 py-3 text-xs font-semibold text-slate-300">
                        {p.retention_period_days === -1 ? 'Permanent' : `${Math.round(p.retention_period_days / 365)} Years (${p.retention_period_days} days)`}
                      </td>
                      <td className="px-4 py-3 text-xs text-amber-400 font-mono">{p.action_on_expiry}</td>
                      <td className="px-4 py-3 text-xs text-slate-400">{p.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Place Hold Modal */}
          {holdModalOpen && (
            <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
              <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl">
                <h3 className="text-base font-bold text-white">Place Legal / Clinical Hold</h3>
                <form onSubmit={handlePlaceLegalHold} className="space-y-3 text-xs">
                  <div>
                    <label className="text-slate-400 block mb-1">Target Patient</label>
                    <input
                      type="text"
                      disabled
                      value={selectedPatient ? `${selectedPatient.first_name} ${selectedPatient.last_name} (${selectedPatient.patient_id})` : 'Institutional Global Hold'}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-300"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Scope Category</label>
                    <select
                      value={newHoldScope}
                      onChange={(e) => setNewHoldScope(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                    >
                      <option value="ALL_RECORDS">ALL_RECORDS</option>
                      <option value="IMAGING_STUDIES">IMAGING_STUDIES</option>
                      <option value="GENOMICS">GENOMICS</option>
                      <option value="CLINICAL_ENCOUNTERS">CLINICAL_ENCOUNTERS</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Reason for Hold</label>
                    <input
                      type="text"
                      required
                      value={newHoldReason}
                      placeholder="e.g. Active litigation, pending clinical trial audit"
                      onChange={(e) => setNewHoldReason(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div>
                    <label className="text-slate-400 block mb-1">Additional Notes</label>
                    <textarea
                      rows={3}
                      value={newHoldNotes}
                      onChange={(e) => setNewHoldNotes(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setHoldModalOpen(false)}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={loading}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-xl font-semibold"
                    >
                      Enforce Hold
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
