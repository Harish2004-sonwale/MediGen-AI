import React, { useState, useEffect } from 'react';
import { usePatient } from '../../context/PatientContext';
import { useAuth } from '../../context/AuthContext';
import { trialsGovernanceApi } from '../../api/client';
import {
  MultiCenterStudySite,
  TrialProtocolDeviation,
  TrialCAPARecord,
  TrialIRBNotification,
  TrialPrescreenEvaluationResponse,
  TrialPrescreenEvaluationItem,
  MultiCenterTrialGovernanceSummary,
  DeviationCategory,
  DeviationSeverity,
  DeviationStatus,
  CAPARootCause,
  IRBSubmissionType,
} from '../../types';

export const TrialsGovernanceWorkspace: React.FC = () => {
  const { selectedPatient } = usePatient();
  const { user } = useAuth();

  const [activeTab, setActiveTab] = useState<'prescreen' | 'deviations' | 'capa' | 'irb' | 'network'>('prescreen');

  // Prescreening State
  const [prescreenData, setPrescreenData] = useState<TrialPrescreenEvaluationResponse | null>(null);
  const [selectedEvaluation, setSelectedEvaluation] = useState<TrialPrescreenEvaluationItem | null>(null);
  const [isPrescreening, setIsPrescreening] = useState<boolean>(false);

  // Deviations State
  const [deviations, setDeviations] = useState<TrialProtocolDeviation[]>([]);
  const [selectedDeviation, setSelectedDeviation] = useState<TrialProtocolDeviation | null>(null);
  const [severityFilter, setSeverityFilter] = useState<DeviationSeverity | ''>('');
  const [isReportingDeviation, setIsReportingDeviation] = useState<boolean>(false);

  // Deviation Form State
  const [devTrialId, setDevTrialId] = useState<number>(1);
  const [devCategory, setDevCategory] = useState<DeviationCategory>('investigational_product_dosing_error');
  const [devSeverity, setDevSeverity] = useState<DeviationSeverity>('critical');
  const [devDescription, setDevDescription] = useState<string>('');
  const [devSafetyImpact, setDevSafetyImpact] = useState<string>('');
  const [devDataIntegrityImpact, setDevDataIntegrityImpact] = useState<string>('');
  const [devRequiresIRB, setDevRequiresIRB] = useState<boolean>(true);

  // CAPA State
  const [isCreatingCAPA, setIsCreatingCAPA] = useState<boolean>(false);
  const [capaRootCause, setCapaRootCause] = useState<CAPARootCause>('staff_training_gap');
  const [capaAnalysis, setCapaAnalysis] = useState<string>('');
  const [capaCorrective, setCapaCorrective] = useState<string>('');
  const [capaPreventive, setCapaPreventive] = useState<string>('');
  const [capaTargetDate, setCapaTargetDate] = useState<string>('2026-09-30');

  // IRB Submission State
  const [isSubmittingIRB, setIsSubmittingIRB] = useState<boolean>(false);
  const [irbCommittee, setIrbCommittee] = useState<string>('Western Institutional Review Board (WIRB)');
  const [irbType, setIrbType] = useState<IRBSubmissionType>('prompt_safety_report_ind');
  const [irbRemarks, setIrbRemarks] = useState<string>('');
  const [irbResult, setIrbResult] = useState<TrialIRBNotification | null>(null);

  // Multi-Center Network State
  const [sites, setSites] = useState<MultiCenterStudySite[]>([]);
  const [networkSummary, setNetworkSummary] = useState<MultiCenterTrialGovernanceSummary | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (selectedPatient) {
      handlePrescreen();
    }
    loadDeviations();
    loadNetworkData();
  }, [selectedPatient]);

  const showNotification = (type: 'success' | 'error', text: string) => {
    setStatusMessage({ type, text });
    setTimeout(() => setStatusMessage(null), 6000);
  };

  const handlePrescreen = async () => {
    if (!selectedPatient) return;
    try {
      setIsPrescreening(true);
      const res = await trialsGovernanceApi.getPrescreening(selectedPatient.patient_id);
      setPrescreenData(res);
      if (res.evaluations && res.evaluations.length > 0) {
        setSelectedEvaluation(res.evaluations[0]);
      }
    } catch (err: any) {
      showNotification('error', `Prescreening failed: ${err?.message}`);
    } finally {
      setIsPrescreening(false);
    }
  };

  const loadDeviations = async () => {
    try {
      setIsLoading(true);
      const res = await trialsGovernanceApi.listDeviations({
        severity: severityFilter ? severityFilter : undefined,
      });
      setDeviations(res.deviations || []);
      if (res.deviations && res.deviations.length > 0 && !selectedDeviation) {
        setSelectedDeviation(res.deviations[0]);
      }
    } catch (err: any) {
      showNotification('error', `Failed to load deviations: ${err?.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const loadNetworkData = async () => {
    try {
      const sitesRes = await trialsGovernanceApi.listSites();
      setSites(sitesRes.sites || []);
      const summaryRes = await trialsGovernanceApi.getTrialSummary(1);
      setNetworkSummary(summaryRes);
    } catch (err: any) {
      // Ignored if trials not yet seeded
    }
  };

  const handleReportDeviationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!devDescription.trim()) {
      showNotification('error', 'Please enter a description for the protocol deviation.');
      return;
    }
    try {
      setIsLoading(true);
      const nowIso = new Date().toISOString();
      const res = await trialsGovernanceApi.reportDeviation({
        trial_id: devTrialId,
        patient_id: selectedPatient?.patient_id,
        deviation_category: devCategory,
        severity: devSeverity,
        description: devDescription.trim(),
        occurred_at: nowIso,
        discovered_at: nowIso,
        impact_on_patient_safety: devSafetyImpact.trim() || undefined,
        impact_on_data_integrity: devDataIntegrityImpact.trim() || undefined,
        requires_irb_submission: devRequiresIRB,
      });
      showNotification('success', `Deviation reported under ID: ${res.deviation_id}`);
      setIsReportingDeviation(false);
      setDevDescription('');
      setDevSafetyImpact('');
      setDevDataIntegrityImpact('');
      loadDeviations();
    } catch (err: any) {
      showNotification('error', `Failed to report deviation: ${err?.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateCAPASubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDeviation || !capaAnalysis.trim() || !capaCorrective.trim() || !capaPreventive.trim()) {
      showNotification('error', 'Please fill in all CAPA required analysis and action fields.');
      return;
    }
    try {
      setIsLoading(true);
      const res = await trialsGovernanceApi.createCAPA(selectedDeviation.id, {
        root_cause_category: capaRootCause,
        root_cause_analysis: capaAnalysis.trim(),
        corrective_action: capaCorrective.trim(),
        preventive_action: capaPreventive.trim(),
        assigned_owner_user_id: user?.id || 1,
        target_resolution_date: capaTargetDate,
      });
      showNotification('success', `CAPA plan created: ${res.capa_id}`);
      setIsCreatingCAPA(false);
      setCapaAnalysis('');
      setCapaCorrective('');
      setCapaPreventive('');
      loadDeviations();
    } catch (err: any) {
      showNotification('error', `Failed to assign CAPA: ${err?.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitIRBSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDeviation || !irbCommittee.trim()) {
      showNotification('error', 'Please specify the IRB Committee name.');
      return;
    }
    try {
      setIsLoading(true);
      const res = await trialsGovernanceApi.submitIRB(selectedDeviation.id, {
        irb_committee_name: irbCommittee.trim(),
        submission_type: irbType,
        custom_remarks: irbRemarks.trim() || undefined,
      });
      setIrbResult(res);
      showNotification('success', `IRB filing acknowledged: ${res.acknowledgement_reference}`);
      setIsSubmittingIRB(false);
      loadDeviations();
    } catch (err: any) {
      showNotification('error', `Failed to submit IRB notification: ${err?.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '16px', gap: '16px', overflowY: 'auto' }}>
      {/* Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Clinical Trials Governance, Precision Auto-Enrollment & Regulatory Auditing
          </h2>
          <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Multi-center study accrual tracking, real-time genomic trial matching, GCP protocol deviation governance, CAPA remediation, and IRB filings.
          </p>
        </div>
        {/* Navigation Tabs */}
        <div style={{ display: 'flex', background: 'var(--bg-secondary)', padding: '4px', borderRadius: '8px', gap: '4px' }}>
          <button
            id="tab-btn-prescreen"
            onClick={() => setActiveTab('prescreen')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              background: activeTab === 'prescreen' ? 'var(--primary-color, #2563eb)' : 'transparent',
              color: activeTab === 'prescreen' ? '#ffffff' : 'var(--text-secondary)',
            }}
          >
            🔬 Patient Prescreening
          </button>
          <button
            id="tab-btn-deviations"
            onClick={() => setActiveTab('deviations')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              background: activeTab === 'deviations' ? 'var(--primary-color, #2563eb)' : 'transparent',
              color: activeTab === 'deviations' ? '#ffffff' : 'var(--text-secondary)',
            }}
          >
            ⚖️ Protocol Deviations ({deviations.length})
          </button>
          <button
            id="tab-btn-network"
            onClick={() => setActiveTab('network')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              background: activeTab === 'network' ? 'var(--primary-color, #2563eb)' : 'transparent',
              color: activeTab === 'network' ? '#ffffff' : 'var(--text-secondary)',
            }}
          >
            🌐 Multi-Center Network Accrual
          </button>
        </div>
      </div>

      {/* Status Notifications */}
      {statusMessage && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '0.9rem',
            background: statusMessage.type === 'success' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            border: `1px solid ${statusMessage.type === 'success' ? '#22c55e' : '#ef4444'}`,
            color: statusMessage.type === 'success' ? '#16a34a' : '#dc2626',
          }}
        >
          {statusMessage.type === 'success' ? '✅' : '⚠️'} {statusMessage.text}
        </div>
      )}

      {/* Patient Required Banner */}
      {!selectedPatient && activeTab === 'prescreen' && (
        <div style={{ padding: '12px 16px', background: 'rgba(234, 179, 8, 0.15)', border: '1px solid #eab308', borderRadius: '8px', color: '#ca8a04', fontSize: '0.9rem' }}>
          ⚠️ Please select a patient to execute real-time genomic prescreening and eligibility matching across active trial protocols.
        </div>
      )}

      {/* TAB 1: PATIENT PRESCREENING & GENOMIC MATCHING */}
      {activeTab === 'prescreen' && (
        <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '16px', height: '100%', minHeight: '520px' }}>
          {/* Left: Matched Trials List */}
          <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '12px', display: 'flex', flexDirection: 'column', gap: '12px', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Active Protocol Matching</span>
              <button
                onClick={handlePrescreen}
                disabled={!selectedPatient || isPrescreening}
                style={{ padding: '4px 10px', fontSize: '0.75rem', borderRadius: '4px', background: 'var(--primary-color, #2563eb)', color: '#fff', cursor: 'pointer' }}
              >
                {isPrescreening ? 'Screening...' : '🔄 Rescreen'}
              </button>
            </div>

            {selectedPatient && (
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '8px', background: 'var(--bg-primary)', borderRadius: '6px' }}>
                Subject: <strong>{selectedPatient.first_name} {selectedPatient.last_name}</strong> ({selectedPatient.patient_id})
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', flex: 1 }}>
              {prescreenData?.evaluations.map((item) => {
                const isSelected = selectedEvaluation?.trial_id === item.trial_id;
                return (
                  <div
                    key={item.trial_id}
                    id={`trial-card-${item.trial_id}`}
                    onClick={() => setSelectedEvaluation(item)}
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      border: isSelected ? '1px solid var(--primary-color, #2563eb)' : '1px solid var(--border-color)',
                      background: isSelected ? 'rgba(37, 99, 235, 0.08)' : 'var(--bg-primary)',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{item.nct_number || `TRI-${item.trial_id}`}</span>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '12px',
                          background: item.is_eligible ? '#dcfce7' : '#fee2e2',
                          color: item.is_eligible ? '#15803d' : '#b91c1c',
                        }}
                      >
                        {item.is_eligible ? 'Eligible' : 'Disqualified'} ({item.eligibility_score}%)
                      </span>
                    </div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                      {item.title}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {item.disease_condition} • {item.phase.replace('_', ' ').toUpperCase()}
                    </div>
                  </div>
                );
              })}
              {(!prescreenData || prescreenData.evaluations.length === 0) && !isPrescreening && (
                <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  No active clinical trial matches found for current patient profile.
                </div>
              )}
            </div>
          </div>

          {/* Right: Detailed Criteria Breakdown */}
          <div style={{ background: 'var(--bg-secondary)', padding: '20px', borderRadius: '12px', display: 'flex', flexDirection: 'column', gap: '16px', border: '1px solid var(--border-color)' }}>
            {selectedEvaluation ? (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary-color, #2563eb)', textTransform: 'uppercase' }}>
                      {selectedEvaluation.phase.replace('_', ' ')} Trial Protocol
                    </span>
                    <h3 style={{ margin: '4px 0 6px 0', fontSize: '1.15rem', fontWeight: 700 }}>
                      {selectedEvaluation.title}
                    </h3>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      Target Condition: <strong>{selectedEvaluation.disease_condition}</strong>
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '1.4rem', fontWeight: 800, color: selectedEvaluation.is_eligible ? '#16a34a' : '#dc2626' }}>
                      {selectedEvaluation.eligibility_score}%
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {selectedEvaluation.matched_criteria_count} of {selectedEvaluation.total_criteria_count} Criteria Met
                    </div>
                  </div>
                </div>

                {/* Disqualifying Reasons Warning */}
                {selectedEvaluation.disqualifying_reasons.length > 0 && (
                  <div style={{ padding: '12px 16px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', borderRadius: '8px' }}>
                    <div style={{ fontWeight: 700, color: '#dc2626', fontSize: '0.85rem', marginBottom: '4px' }}>
                      Protocol Disqualification Factors:
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.8rem', color: '#b91c1c' }}>
                      {selectedEvaluation.disqualifying_reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Structured Criteria Table */}
                <div>
                  <h4 style={{ margin: '0 0 8px 0', fontSize: '0.9rem', fontWeight: 700 }}>
                    Inclusion & Exclusion Criteria Matrix:
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {selectedEvaluation.criteria_results.map((c) => (
                      <div
                        key={c.criterion_id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '10px 14px',
                          borderRadius: '6px',
                          background: 'var(--bg-primary)',
                          border: '1px solid var(--border-color)',
                          fontSize: '0.85rem',
                        }}
                      >
                        <div style={{ flex: 1, paddingRight: '16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span
                              style={{
                                fontSize: '0.7rem',
                                fontWeight: 700,
                                padding: '1px 6px',
                                borderRadius: '4px',
                                background: c.criterion_type === 'inclusion' ? '#e0f2fe' : '#fef3c7',
                                color: c.criterion_type === 'inclusion' ? '#0369a1' : '#92400e',
                              }}
                            >
                              {c.criterion_type.toUpperCase()}
                            </span>
                            <span style={{ fontWeight: 600 }}>{c.description}</span>
                          </div>
                          {c.patient_value && (
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                              Patient Data: <strong>{c.patient_value}</strong>
                            </div>
                          )}
                        </div>
                        <div>
                          <span
                            style={{
                              fontSize: '0.8rem',
                              fontWeight: 700,
                              padding: '3px 10px',
                              borderRadius: '12px',
                              background: c.is_met ? '#dcfce7' : '#fee2e2',
                              color: c.is_met ? '#15803d' : '#b91c1c',
                            }}
                          >
                            {c.is_met ? '✓ Satisfied' : '✗ Unmet'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)' }}>
                Select a trial from the left to view full criteria breakdown.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: PROTOCOL DEVIATIONS & NON-COMPLIANCE */}
      {activeTab === 'deviations' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
              <label style={{ fontSize: '0.85rem', fontWeight: 600 }}>Filter by Severity:</label>
              <select
                value={severityFilter}
                onChange={(e) => {
                  setSeverityFilter(e.target.value as DeviationSeverity | '');
                  loadDeviations();
                }}
                style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              >
                <option value="">All Severities</option>
                <option value="critical">Critical</option>
                <option value="major">Major</option>
                <option value="minor">Minor</option>
              </select>
            </div>
            <button
              id="btn-report-deviation-open"
              onClick={() => setIsReportingDeviation(true)}
              style={{ padding: '8px 16px', borderRadius: '6px', background: 'var(--primary-color, #2563eb)', color: '#fff', fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer' }}
            >
              ➕ Report Protocol Deviation
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '16px', minHeight: '480px' }}>
            {/* Left: Deviations List */}
            <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '12px', display: 'flex', flexDirection: 'column', gap: '10px', border: '1px solid var(--border-color)', overflowY: 'auto' }}>
              {deviations.map((dev) => {
                const isSelected = selectedDeviation?.id === dev.id;
                return (
                  <div
                    key={dev.id}
                    id={`dev-item-${dev.deviation_id}`}
                    onClick={() => setSelectedDeviation(dev)}
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      border: isSelected ? '1px solid var(--primary-color, #2563eb)' : '1px solid var(--border-color)',
                      background: isSelected ? 'rgba(37, 99, 235, 0.08)' : 'var(--bg-primary)',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{dev.deviation_id}</span>
                      <span
                        style={{
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '10px',
                          background: dev.severity === 'critical' ? '#fee2e2' : dev.severity === 'major' ? '#fef3c7' : '#e0f2fe',
                          color: dev.severity === 'critical' ? '#b91c1c' : dev.severity === 'major' ? '#92400e' : '#0369a1',
                        }}
                      >
                        {dev.severity.toUpperCase()}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                      {dev.deviation_category.replace(/_/g, ' ').toUpperCase()}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {dev.description}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                      <span>Status: <strong>{dev.status}</strong></span>
                      <span>{new Date(dev.occurred_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                );
              })}
              {deviations.length === 0 && (
                <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                  No protocol deviations found.
                </div>
              )}
            </div>

            {/* Right: Selected Deviation Governance Dashboard */}
            <div style={{ background: 'var(--bg-secondary)', padding: '20px', borderRadius: '12px', display: 'flex', flexDirection: 'column', gap: '16px', border: '1px solid var(--border-color)' }}>
              {selectedDeviation ? (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                    <div>
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary-color, #2563eb)' }}>
                        Protocol Non-Compliance Audit Record
                      </span>
                      <h3 style={{ margin: '4px 0 6px 0', fontSize: '1.2rem', fontWeight: 700 }}>
                        {selectedDeviation.deviation_id} • {selectedDeviation.deviation_category.replace(/_/g, ' ').toUpperCase()}
                      </h3>
                      <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                        Occurred: {new Date(selectedDeviation.occurred_at).toLocaleString()} | Discovered: {new Date(selectedDeviation.discovered_at).toLocaleString()}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        id="btn-open-capa-modal"
                        onClick={() => setIsCreatingCAPA(true)}
                        style={{ padding: '6px 14px', borderRadius: '6px', background: '#0284c7', color: '#fff', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
                      >
                        🛠️ Assign CAPA
                      </button>
                      <button
                        id="btn-open-irb-modal"
                        onClick={() => setIsSubmittingIRB(true)}
                        style={{ padding: '6px 14px', borderRadius: '6px', background: '#7c3aed', color: '#fff', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
                      >
                        🏛️ Submit to IRB
                      </button>
                    </div>
                  </div>

                  <div style={{ background: 'var(--bg-primary)', padding: '14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: '6px' }}>Incident Description:</div>
                    <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                      {selectedDeviation.description}
                    </p>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                      <div style={{ fontWeight: 700, fontSize: '0.8rem', color: '#b91c1c', marginBottom: '4px' }}>
                        🏥 Patient Safety Impact:
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                        {selectedDeviation.impact_on_patient_safety || 'None observed or reported.'}
                      </div>
                    </div>
                    <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                      <div style={{ fontWeight: 700, fontSize: '0.8rem', color: '#0369a1', marginBottom: '4px' }}>
                        📊 Data Integrity Impact:
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                        {selectedDeviation.impact_on_data_integrity || 'No evaluable data loss.'}
                      </div>
                    </div>
                  </div>

                  {/* Regulatory Status */}
                  <div style={{ padding: '12px', borderRadius: '8px', background: selectedDeviation.requires_irb_submission ? 'rgba(234, 179, 8, 0.1)' : 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                      IRB Regulatory Mandate:{' '}
                      <span style={{ color: selectedDeviation.requires_irb_submission ? '#ca8a04' : '#16a34a' }}>
                        {selectedDeviation.requires_irb_submission ? 'Mandatory Expedited IRB Filing' : 'Routine Annual Review'}
                      </span>
                    </div>
                    {selectedDeviation.irb_submitted_at && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                        Filing Submitted on: {new Date(selectedDeviation.irb_submitted_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)' }}>
                  Select a deviation to inspect GCP compliance notes and remediation plans.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: MULTI-CENTER NETWORK ACCRUAL */}
      {activeTab === 'network' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {networkSummary && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
              <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Total Target Accrual</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800 }}>{networkSummary.total_target_accrual} Subjects</div>
              </div>
              <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Current Enrolled</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--primary-color, #2563eb)' }}>
                  {networkSummary.total_enrolled} Subjects
                </div>
              </div>
              <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Network Accrual Rate</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: '#16a34a' }}>
                  {networkSummary.overall_accrual_rate}%
                </div>
              </div>
              <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Active Study Sites</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800 }}>{networkSummary.active_sites_count} Facilities</div>
              </div>
            </div>
          )}

          <div style={{ background: 'var(--bg-secondary)', padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.1rem', fontWeight: 700 }}>
              Participating Clinical Research Sites:
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {sites.map((site) => (
                <div
                  key={site.id}
                  style={{
                    padding: '14px',
                    borderRadius: '8px',
                    background: 'var(--bg-primary)',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                    gap: '12px',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{site.site_name}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                      Site ID: {site.site_id} {site.facility_id && `• Facility: ${site.facility_id}`} • IRB: {site.irb_approval_number || 'Pending'}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '0.9rem', fontWeight: 700 }}>
                        {site.current_enrolled} / {site.target_accrual} Enrolled
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        {Math.round((site.current_enrolled / site.target_accrual) * 100)}% Target Met
                      </div>
                    </div>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        padding: '3px 10px',
                        borderRadius: '12px',
                        background: site.site_status === 'active' ? '#dcfce7' : '#fee2e2',
                        color: site.site_status === 'active' ? '#15803d' : '#b91c1c',
                      }}
                    >
                      {site.site_status.toUpperCase()}
                    </span>
                  </div>
                </div>
              ))}
              {sites.length === 0 && (
                <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-secondary)' }}>
                  No participating study sites registered for this trial.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL: REPORT DEVIATION */}
      {isReportingDeviation && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '16px' }}>
          <div style={{ background: 'var(--bg-primary)', padding: '24px', borderRadius: '12px', width: '100%', maxWidth: '560px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>Report Protocol Deviation</h3>
            <form onSubmit={handleReportDeviationSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Category:</label>
                <select
                  value={devCategory}
                  onChange={(e) => setDevCategory(e.target.value as DeviationCategory)}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                >
                  <option value="investigational_product_dosing_error">Investigational Product Dosing Error</option>
                  <option value="informed_consent_variance">Informed Consent Variance</option>
                  <option value="inclusion_exclusion_breach">Inclusion/Exclusion Breach</option>
                  <option value="missed_study_visit">Missed Study Visit</option>
                  <option value="prohibited_medication">Prohibited Concomitant Medication</option>
                  <option value="laboratory_out_of_window">Laboratory Out of Window</option>
                  <option value="safety_reporting_delay">Safety Reporting Delay</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Severity:</label>
                <select
                  value={devSeverity}
                  onChange={(e) => setDevSeverity(e.target.value as DeviationSeverity)}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                >
                  <option value="critical">Critical (Immediate safety / major data integrity risk)</option>
                  <option value="major">Major (GCP variance with potential impact)</option>
                  <option value="minor">Minor (Administrative or procedural variance)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Incident Description:</label>
                <textarea
                  value={devDescription}
                  onChange={(e) => setDevDescription(e.target.value)}
                  placeholder="Detail the non-compliance incident, timeline, and individuals involved..."
                  rows={3}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Patient Safety Impact:</label>
                <input
                  type="text"
                  value={devSafetyImpact}
                  onChange={(e) => setDevSafetyImpact(e.target.value)}
                  placeholder="e.g. Vitals monitored; no adverse symptoms reported"
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  id="chk-dev-irb"
                  checked={devRequiresIRB}
                  onChange={(e) => setDevRequiresIRB(e.target.checked)}
                />
                <label htmlFor="chk-dev-irb" style={{ fontSize: '0.85rem', fontWeight: 600 }}>
                  Mandates Expedited IRB Regulatory Notification
                </label>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  onClick={() => setIsReportingDeviation(false)}
                  style={{ padding: '8px 16px', borderRadius: '6px', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-primary)', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  style={{ padding: '8px 16px', borderRadius: '6px', background: 'var(--primary-color, #2563eb)', color: '#fff', fontWeight: 700, cursor: 'pointer' }}
                >
                  {isLoading ? 'Submitting...' : 'Submit Deviation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: ASSIGN CAPA */}
      {isCreatingCAPA && selectedDeviation && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '16px' }}>
          <div style={{ background: 'var(--bg-primary)', padding: '24px', borderRadius: '12px', width: '100%', maxWidth: '560px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>
              Assign CAPA for {selectedDeviation.deviation_id}
            </h3>
            <form onSubmit={handleCreateCAPASubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Root Cause Category:</label>
                <select
                  value={capaRootCause}
                  onChange={(e) => setCapaRootCause(e.target.value as CAPARootCause)}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                >
                  <option value="investigator_oversight">Investigator Oversight</option>
                  <option value="patient_noncompliance">Patient Non-compliance</option>
                  <option value="pharmacy_dispensation_delay">Pharmacy Dispensation Delay</option>
                  <option value="laboratory_logistics_error">Laboratory Logistics Error</option>
                  <option value="staff_training_gap">Staff Training Gap</option>
                  <option value="protocol_ambiguity">Protocol Ambiguity</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Root Cause Analysis (5-Whys):</label>
                <textarea
                  value={capaAnalysis}
                  onChange={(e) => setCapaAnalysis(e.target.value)}
                  placeholder="Describe underlying root cause findings..."
                  rows={2}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Corrective Action (Immediate Fix):</label>
                <textarea
                  value={capaCorrective}
                  onChange={(e) => setCapaCorrective(e.target.value)}
                  placeholder="Immediate steps taken to correct the non-compliance..."
                  rows={2}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Preventive Action (Long-Term Prevention):</label>
                <textarea
                  value={capaPreventive}
                  onChange={(e) => setCapaPreventive(e.target.value)}
                  placeholder="Systemic process improvements and training..."
                  rows={2}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  onClick={() => setIsCreatingCAPA(false)}
                  style={{ padding: '8px 16px', borderRadius: '6px', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-primary)', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  style={{ padding: '8px 16px', borderRadius: '6px', background: '#0284c7', color: '#fff', fontWeight: 700, cursor: 'pointer' }}
                >
                  {isLoading ? 'Creating...' : 'Save CAPA'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: SUBMIT TO IRB */}
      {isSubmittingIRB && selectedDeviation && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '16px' }}>
          <div style={{ background: 'var(--bg-primary)', padding: '24px', borderRadius: '12px', width: '100%', maxWidth: '560px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>
              IRB Regulatory Submission for {selectedDeviation.deviation_id}
            </h3>
            <form onSubmit={handleSubmitIRBSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>IRB Committee Name:</label>
                <input
                  type="text"
                  value={irbCommittee}
                  onChange={(e) => setIrbCommittee(e.target.value)}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Submission Filing Type:</label>
                <select
                  value={irbType}
                  onChange={(e) => setIrbType(e.target.value as IRBSubmissionType)}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)' }}
                >
                  <option value="prompt_safety_report_ind">Prompt IND Safety Report (FDA 21 CFR 312)</option>
                  <option value="initial_deviation_report">Initial Protocol Deviation Notice</option>
                  <option value="follow_up_capa">Follow-up CAPA Resolution Report</option>
                  <option value="annual_continuing_review">Annual Continuing Review Report</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Remarks / Regulatory Cover Letter:</label>
                <textarea
                  value={irbRemarks}
                  onChange={(e) => setIrbRemarks(e.target.value)}
                  placeholder="Optional remarks for the Institutional Review Board..."
                  rows={2}
                  style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button
                  type="button"
                  onClick={() => setIsSubmittingIRB(false)}
                  style={{ padding: '8px 16px', borderRadius: '6px', background: 'transparent', border: '1px solid var(--border-color)', color: 'var(--text-primary)', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  style={{ padding: '8px 16px', borderRadius: '6px', background: '#7c3aed', color: '#fff', fontWeight: 700, cursor: 'pointer' }}
                >
                  {isLoading ? 'Filing...' : 'Submit Regulatory Filing'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
