import React, { useState, useEffect, useCallback } from 'react';
import { transitionsApi } from '../../api/client';
import {
  ClinicalHandoff,
  DischargeProtocol,
  HandoffFramework,
  HandoffType,
  DischargeDisposition,
  User,
} from '../../types';

interface TransitionsWorkspaceProps {
  patientId?: string;
  currentUser: User | null;
}

export const TransitionsWorkspace: React.FC<TransitionsWorkspaceProps> = ({
  patientId,
  currentUser,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'handoffs' | 'discharge'>('handoffs');
  const [handoffs, setHandoffs] = useState<ClinicalHandoff[]>([]);
  const [selectedHandoff, setSelectedHandoff] = useState<ClinicalHandoff | null>(null);
  const [dischargeProtocols, setDischargeProtocols] = useState<DischargeProtocol[]>([]);
  const [selectedDischarge, setSelectedDischarge] = useState<DischargeProtocol | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modals & Synthesis State
  const [showHandoffModal, setShowHandoffModal] = useState<boolean>(false);
  const [showAckModal, setShowAckModal] = useState<boolean>(false);
  const [showDischargeModal, setShowDischargeModal] = useState<boolean>(false);
  const [showSignoffModal, setShowSignoffModal] = useState<boolean>(false);
  const [synthesizing, setSynthesizing] = useState<boolean>(false);

  // New Handoff form
  const [targetFramework, setTargetFramework] = useState<HandoffFramework>('ipass');
  const [targetHandoffType, setTargetHandoffType] = useState<HandoffType>('shift_change');
  const [handoffCustomContext, setHandoffCustomContext] = useState<string>('');
  const [ackNotes, setAckNotes] = useState<string>('');

  // New Discharge form
  const [targetDisposition, setTargetDisposition] = useState<DischargeDisposition>('home_self_care');
  const [dischargeCustomInstructions, setDischargeCustomInstructions] = useState<string>('');
  const [signoffRole, setSignoffRole] = useState<string>('attending_physician');
  const [signoffNotes, setSignoffNotes] = useState<string>('');

  const loadData = useCallback(async () => {
    if (!patientId) return;
    try {
      setLoading(true);
      setError(null);
      const [hList, dList] = await Promise.all([
        transitionsApi.listHandoffs(patientId),
        transitionsApi.listDischargeProtocols(patientId),
      ]);
      setHandoffs(hList.items);
      if (hList.items.length > 0) setSelectedHandoff(hList.items[0]);
      setDischargeProtocols(dList.items);
      if (dList.items.length > 0) setSelectedDischarge(dList.items[0]);
    } catch (err: any) {
      setError(err?.message || 'Failed to load transitions of care and discharge data.');
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Trigger AI Handoff Synthesis
  const handleSynthesizeHandoff = async () => {
    if (!patientId) return;
    try {
      setSynthesizing(true);
      const created = await transitionsApi.synthesizeHandoff(patientId, {
        framework: targetFramework,
        handoff_type: targetHandoffType,
        custom_context: handoffCustomContext || undefined,
      });
      setShowHandoffModal(false);
      setHandoffCustomContext('');
      setSelectedHandoff(created);
      await loadData();
    } catch (err: any) {
      alert(err?.message || 'Failed to synthesize handoff');
    } finally {
      setSynthesizing(false);
    }
  };

  // Trigger Handoff Acknowledgment
  const handleAcknowledgeHandoff = async () => {
    if (!selectedHandoff) return;
    try {
      setSynthesizing(true);
      const updated = await transitionsApi.acknowledgeHandoff(selectedHandoff.handoff_id, ackNotes);
      setShowAckModal(false);
      setAckNotes('');
      setSelectedHandoff(updated);
      await loadData();
    } catch (err: any) {
      alert(err?.message || 'Failed to acknowledge handoff');
    } finally {
      setSynthesizing(false);
    }
  };

  // Trigger AI Discharge Protocol Synthesis
  const handleSynthesizeDischarge = async () => {
    if (!patientId) return;
    try {
      setSynthesizing(true);
      const created = await transitionsApi.synthesizeDischargeProtocol(patientId, {
        disposition: targetDisposition,
        custom_instructions: dischargeCustomInstructions || undefined,
      });
      setShowDischargeModal(false);
      setDischargeCustomInstructions('');
      setSelectedDischarge(created);
      await loadData();
    } catch (err: any) {
      alert(err?.message || 'Failed to synthesize discharge protocol');
    } finally {
      setSynthesizing(false);
    }
  };

  // Trigger Signoff
  const handleSignoffDischarge = async () => {
    if (!selectedDischarge) return;
    try {
      setSynthesizing(true);
      const updated = await transitionsApi.signoffDischargeProtocol(
        selectedDischarge.discharge_id,
        signoffRole,
        signoffNotes || undefined
      );
      setShowSignoffModal(false);
      setSignoffNotes('');
      setSelectedDischarge(updated);
      await loadData();
    } catch (err: any) {
      alert(err?.message || 'Failed to sign off discharge protocol');
    } finally {
      setSynthesizing(false);
    }
  };

  const getSeverityColor = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'unstable':
        return '#ef4444';
      case 'watcher':
        return '#eab308';
      case 'stable':
      default:
        return '#10b981';
    }
  };

  const getReconStatusBadge = (st: string) => {
    switch (st.toLowerCase()) {
      case 'continued':
        return { bg: 'rgba(16, 185, 129, 0.2)', color: '#10b981' };
      case 'dosage_adjusted':
        return { bg: 'rgba(234, 179, 8, 0.2)', color: '#eab308' };
      case 'newly_prescribed':
        return { bg: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa' };
      case 'discontinued':
        return { bg: 'rgba(239, 68, 68, 0.2)', color: '#ef4444' };
      default:
        return { bg: 'rgba(148, 163, 184, 0.2)', color: '#94a3b8' };
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%', height: '100%' }}>
      {/* Header & Sub-Tabs */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          background: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(16px)',
          padding: '1.25rem 1.5rem',
          borderRadius: '16px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: '1.5rem', color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>🔄</span> Clinical Transitions of Care & Discharge
          </h2>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: '#94a3b8' }}>
            Structured I-PASS / SBAR shift handovers, medication reconciliation, and multi-disciplinary discharge synthesis.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <div style={{ display: 'flex', background: '#1e293b', padding: '0.25rem', borderRadius: '8px' }}>
            <button
              onClick={() => setActiveSubTab('handoffs')}
              style={{
                padding: '0.4rem 0.8rem',
                borderRadius: '6px',
                border: 'none',
                background: activeSubTab === 'handoffs' ? '#3b82f6' : 'transparent',
                color: '#fff',
                fontWeight: 600,
                fontSize: '0.8rem',
                cursor: 'pointer',
              }}
            >
              📋 Clinical Handoffs ({handoffs.length})
            </button>
            <button
              onClick={() => setActiveSubTab('discharge')}
              style={{
                padding: '0.4rem 0.8rem',
                borderRadius: '6px',
                border: 'none',
                background: activeSubTab === 'discharge' ? '#3b82f6' : 'transparent',
                color: '#fff',
                fontWeight: 600,
                fontSize: '0.8rem',
                cursor: 'pointer',
              }}
            >
              🏥 Discharge Protocols ({dischargeProtocols.length})
            </button>
          </div>

          {activeSubTab === 'handoffs' ? (
            <button
              onClick={() => setShowHandoffModal(true)}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '8px',
                background: '#8b5cf6',
                color: '#fff',
                border: 'none',
                fontWeight: 600,
                fontSize: '0.85rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
              }}
            >
              <span>⚡</span> Synthesize AI Handoff
            </button>
          ) : (
            <button
              onClick={() => setShowDischargeModal(true)}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '8px',
                background: '#10b981',
                color: '#fff',
                border: 'none',
                fontWeight: 600,
                fontSize: '0.85rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.35rem',
              }}
            >
              <span>⚡</span> Synthesize AI Discharge
            </button>
          )}
        </div>
      </div>

      {error && (
        <div style={{ padding: '1rem', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', border: '1px solid #ef4444' }}>
          {error}
        </div>
      )}

      {/* Main Content Area */}
      {loading && !selectedHandoff && !selectedDischarge ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>Loading transition records...</div>
      ) : activeSubTab === 'handoffs' ? (
        /* ================= CLINICAL HANDOFFS VIEW ================= */
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '1.25rem', height: 'calc(100vh - 280px)', minHeight: '500px' }}>
          {/* Left Column: Handoff List */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              backdropFilter: 'blur(12px)',
              padding: '1rem',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem', color: '#f8fafc' }}>
              Shift & Transfer Handoffs
            </h3>
            {handoffs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8', fontSize: '0.85rem' }}>
                No handoffs created for this patient.
              </div>
            ) : (
              handoffs.map((h) => (
                <div
                  key={h.id}
                  onClick={() => setSelectedHandoff(h)}
                  style={{
                    padding: '0.75rem',
                    borderRadius: '10px',
                    background: selectedHandoff?.id === h.id ? '#1e293b' : 'rgba(30, 41, 59, 0.4)',
                    border: selectedHandoff?.id === h.id ? '1px solid #3b82f6' : '1px solid rgba(255, 255, 255, 0.05)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.35rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#60a5fa' }}>
                      {h.framework.toUpperCase()}
                    </span>
                    <span
                      style={{
                        padding: '0.15rem 0.45rem',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        background: `${getSeverityColor(h.illness_severity)}20`,
                        color: getSeverityColor(h.illness_severity),
                        border: `1px solid ${getSeverityColor(h.illness_severity)}50`,
                      }}
                    >
                      {h.illness_severity.toUpperCase()}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'capitalize' }}>
                    {h.handoff_type.replace('_', ' ')} • {new Date(h.created_at).toLocaleDateString()}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.25rem' }}>
                    <span style={{ fontSize: '0.7rem', color: h.status === 'acknowledged' ? '#10b981' : '#f59e0b' }}>
                      ● {h.status.toUpperCase()}
                    </span>
                    {h.is_ai_generated && (
                      <span style={{ fontSize: '0.65rem', color: '#8b5cf6' }}>⚡ AI Draft</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Right Column: Selected Handoff Details */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.65)',
              backdropFilter: 'blur(16px)',
              padding: '1.5rem',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem',
            }}
          >
            {selectedHandoff ? (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '1rem' }}>
                  <div>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc' }}>
                        {selectedHandoff.framework.toUpperCase()} Handoff Protocol
                      </h3>
                      <span
                        style={{
                          padding: '0.2rem 0.5rem',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          background: `${getSeverityColor(selectedHandoff.illness_severity)}25`,
                          color: getSeverityColor(selectedHandoff.illness_severity),
                        }}
                      >
                        {selectedHandoff.illness_severity.toUpperCase()}
                      </span>
                    </div>
                    <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
                      ID: {selectedHandoff.handoff_id} • Context: {selectedHandoff.handoff_type.replace('_', ' ')}
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    {selectedHandoff.status !== 'acknowledged' && (
                      <button
                        onClick={() => setShowAckModal(true)}
                        style={{
                          padding: '0.4rem 0.8rem',
                          borderRadius: '8px',
                          background: '#10b981',
                          color: '#fff',
                          border: 'none',
                          fontSize: '0.8rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        🤝 Acknowledge & Read Back
                      </button>
                    )}
                  </div>
                </div>

                {/* Narrative Summary */}
                <div>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: '#cbd5e1' }}>
                    {selectedHandoff.framework === 'sbar' ? 'SBAR Overview' : 'Patient Summary'}
                  </h4>
                  <div
                    style={{
                      background: 'rgba(30, 41, 59, 0.6)',
                      padding: '1rem',
                      borderRadius: '10px',
                      color: '#f8fafc',
                      fontSize: '0.875rem',
                      lineHeight: '1.5',
                      whiteSpace: 'pre-wrap',
                      border: '1px solid rgba(255, 255, 255, 0.05)',
                    }}
                  >
                    {selectedHandoff.summary}
                  </div>
                </div>

                {/* Action Items Checklist */}
                <div>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: '#cbd5e1' }}>
                    Pending Action Items ({(selectedHandoff.action_items_json || []).length})
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {(selectedHandoff.action_items_json || []).map((act, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: '#1e293b',
                          padding: '0.6rem 0.8rem',
                          borderRadius: '8px',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          borderLeft: act.priority === 'STAT' ? '4px solid #ef4444' : '4px solid #3b82f6',
                        }}
                      >
                        <div style={{ fontSize: '0.85rem', color: '#f8fafc' }}>
                          <span style={{ color: '#94a3b8', marginRight: '0.5rem', fontFamily: 'monospace' }}>[{act.item_id}]</span>
                          {act.task_description}
                        </div>
                        <span style={{ fontSize: '0.75rem', color: act.priority === 'STAT' ? '#ef4444' : '#60a5fa', fontWeight: 600 }}>
                          {act.priority} • {act.role_required}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Contingency Plans */}
                <div>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: '#cbd5e1' }}>
                    Situational Awareness & Contingency Guidelines
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {(selectedHandoff.situational_awareness_json || []).map((ctg, idx) => (
                      <div
                        key={idx}
                        style={{
                          background: 'rgba(234, 179, 8, 0.08)',
                          border: '1px solid rgba(234, 179, 8, 0.25)',
                          padding: '0.6rem 0.8rem',
                          borderRadius: '8px',
                        }}
                      >
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#eab308' }}>
                          ⚡ Trigger: {ctg.trigger_condition}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '0.25rem' }}>
                          Action: {ctg.immediate_action}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
                          Escalation: {ctg.escalation_contact}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Receiver Synthesis & Read-back */}
                {selectedHandoff.synthesis_notes && (
                  <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '0.75rem 1rem', borderRadius: '10px' }}>
                    <strong style={{ fontSize: '0.85rem', color: '#10b981' }}>✓ Receiver Acknowledgment & Synthesis</strong>
                    <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: '#cbd5e1' }}>
                      {selectedHandoff.synthesis_notes}
                    </p>
                  </div>
                )}
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                Select a clinical handoff to view full details.
              </div>
            )}
          </div>
        </div>
      ) : (
        /* ================= DISCHARGE PROTOCOLS VIEW ================= */
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '1.25rem', height: 'calc(100vh - 280px)', minHeight: '500px' }}>
          {/* Left Column: Discharge List */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              backdropFilter: 'blur(12px)',
              padding: '1rem',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
            }}
          >
            <h3 style={{ margin: '0 0 0.5rem', fontSize: '1rem', color: '#f8fafc' }}>
              Discharge Packages
            </h3>
            {dischargeProtocols.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#94a3b8', fontSize: '0.85rem' }}>
                No discharge protocols initiated.
              </div>
            ) : (
              dischargeProtocols.map((d) => (
                <div
                  key={d.id}
                  onClick={() => setSelectedDischarge(d)}
                  style={{
                    padding: '0.75rem',
                    borderRadius: '10px',
                    background: selectedDischarge?.id === d.id ? '#1e293b' : 'rgba(30, 41, 59, 0.4)',
                    border: selectedDischarge?.id === d.id ? '1px solid #10b981' : '1px solid rgba(255, 255, 255, 0.05)',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.35rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.85rem', color: '#10b981' }}>
                      {d.primary_discharge_diagnosis}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'capitalize' }}>
                    To: {d.disposition.replace('_', ' ')}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.25rem' }}>
                    <span style={{ fontSize: '0.7rem', color: d.status === 'ready_for_discharge' ? '#10b981' : '#f59e0b' }}>
                      ● {d.status.replace('_', ' ').toUpperCase()}
                    </span>
                    {d.is_ai_generated && (
                      <span style={{ fontSize: '0.65rem', color: '#8b5cf6' }}>⚡ AI Draft</span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Right Column: Selected Discharge Details */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.65)',
              backdropFilter: 'blur(16px)',
              padding: '1.5rem',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '1.25rem',
            }}
          >
            {selectedDischarge ? (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid rgba(255, 255, 255, 0.08)', paddingBottom: '1rem' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.25rem', color: '#f8fafc' }}>
                      Discharge Protocol: {selectedDischarge.primary_discharge_diagnosis}
                    </h3>
                    <p style={{ margin: '0.25rem 0 0', fontSize: '0.8rem', color: '#94a3b8' }}>
                      Disposition: <strong>{selectedDischarge.disposition.replace('_', ' ').toUpperCase()}</strong> • Status: <strong>{selectedDischarge.status.replace('_', ' ').toUpperCase()}</strong>
                    </p>
                  </div>

                  <button
                    onClick={() => setShowSignoffModal(true)}
                    style={{
                      padding: '0.4rem 0.8rem',
                      borderRadius: '8px',
                      background: '#3b82f6',
                      color: '#fff',
                      border: 'none',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    ✍️ Signoff & Review
                  </button>
                </div>

                {/* Hospital Course Narrative */}
                <div>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: '#cbd5e1' }}>
                    Hospital Course Summary
                  </h4>
                  <div
                    style={{
                      background: 'rgba(30, 41, 59, 0.6)',
                      padding: '1rem',
                      borderRadius: '10px',
                      color: '#f8fafc',
                      fontSize: '0.875rem',
                      lineHeight: '1.5',
                      border: '1px solid rgba(255, 255, 255, 0.05)',
                    }}
                  >
                    {selectedDischarge.hospital_course_summary}
                  </div>
                </div>

                {/* Medication Reconciliation Matrix */}
                <div>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.9rem', color: '#cbd5e1' }}>
                    Discharge Medication Reconciliation Matrix ({(selectedDischarge.medication_reconciliation_json || []).length})
                  </h4>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8' }}>
                          <th style={{ padding: '0.5rem' }}>Medication & Dose</th>
                          <th style={{ padding: '0.5rem' }}>Frequency</th>
                          <th style={{ padding: '0.5rem' }}>Status</th>
                          <th style={{ padding: '0.5rem' }}>Clinical Rationale</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(selectedDischarge.medication_reconciliation_json || []).map((med, idx) => {
                          const badge = getReconStatusBadge(med.reconciliation_status);
                          return (
                            <tr key={idx} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)', color: '#f8fafc' }}>
                              <td style={{ padding: '0.5rem', fontWeight: 600 }}>{med.medication_name} ({med.dose})</td>
                              <td style={{ padding: '0.5rem', color: '#cbd5e1' }}>{med.frequency}</td>
                              <td style={{ padding: '0.5rem' }}>
                                <span style={{ padding: '0.2rem 0.45rem', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 700, background: badge.bg, color: badge.color }}>
                                  {med.reconciliation_status.replace('_', ' ').toUpperCase()}
                                </span>
                              </td>
                              <td style={{ padding: '0.5rem', color: '#94a3b8' }}>{med.clinical_rationale}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Follow-up & Pending Tests */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div>
                    <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                      Follow-up Appointments
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      {(selectedDischarge.followup_instructions_json || []).map((f, idx) => (
                        <div key={idx} style={{ background: '#1e293b', padding: '0.5rem 0.75rem', borderRadius: '6px', fontSize: '0.8rem' }}>
                          <strong style={{ color: '#60a5fa' }}>{f.provider_or_specialty}</strong> — {f.timeframe}
                          <div style={{ color: '#94a3b8', fontSize: '0.75rem', marginTop: '0.15rem' }}>{f.purpose}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', color: '#cbd5e1' }}>
                      Pending Lab & Diagnostic Tests
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                      {(selectedDischarge.pending_tests_json || []).map((p, idx) => (
                        <div key={idx} style={{ background: '#1e293b', padding: '0.5rem 0.75rem', borderRadius: '6px', fontSize: '0.8rem' }}>
                          <strong style={{ color: '#f59e0b' }}>{p.test_name}</strong>
                          <div style={{ color: '#94a3b8', fontSize: '0.75rem', marginTop: '0.15rem' }}>{p.instructions}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Red Flag Warning Signs */}
                <div>
                  <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.85rem', color: '#ef4444' }}>
                    🚨 Emergency Warning Symptoms & Contingency Guidelines
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    {(selectedDischarge.warning_symptoms_json || []).map((w, idx) => (
                      <div key={idx} style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '0.5rem 0.75rem', borderRadius: '6px' }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#ef4444' }}>
                          [{w.urgency_level}] {w.symptom_title}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#cbd5e1', marginTop: '0.15rem' }}>
                          {w.action_instructions}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Signoff Status */}
                {selectedDischarge.signed_off_at && (
                  <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', padding: '0.75rem', borderRadius: '8px', fontSize: '0.8rem', color: '#10b981' }}>
                    ✓ Attending Physician Signoff Completed on {new Date(selectedDischarge.signed_off_at).toLocaleString()}
                  </div>
                )}
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>
                Select a discharge protocol to inspect instructions and medication reconciliation.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modal: Synthesize Handoff */}
      {showHandoffModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '16px', padding: '1.5rem', width: '90%', maxWidth: '450px', color: '#f8fafc' }}>
            <h3 style={{ margin: '0 0 1rem' }}>⚡ Synthesize Clinical Shift Handoff</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Handoff Framework</label>
                <select
                  value={targetFramework}
                  onChange={(e) => setTargetFramework(e.target.value as HandoffFramework)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                >
                  <option value="ipass">I-PASS (Illness Severity, Patient Summary, Actions, Contingencies)</option>
                  <option value="sbar">SBAR (Situation, Background, Assessment, Recommendation)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Transition Context</label>
                <select
                  value={targetHandoffType}
                  onChange={(e) => setTargetHandoffType(e.target.value as HandoffType)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                >
                  <option value="shift_change">Shift Change</option>
                  <option value="unit_transfer">Unit Transfer (e.g. ICU to Floor)</option>
                  <option value="discharge_transition">Discharge Transition</option>
                  <option value="service_consultation">Service Consultation</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Custom Handover Notes (optional)</label>
                <textarea
                  rows={3}
                  value={handoffCustomContext}
                  onChange={(e) => setHandoffCustomContext(e.target.value)}
                  placeholder="Special clinical nuances for incoming team..."
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => setShowHandoffModal(false)} style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#334155', color: '#fff', border: 'none' }}>
                  Cancel
                </button>
                <button type="button" disabled={synthesizing} onClick={handleSynthesizeHandoff} style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#8b5cf6', color: '#fff', border: 'none', fontWeight: 600 }}>
                  {synthesizing ? 'Synthesizing...' : 'Generate Handoff'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Acknowledge Handoff */}
      {showAckModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '16px', padding: '1.5rem', width: '90%', maxWidth: '450px', color: '#f8fafc' }}>
            <h3 style={{ margin: '0 0 1rem' }}>🤝 Receiver Read-Back & Acknowledgment</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Synthesis & Confirmation Notes</label>
                <textarea
                  required
                  rows={4}
                  value={ackNotes}
                  onChange={(e) => setAckNotes(e.target.value)}
                  placeholder="Confirm receipt, vital telemetry status, and agreement on action items..."
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => setShowAckModal(false)} style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#334155', color: '#fff', border: 'none' }}>
                  Cancel
                </button>
                <button type="button" disabled={synthesizing || !ackNotes} onClick={handleAcknowledgeHandoff} style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#10b981', color: '#fff', border: 'none', fontWeight: 600 }}>
                  {synthesizing ? 'Submitting...' : 'Confirm Acknowledgment'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Synthesize Discharge */}
      {showDischargeModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '16px', padding: '1.5rem', width: '90%', maxWidth: '450px', color: '#f8fafc' }}>
            <h3 style={{ margin: '0 0 1rem' }}>⚡ Synthesize Discharge Protocol</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Discharge Disposition</label>
                <select
                  value={targetDisposition}
                  onChange={(e) => setTargetDisposition(e.target.value as DischargeDisposition)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                >
                  <option value="home_self_care">Home with Self-Care</option>
                  <option value="home_health_services">Home with Home Health Services</option>
                  <option value="skilled_nursing_facility">Skilled Nursing Facility (SNF)</option>
                  <option value="rehab_facility">Inpatient Rehabilitation</option>
                  <option value="hospice">Hospice Care</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Custom Instructions (optional)</label>
                <textarea
                  rows={3}
                  value={dischargeCustomInstructions}
                  onChange={(e) => setDischargeCustomInstructions(e.target.value)}
                  placeholder="Wound dressing guidelines, weight threshold..."
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => setShowDischargeModal(false)} style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#334155', color: '#fff', border: 'none' }}>
                  Cancel
                </button>
                <button type="button" disabled={synthesizing} onClick={handleSynthesizeDischarge} style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#10b981', color: '#fff', border: 'none', fontWeight: 600 }}>
                  {synthesizing ? 'Synthesizing...' : 'Generate Discharge Package'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Signoff Discharge */}
      {showSignoffModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.15)', borderRadius: '16px', padding: '1.5rem', width: '90%', maxWidth: '450px', color: '#f8fafc' }}>
            <h3 style={{ margin: '0 0 1rem' }}>✍️ Multi-Disciplinary Signoff</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Signoff Role</label>
                <select
                  value={signoffRole}
                  onChange={(e) => setSignoffRole(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                >
                  <option value="attending_physician">Attending Physician (Final Discharge Clearance)</option>
                  <option value="registered_nurse">Registered Nurse (Discharge Teaching)</option>
                  <option value="clinical_pharmacist">Clinical Pharmacist (Medication Reconciliation)</option>
                </select>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Signoff Notes (optional)</label>
                <textarea
                  rows={3}
                  value={signoffNotes}
                  onChange={(e) => setSignoffNotes(e.target.value)}
                  placeholder="Validation comments..."
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => setShowSignoffModal(false)} style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#334155', color: '#fff', border: 'none' }}>
                  Cancel
                </button>
                <button type="button" disabled={synthesizing} onClick={handleSignoffDischarge} style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#3b82f6', color: '#fff', border: 'none', fontWeight: 600 }}>
                  {synthesizing ? 'Signing off...' : 'Complete Signoff'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
