// ==============================================================================
// MediGen AI - Vital Telemetry & CDS Alerting Workspace
// ==============================================================================

import React, { useEffect, useState, useCallback } from 'react';
import { vitalsApi } from '../../api/client';
import { ClinicalAlert, VitalSimulationProfile, VitalTelemetry } from '../../types';

interface VitalTelemetryWorkspaceProps {
  patientId?: string;
}

export const VitalTelemetryWorkspace: React.FC<VitalTelemetryWorkspaceProps> = ({
  patientId,
}) => {
  const [latestVital, setLatestVital] = useState<VitalTelemetry | null>(null);
  const [vitalsHistory, setVitalsHistory] = useState<VitalTelemetry[]>([]);
  const [alerts, setAlerts] = useState<ClinicalAlert[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [simProfile, setSimProfile] = useState<VitalSimulationProfile>('normal');
  const [alertFilter, setAlertFilter] = useState<string>('active');
  const [dismissingAlertId, setDismissingAlertId] = useState<string | null>(null);
  const [dismissReason, setDismissReason] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!patientId) {
      setLatestVital(null);
      setVitalsHistory([]);
      setAlerts([]);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const [latestRes, historyRes, alertsRes] = await Promise.all([
        vitalsApi.getLatest(patientId),
        vitalsApi.list(patientId, 0, 10),
        vitalsApi.listAlerts(patientId, alertFilter === 'all' ? undefined : alertFilter),
      ]);
      setLatestVital(latestRes);
      setVitalsHistory(historyRes.items);
      setAlerts(alertsRes.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load telemetry or alerts.');
    } finally {
      setIsLoading(false);
    }
  }, [patientId, alertFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSimulate = async () => {
    if (!patientId) return;
    setIsLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await vitalsApi.simulate(patientId, simProfile);
      setSuccessMsg(`Simulated ${simProfile.toUpperCase()} telemetry ingested successfully.`);
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to simulate vital telemetry.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAcknowledge = async (alertId: string) => {
    setError(null);
    try {
      await vitalsApi.acknowledgeAlert(alertId);
      setSuccessMsg('Alert acknowledged.');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to acknowledge alert.');
    }
  };

  const handleDismiss = async (alertId: string) => {
    if (!dismissReason.trim() || dismissReason.trim().length < 3) {
      setError('Please provide a clinical reason for dismissal (minimum 3 characters).');
      return;
    }
    setError(null);
    try {
      await vitalsApi.dismissAlert(alertId, dismissReason.trim());
      setDismissingAlertId(null);
      setDismissReason('');
      setSuccessMsg('Alert dismissed with clinical justification.');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to dismiss alert.');
    }
  };

  // Helper for physiological status color
  const getSpo2Color = (val?: number) => {
    if (!val) return 'var(--text-muted)';
    if (val < 90) return '#ef4444';
    if (val < 94) return '#f59e0b';
    return '#10b981';
  };

  const getHrColor = (val?: number) => {
    if (!val) return 'var(--text-muted)';
    if (val > 140 || val < 40) return '#ef4444';
    if (val > 100 || val < 50) return '#f59e0b';
    return '#10b981';
  };

  const getBpColor = (sbp?: number, dbp?: number) => {
    if (!sbp || !dbp) return 'var(--text-muted)';
    if (sbp >= 180 || dbp >= 120 || sbp < 85) return '#ef4444';
    if (sbp >= 140 || dbp >= 90 || sbp < 90) return '#f59e0b';
    return '#10b981';
  };

  const getSeverityBadgeClass = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'badge-danger';
      case 'HIGH':
        return 'badge-warning';
      case 'MODERATE':
        return 'badge-info';
      default:
        return 'badge-secondary';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%', overflowY: 'auto' }}>
      {/* Top: Header & Telemetry Simulator Controls */}
      <div className="glass-panel" style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>💓</span> Real-Time Vital Telemetry & CDS Alerting
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Continuous physiological parameter ingestion & automated clinical rule evaluation
          </span>
        </div>

        {patientId && (
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <select
              className="form-select"
              value={simProfile}
              onChange={(e) => setSimProfile(e.target.value as VitalSimulationProfile)}
              style={{ fontSize: '0.8125rem' }}
            >
              <option value="normal">Normal Baseline (HR 72, BP 120/80, SpO2 98%)</option>
              <option value="hypoxic">Severe Hypoxia (SpO2 86%, RR 26)</option>
              <option value="hypertensive_crisis">Hypertensive Crisis (BP 195/128)</option>
              <option value="tachycardic">Severe Tachycardia (HR 152 bpm)</option>
              <option value="bradycardic">Severe Bradycardia (HR 36 bpm)</option>
            </select>
            <button
              className="btn btn-primary btn-sm"
              onClick={handleSimulate}
              disabled={isLoading}
            >
              ⚡ Ingest Simulation
            </button>
            <button className="btn btn-secondary btn-sm" onClick={loadData} disabled={isLoading}>
              ↻
            </button>
          </div>
        )}
      </div>

      {/* Mandatory Clinical Safety Disclaimer */}
      <div style={{ padding: '8px 14px', background: 'rgba(2, 132, 199, 0.08)', border: '1px solid rgba(2, 132, 199, 0.25)', borderRadius: 'var(--radius-sm)', color: '#38bdf8', fontSize: '0.75rem', lineHeight: '1.4' }}>
        ℹ️ <strong>Clinical Decision Support Alerting:</strong> Vital telemetry alerts are assistive notifications. All alert recommendations and critical notifications require clinician review before clinical action.
      </div>

      {error && (
        <div style={{ padding: '8px 12px', background: 'rgba(239,68,68,0.15)', border: '1px solid var(--danger-border)', borderRadius: '4px', color: '#fca5a5', fontSize: '0.8125rem' }}>
          ⚠️ {error}
        </div>
      )}

      {successMsg && (
        <div style={{ padding: '8px 12px', background: 'rgba(16,185,129,0.15)', border: '1px solid var(--success-border)', borderRadius: '4px', color: '#34d399', fontSize: '0.8125rem' }}>
          {successMsg}
        </div>
      )}

      {/* Grid: Left Live Vitals & Right CDS Alerts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* Left Column: Real-time Vital Parameter Cards */}
        <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
            Latest Physiological Snapshot {latestVital && `(${new Date(latestVital.measured_at).toLocaleTimeString()})`}
          </h4>

          {latestVital ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {/* SpO2 */}
              <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>SpO2 Saturation</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: getSpo2Color(latestVital.spo2_percent) }}>
                  {latestVital.spo2_percent != null ? `${latestVital.spo2_percent}%` : '--'}
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Target: &gt;94%</div>
              </div>

              {/* Heart Rate */}
              <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Heart Rate</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: getHrColor(latestVital.heart_rate) }}>
                  {latestVital.heart_rate != null ? `${latestVital.heart_rate} bpm` : '--'}
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Range: 50-100 bpm</div>
              </div>

              {/* Blood Pressure */}
              <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Blood Pressure</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 800, color: getBpColor(latestVital.systolic_bp, latestVital.diastolic_bp) }}>
                  {latestVital.systolic_bp != null && latestVital.diastolic_bp != null
                    ? `${latestVital.systolic_bp}/${latestVital.diastolic_bp}`
                    : '--'}
                  <span style={{ fontSize: '0.75rem', fontWeight: 400, marginLeft: '4px' }}>mmHg</span>
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Target: &lt;120/80 mmHg</div>
              </div>

              {/* Respiratory Rate */}
              <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Respiratory Rate</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                  {latestVital.respiratory_rate != null ? `${latestVital.respiratory_rate}` : '--'}
                  <span style={{ fontSize: '0.75rem', fontWeight: 400, marginLeft: '4px' }}>/min</span>
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Range: 12-20 /min</div>
              </div>

              {/* Temperature */}
              <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Temperature</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: latestVital.temperature_c && latestVital.temperature_c >= 38.5 ? '#f59e0b' : 'var(--text-primary)' }}>
                  {latestVital.temperature_c != null ? `${latestVital.temperature_c}°C` : '--'}
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Target: 36.5-37.5°C</div>
              </div>

              {/* Weight */}
              <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Weight</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                  {latestVital.weight_kg != null ? `${latestVital.weight_kg} kg` : '--'}
                </div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>Source: {latestVital.source}</div>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
              No telemetry readings recorded for this patient. Click <strong>⚡ Ingest Simulation</strong> to generate data.
            </div>
          )}

          {/* Recent Telemetry Readings Table */}
          <h5 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '12px' }}>
            Telemetry History Log
          </h5>
          <div style={{ maxHeight: '180px', overflowY: 'auto' }}>
            <table className="table" style={{ width: '100%', fontSize: '0.75rem' }}>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>SpO2</th>
                  <th>HR</th>
                  <th>BP</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {vitalsHistory.map((v) => (
                  <tr key={v.reading_id}>
                    <td>{new Date(v.measured_at).toLocaleTimeString()}</td>
                    <td style={{ color: getSpo2Color(v.spo2_percent), fontWeight: 600 }}>
                      {v.spo2_percent != null ? `${v.spo2_percent}%` : '--'}
                    </td>
                    <td style={{ color: getHrColor(v.heart_rate), fontWeight: 600 }}>
                      {v.heart_rate != null ? `${v.heart_rate}` : '--'}
                    </td>
                    <td style={{ color: getBpColor(v.systolic_bp, v.diastolic_bp), fontWeight: 600 }}>
                      {v.systolic_bp != null ? `${v.systolic_bp}/${v.diastolic_bp}` : '--'}
                    </td>
                    <td><span className="badge badge-secondary" style={{ fontSize: '0.6rem' }}>{v.source}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Column: Active Clinical Alerts & Actions */}
        <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>⚠️</span> CDS Alert Stack ({alerts.length})
            </h4>
            <div style={{ display: 'flex', gap: '6px' }}>
              {(['active', 'acknowledged', 'dismissed', 'all'] as const).map((st) => (
                <button
                  key={st}
                  className={`btn btn-sm ${alertFilter === st ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setAlertFilter(st)}
                  style={{ fontSize: '0.7rem', textTransform: 'capitalize', padding: '2px 8px' }}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', maxHeight: '420px' }}>
            {alerts.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                ✅ No {alertFilter !== 'all' ? alertFilter : ''} clinical alerts active for this patient.
              </div>
            ) : (
              alerts.map((alert) => (
                <div
                  key={alert.alert_id}
                  style={{
                    padding: '12px',
                    borderRadius: 'var(--radius-sm)',
                    background: alert.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.12)' : 'rgba(245, 158, 11, 0.08)',
                    border: alert.severity === 'CRITICAL' ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid rgba(245, 158, 11, 0.3)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <span className={`badge ${getSeverityBadgeClass(alert.severity)}`} style={{ fontSize: '0.65rem' }}>
                        {alert.severity}
                      </span>
                      <strong style={{ fontSize: '0.8125rem', color: 'var(--text-primary)' }}>
                        {alert.title}
                      </strong>
                    </div>
                    {alert.recurrence_count > 1 && (
                      <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>
                        🔁 x{alert.recurrence_count}
                      </span>
                    )}
                  </div>

                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.4', margin: 0 }}>
                    {alert.explanation}
                  </p>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    <span>Triggered: {new Date(alert.last_triggered_at).toLocaleTimeString()}</span>
                    <span>Status: <strong style={{ textTransform: 'uppercase' }}>{alert.status}</strong></span>
                  </div>

                  {/* Actions for Active Alerts */}
                  {alert.status === 'active' && (
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '6px' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                        onClick={() => handleAcknowledge(alert.alert_id)}
                      >
                        ✓ Acknowledge
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                        onClick={() => setDismissingAlertId(alert.alert_id)}
                      >
                        ✕ Dismiss
                      </button>
                    </div>
                  )}

                  {/* Dismiss Reason Form */}
                  {dismissingAlertId === alert.alert_id && (
                    <div style={{ marginTop: '8px', padding: '8px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="Mandatory clinical justification for dismissal..."
                        value={dismissReason}
                        onChange={(e) => setDismissReason(e.target.value)}
                        style={{ fontSize: '0.75rem' }}
                      />
                      <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '0.65rem', padding: '2px 6px' }}
                          onClick={() => { setDismissingAlertId(null); setDismissReason(''); }}
                        >
                          Cancel
                        </button>
                        <button
                          className="btn btn-primary btn-sm"
                          style={{ fontSize: '0.65rem', padding: '2px 6px' }}
                          onClick={() => handleDismiss(alert.alert_id)}
                        >
                          Confirm Dismissal
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
