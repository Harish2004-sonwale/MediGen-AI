// ==============================================================================
// MediGen AI - Clinical Decision Support (CDS) Safety Prescriber Modal
// ==============================================================================

import React, { useState } from 'react';
import { safetyApi } from '../../api/client';
import { ClinicalSafetyReport } from '../../types';

interface SafetyPrescriberModalProps {
  patientId?: string;
  isOpen: boolean;
  onClose: () => void;
}

export const SafetyPrescriberModal: React.FC<SafetyPrescriberModalProps> = ({
  patientId,
  isOpen,
  onClose,
}) => {
  const [candidateDrugsInput, setCandidateDrugsInput] = useState<string>('');
  const [activeConditionsInput, setActiveConditionsInput] = useState<string>('');
  const [report, setReport] = useState<ClinicalSafetyReport | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleRunSafetyCheck = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientId) {
      setError('Please select an active patient first.');
      return;
    }

    setIsLoading(true);
    setError(null);
    setReport(null);

    const candidateMedications = candidateDrugsInput
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const activeConditions = activeConditionsInput
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      const res = await safetyApi.checkSafety(
        patientId,
        candidateMedications.length > 0 ? candidateMedications : undefined,
        activeConditions.length > 0 ? activeConditions : undefined
      );
      setReport(res);
    } catch (err: any) {
      setError(err.message || 'Failed to execute clinical safety check.');
    } finally {
      setIsLoading(false);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return <span className="badge badge-danger">CRITICAL</span>;
      case 'HIGH':
        return <span className="badge badge-danger">HIGH RISK</span>;
      case 'MODERATE':
        return <span className="badge badge-warning">MODERATE</span>;
      case 'LOW':
        return <span className="badge badge-info">LOW RISK</span>;
      default:
        return <span className="badge">{severity}</span>;
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
        padding: '20px',
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '680px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          padding: '24px',
          boxShadow: 'var(--shadow-lg)',
        }}
      >
        {/* Modal Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: '#fbbf24' }}>🛡️</span>
              Clinical Decision Support (CDS) Safety Prescriber
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Evaluate drug-drug interactions, allergy conflicts, duplications & contraindications
            </span>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Prescription Input Form */}
        <form onSubmit={handleRunSafetyCheck} style={{ marginBottom: '16px' }}>
          <div className="form-group">
            <label className="form-label">Proposed / Candidate Medications</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Warfarin, Aspirin, Ibuprofen (comma-separated)"
              value={candidateDrugsInput}
              onChange={(e) => setCandidateDrugsInput(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Active Conditions / Diagnoses (Optional)</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Chronic Kidney Disease, Peptic Ulcer (comma-separated)"
              value={activeConditionsInput}
              onChange={(e) => setActiveConditionsInput(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={isLoading || !patientId}>
              {isLoading ? 'Analyzing Safety...' : 'Run Clinical Safety Check'}
            </button>
          </div>
        </form>

        {error && (
          <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.15)', border: '1px solid var(--danger-border)', borderRadius: 'var(--radius-sm)', color: '#fca5a5', fontSize: '0.8125rem', marginBottom: '16px' }}>
            ⚠️ {error}
          </div>
        )}

        {/* Safety Evaluation Results Report */}
        <div style={{ flex: 1, overflowY: 'auto', paddingRight: '4px' }}>
          {report && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {/* Overall Status Banner */}
              <div
                style={{
                  padding: '14px 16px',
                  borderRadius: 'var(--radius-sm)',
                  background: report.safe_to_proceed ? 'var(--success-bg)' : 'var(--danger-bg)',
                  border: report.safe_to_proceed ? '1px solid var(--success-border)' : '1px solid var(--danger-border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', color: report.safe_to_proceed ? '#34d399' : '#f87171' }}>
                    {report.safe_to_proceed ? '✅ Safe to Proceed' : '⚠️ Potential Safety Warnings Detected'}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    {report.summary}
                  </div>
                </div>
                <span className="badge" style={{ background: 'rgba(0,0,0,0.3)', color: '#ffffff' }}>
                  {report.checked_items} Items Evaluated
                </span>
              </div>

              {/* Alerts List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {report.alerts.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '16px', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                    No safety conflicts detected for the evaluated medications.
                  </div>
                ) : (
                  report.alerts.map((alert) => (
                    <div
                      key={alert.alert_id}
                      style={{
                        padding: '12px 14px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid var(--border-color)',
                        borderLeft: alert.severity === 'CRITICAL' || alert.severity === 'HIGH' ? '4px solid #ef4444' : '4px solid #f59e0b',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                          {alert.title}
                        </span>
                        {getSeverityBadge(alert.severity)}
                      </div>
                      <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '6px' }}>
                        {alert.explanation}
                      </p>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        <span>Medications: {alert.medications.join(', ')}</span>
                        <span>Provider: {alert.provider}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Mandatory CDS Disclaimer */}
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontStyle: 'italic', borderTop: '1px solid var(--border-color)', paddingTop: '10px' }}>
                ℹ️ {report.disclaimer}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
