import React, { useState, useEffect, useCallback } from 'react';
import { cohortsApi } from '../../api/client';
import {
  PatientCohort,
  CohortMembership,
  CohortAnalytics,
  ClinicalRiskAssessment,
  CohortType,
  RiskType,
  User,
} from '../../types';

interface CohortWorkspaceProps {
  currentUser: User | null;
  currentPatientId?: string;
  onSelectPatient?: (patientId: string) => void;
}

export const CohortWorkspace: React.FC<CohortWorkspaceProps> = ({
  currentUser,
  currentPatientId,
  onSelectPatient,
}) => {
  const [cohorts, setCohorts] = useState<PatientCohort[]>([]);
  const [selectedCohort, setSelectedCohort] = useState<PatientCohort | null>(null);
  const [members, setMembers] = useState<CohortMembership[]>([]);
  const [analytics, setAnalytics] = useState<CohortAnalytics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [showRiskModal, setShowRiskModal] = useState<boolean>(false);
  const [showRiskDetailModal, setShowRiskDetailModal] = useState<boolean>(false);
  const [targetPatientId, setTargetPatientId] = useState<string>('');
  const [targetRiskType, setTargetRiskType] = useState<RiskType>('readmission_30d');
  const [stratifying, setStratifying] = useState<boolean>(false);
  const [selectedRiskAssessment, setSelectedRiskAssessment] = useState<ClinicalRiskAssessment | null>(null);

  // New cohort form state
  const [newCohortName, setNewCohortName] = useState('');
  const [newCohortDesc, setNewCohortDesc] = useState('');
  const [newCohortType, setNewCohortType] = useState<CohortType>('disease_registry');
  const [newMinAge, setNewMinAge] = useState<string>('');
  const [newConditions, setNewConditions] = useState<string>('');
  const [newIsDynamic, setNewIsDynamic] = useState<boolean>(true);

  // Load cohorts
  const loadCohorts = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await cohortsApi.list();
      setCohorts(res.items);
      if (res.items.length > 0 && !selectedCohort) {
        setSelectedCohort(res.items[0]);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load disease registries and cohorts.');
    } finally {
      setLoading(false);
    }
  }, [selectedCohort]);

  // Load cohort details, members, and analytics
  const loadCohortData = useCallback(async (cohort: PatientCohort) => {
    try {
      const [membersData, analyticsData] = await Promise.all([
        cohortsApi.listMembers(cohort.cohort_id),
        cohortsApi.getAnalytics(cohort.cohort_id),
      ]);
      setMembers(membersData);
      setAnalytics(analyticsData);
    } catch (err: any) {
      console.error('Error loading cohort data:', err);
    }
  }, []);

  useEffect(() => {
    loadCohorts();
  }, [loadCohorts]);

  useEffect(() => {
    if (selectedCohort) {
      loadCohortData(selectedCohort);
    }
  }, [selectedCohort, loadCohortData]);

  // Create Cohort Handler
  const handleCreateCohort = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const conditionsList = newConditions
        ? newConditions.split(',').map((s) => s.trim()).filter(Boolean)
        : undefined;

      const created = await cohortsApi.create({
        name: newCohortName,
        description: newCohortDesc,
        cohort_type: newCohortType,
        criteria: {
          min_age: newMinAge ? parseInt(newMinAge, 10) : undefined,
          conditions: conditionsList,
        },
        is_dynamic: newIsDynamic,
      });

      setShowCreateModal(false);
      setNewCohortName('');
      setNewCohortDesc('');
      setNewMinAge('');
      setNewConditions('');
      setSelectedCohort(created);
      await loadCohorts();
    } catch (err: any) {
      alert(err?.message || 'Failed to create cohort');
    } finally {
      setLoading(false);
    }
  };

  // Run Risk Stratification
  const handleRunRiskStratification = async () => {
    if (!targetPatientId) return;
    try {
      setStratifying(true);
      const result = await cohortsApi.calculateRisk(targetPatientId, {
        risk_type: targetRiskType,
      });
      setSelectedRiskAssessment(result);
      setShowRiskModal(false);
      setShowRiskDetailModal(true);
      if (selectedCohort) {
        await loadCohortData(selectedCohort);
      }
    } catch (err: any) {
      alert(err?.message || 'Failed to calculate clinical risk.');
    } finally {
      setStratifying(false);
    }
  };

  const getTierColor = (tier?: string) => {
    switch (tier) {
      case 'CRITICAL':
        return '#ef4444';
      case 'HIGH':
        return '#f97316';
      case 'MODERATE':
        return '#eab308';
      case 'LOW':
        return '#10b981';
      default:
        return '#64748b';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%' }}>
      {/* Top Header & Cohort Selector */}
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
            <span>👥</span> Clinical Cohort Analytics & Population Risk
          </h2>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: '#94a3b8' }}>
            Longitudinal disease registries, dynamic patient inclusion, and deterministic clinical risk stratification.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <select
            aria-label="Select Cohort Registry"
            value={selectedCohort?.cohort_id || ''}
            onChange={(e) => {
              const found = cohorts.find((c) => c.cohort_id === e.target.value);
              if (found) setSelectedCohort(found);
            }}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              background: '#1e293b',
              color: '#f8fafc',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              fontSize: '0.875rem',
            }}
          >
            {cohorts.map((c) => (
              <option key={c.cohort_id} value={c.cohort_id}>
                {c.name} ({c.cohort_type.replace('_', ' ')})
              </option>
            ))}
          </select>

          <button
            onClick={() => setShowCreateModal(true)}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              background: '#3b82f6',
              color: '#ffffff',
              border: 'none',
              fontWeight: 600,
              fontSize: '0.875rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem',
            }}
          >
            <span>➕</span> New Registry / Cohort
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '1rem', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', border: '1px solid #ef4444' }}>
          {error}
        </div>
      )}

      {loading && !selectedCohort ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#94a3b8' }}>Loading clinical registries...</div>
      ) : selectedCohort ? (
        <>
          {/* Cohort Description & Dynamic Indicator */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.45)',
              backdropFilter: 'blur(12px)',
              padding: '1rem 1.25rem',
              borderRadius: '12px',
              border: '1px solid rgba(255, 255, 255, 0.05)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <div>
              <strong style={{ color: '#f8fafc' }}>{selectedCohort.name}</strong>
              <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: '#cbd5e1' }}>
                {selectedCohort.description}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span
                style={{
                  padding: '0.25rem 0.6rem',
                  borderRadius: '999px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  background: selectedCohort.is_dynamic ? 'rgba(16, 185, 129, 0.2)' : 'rgba(148, 163, 184, 0.2)',
                  color: selectedCohort.is_dynamic ? '#10b981' : '#94a3b8',
                }}
              >
                {selectedCohort.is_dynamic ? '⚡ Dynamic Sync' : '📌 Static Roster'}
              </span>
              <span
                style={{
                  padding: '0.25rem 0.6rem',
                  borderRadius: '999px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  background: 'rgba(59, 130, 246, 0.2)',
                  color: '#60a5fa',
                  textTransform: 'capitalize',
                }}
              >
                {selectedCohort.cohort_type.replace('_', ' ')}
              </span>
            </div>
          </div>

          {/* KPI Analytics Cards */}
          {analytics && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
              <div style={{ background: 'rgba(30, 41, 59, 0.7)', padding: '1rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Enrolled Patients</span>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f8fafc', marginTop: '0.25rem' }}>{analytics.total_members}</div>
              </div>

              <div style={{ background: 'rgba(30, 41, 59, 0.7)', padding: '1rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>High/Critical Risk</span>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#ef4444', marginTop: '0.25rem' }}>{analytics.high_risk_patient_count}</div>
              </div>

              <div style={{ background: 'rgba(30, 41, 59, 0.7)', padding: '1rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Mean Risk Score</span>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#eab308', marginTop: '0.25rem' }}>{analytics.mean_risk_score} <span style={{ fontSize: '0.875rem' }}>/100</span></div>
              </div>

              <div style={{ background: 'rgba(30, 41, 59, 0.7)', padding: '1rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Active CDS Alerts</span>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#f97316', marginTop: '0.25rem' }}>{analytics.active_alerts_count}</div>
              </div>

              <div style={{ background: 'rgba(30, 41, 59, 0.7)', padding: '1rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Active Care Plans</span>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#10b981', marginTop: '0.25rem' }}>{analytics.active_care_plans_count}</div>
              </div>

              <div style={{ background: 'rgba(30, 41, 59, 0.7)', padding: '1rem', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Overdue Tasks</span>
                <div style={{ fontSize: '1.75rem', fontWeight: 700, color: '#ec4899', marginTop: '0.25rem' }}>{analytics.overdue_tasks_count}</div>
              </div>
            </div>
          )}

          {/* Risk Tier Breakdown Bar */}
          {analytics && analytics.total_members > 0 && (
            <div
              style={{
                background: 'rgba(15, 23, 42, 0.6)',
                padding: '1.25rem',
                borderRadius: '12px',
                border: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem', color: '#f8fafc' }}>
                Population Risk Tier Distribution
              </h3>
              <div style={{ display: 'flex', height: '12px', borderRadius: '6px', overflow: 'hidden', background: '#334155' }}>
                {['CRITICAL', 'HIGH', 'MODERATE', 'LOW'].map((tier) => {
                  const count = analytics.risk_tier_distribution[tier] || 0;
                  const pct = (count / analytics.total_members) * 100;
                  if (pct === 0) return null;
                  return (
                    <div
                      key={tier}
                      style={{
                        width: `${pct}%`,
                        background: getTierColor(tier),
                        transition: 'width 0.4s ease',
                      }}
                      title={`${tier}: ${count} (${pct.toFixed(1)}%)`}
                    />
                  );
                })}
              </div>
              <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.75rem', flexWrap: 'wrap' }}>
                {['CRITICAL', 'HIGH', 'MODERATE', 'LOW'].map((tier) => (
                  <div key={tier} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem', color: '#cbd5e1' }}>
                    <div style={{ width: '10px', height: '10px', borderRadius: '2px', background: getTierColor(tier) }} />
                    <span>{tier}: {analytics.risk_tier_distribution[tier] || 0}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Members Table & Action Bar */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.65)',
              backdropFilter: 'blur(16px)',
              padding: '1.25rem',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.125rem', color: '#f8fafc' }}>
                Enrolled Patients ({members.length})
              </h3>
              {currentPatientId && (
                <button
                  onClick={() => {
                    setTargetPatientId(currentPatientId);
                    setShowRiskModal(true);
                  }}
                  style={{
                    padding: '0.4rem 0.8rem',
                    borderRadius: '8px',
                    background: '#8b5cf6',
                    color: '#ffffff',
                    border: 'none',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                  }}
                >
                  <span>⚡</span> Stratify Risk for Active Patient
                </button>
              )}
            </div>

            {members.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2.5rem', color: '#94a3b8' }}>
                No patients currently enrolled in this registry.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.1)', color: '#94a3b8' }}>
                      <th style={{ padding: '0.75rem 0.5rem' }}>Patient ID</th>
                      <th style={{ padding: '0.75rem 0.5rem' }}>Name</th>
                      <th style={{ padding: '0.75rem 0.5rem' }}>Enrolled</th>
                      <th style={{ padding: '0.75rem 0.5rem' }}>Status</th>
                      <th style={{ padding: '0.75rem 0.5rem' }}>Risk Score</th>
                      <th style={{ padding: '0.75rem 0.5rem' }}>Risk Tier</th>
                      <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {members.map((m) => (
                      <tr
                        key={m.id}
                        style={{
                          borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                          color: '#f8fafc',
                        }}
                      >
                        <td style={{ padding: '0.75rem 0.5rem', fontFamily: 'monospace', color: '#60a5fa' }}>
                          {m.patient_identifier || `PAT-${m.patient_id}`}
                        </td>
                        <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>
                          {m.patient_name || 'Patient Record'}
                        </td>
                        <td style={{ padding: '0.75rem 0.5rem', color: '#94a3b8' }}>
                          {new Date(m.enrolled_at).toLocaleDateString()}
                        </td>
                        <td style={{ padding: '0.75rem 0.5rem' }}>
                          <span
                            style={{
                              padding: '0.2rem 0.5rem',
                              borderRadius: '4px',
                              fontSize: '0.75rem',
                              background: m.status === 'active' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(148, 163, 184, 0.2)',
                              color: m.status === 'active' ? '#10b981' : '#94a3b8',
                            }}
                          >
                            {m.status}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem 0.5rem', fontWeight: 700 }}>
                          {m.latest_risk_score !== null && m.latest_risk_score !== undefined
                            ? `${m.latest_risk_score} / 100`
                            : <span style={{ color: '#64748b' }}>Pending</span>}
                        </td>
                        <td style={{ padding: '0.75rem 0.5rem' }}>
                          {m.latest_risk_tier ? (
                            <span
                              style={{
                                padding: '0.25rem 0.5rem',
                                borderRadius: '6px',
                                fontSize: '0.75rem',
                                fontWeight: 700,
                                background: `${getTierColor(m.latest_risk_tier)}25`,
                                color: getTierColor(m.latest_risk_tier),
                                border: `1px solid ${getTierColor(m.latest_risk_tier)}60`,
                              }}
                            >
                              {m.latest_risk_tier}
                            </span>
                          ) : (
                            <span style={{ color: '#64748b' }}>—</span>
                          )}
                        </td>
                        <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>
                          <button
                            onClick={() => {
                              setTargetPatientId(m.patient_identifier || `PAT-${m.patient_id}`);
                              setShowRiskModal(true);
                            }}
                            style={{
                              padding: '0.3rem 0.6rem',
                              borderRadius: '6px',
                              background: '#3b82f6',
                              color: '#fff',
                              border: 'none',
                              fontSize: '0.75rem',
                              cursor: 'pointer',
                              marginRight: '0.5rem',
                            }}
                          >
                            ⚡ Score Risk
                          </button>
                          {onSelectPatient && m.patient_identifier && (
                            <button
                              onClick={() => onSelectPatient(m.patient_identifier!)}
                              style={{
                                padding: '0.3rem 0.6rem',
                                borderRadius: '6px',
                                background: 'rgba(255, 255, 255, 0.1)',
                                color: '#fff',
                                border: 'none',
                                fontSize: '0.75rem',
                                cursor: 'pointer',
                              }}
                            >
                              View Context
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : null}

      {/* Modal: Create Registry / Cohort */}
      {showCreateModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            style={{
              background: '#0f172a',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '16px',
              padding: '1.5rem',
              width: '90%',
              maxWidth: '500px',
              color: '#f8fafc',
            }}
          >
            <h3 style={{ margin: '0 0 1rem' }}>➕ Create Disease Registry / Cohort</h3>
            <form onSubmit={handleCreateCohort} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Registry Name</label>
                <input
                  required
                  value={newCohortName}
                  onChange={(e) => setNewCohortName(e.target.value)}
                  placeholder="e.g. Uncontrolled Hypertension Registry"
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                />
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Clinical Description</label>
                <textarea
                  required
                  rows={3}
                  value={newCohortDesc}
                  onChange={(e) => setNewCohortDesc(e.target.value)}
                  placeholder="Clinical objective, monitoring protocol..."
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <div>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Cohort Type</label>
                  <select
                    value={newCohortType}
                    onChange={(e) => setNewCohortType(e.target.value as CohortType)}
                    style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                  >
                    <option value="disease_registry">Disease Registry</option>
                    <option value="risk_watch_list">Risk Watch List</option>
                    <option value="post_op_monitoring">Post-Op Monitoring</option>
                    <option value="quality_measure">Quality Measure</option>
                    <option value="custom_cohort">Custom Cohort</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Min Age (optional)</label>
                  <input
                    type="number"
                    value={newMinAge}
                    onChange={(e) => setNewMinAge(e.target.value)}
                    placeholder="e.g. 65"
                    style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Condition Keywords (comma separated)</label>
                <input
                  value={newConditions}
                  onChange={(e) => setNewConditions(e.target.value)}
                  placeholder="e.g. Hypertension, Heart Failure, COPD"
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.25rem' }}>
                <input
                  type="checkbox"
                  id="dynamic-cb"
                  checked={newIsDynamic}
                  onChange={(e) => setNewIsDynamic(e.target.checked)}
                />
                <label htmlFor="dynamic-cb" style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>
                  Enable dynamic automated patient matching
                </label>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1rem' }}>
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#334155', color: '#fff', border: 'none', cursor: 'pointer' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#3b82f6', color: '#fff', border: 'none', fontWeight: 600, cursor: 'pointer' }}
                >
                  Create Registry
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Calculate Risk Stratification */}
      {showRiskModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            style={{
              background: '#0f172a',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '16px',
              padding: '1.5rem',
              width: '90%',
              maxWidth: '450px',
              color: '#f8fafc',
            }}
          >
            <h3 style={{ margin: '0 0 1rem' }}>⚡ Run Clinical Risk Stratification</h3>
            <p style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
              Calculating multi-factorial deterministic clinical risk for patient: <strong>{targetPatientId}</strong>
            </p>

            <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Target Risk Model</label>
              <select
                value={targetRiskType}
                onChange={(e) => setTargetRiskType(e.target.value as RiskType)}
                style={{ width: '100%', padding: '0.6rem', borderRadius: '8px', background: '#1e293b', color: '#fff', border: '1px solid #334155' }}
              >
                <option value="readmission_30d">30-Day Readmission Risk</option>
                <option value="cardiovascular_decompensation">Cardiovascular Decompensation Risk</option>
                <option value="clinical_deterioration">Clinical Deterioration & Sepsis Risk</option>
                <option value="medication_adherence">Medication Non-Adherence Risk</option>
                <option value="general_mortality">1-Year Mortality Vulnerability</option>
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1.5rem' }}>
              <button
                type="button"
                onClick={() => setShowRiskModal(false)}
                style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#334155', color: '#fff', border: 'none', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={stratifying}
                onClick={handleRunRiskStratification}
                style={{ padding: '0.5rem 1rem', borderRadius: '8px', background: '#8b5cf6', color: '#fff', border: 'none', fontWeight: 600, cursor: 'pointer' }}
              >
                {stratifying ? 'Calculating...' : 'Calculate Score'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Risk Assessment Breakdown */}
      {showRiskDetailModal && selectedRiskAssessment && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <div
            style={{
              background: '#0f172a',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              borderRadius: '16px',
              padding: '1.5rem',
              width: '90%',
              maxWidth: '600px',
              maxHeight: '85vh',
              overflowY: 'auto',
              color: '#f8fafc',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.25rem' }}>
                Clinical Risk Assessment Breakdown
              </h3>
              <span
                style={{
                  padding: '0.3rem 0.75rem',
                  borderRadius: '999px',
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  background: `${getTierColor(selectedRiskAssessment.risk_tier)}25`,
                  color: getTierColor(selectedRiskAssessment.risk_tier),
                  border: `1px solid ${getTierColor(selectedRiskAssessment.risk_tier)}60`,
                }}
              >
                {selectedRiskAssessment.risk_tier} ({selectedRiskAssessment.risk_score}/100)
              </span>
            </div>

            <p style={{ fontSize: '0.9rem', color: '#cbd5e1', background: 'rgba(255,255,255,0.05)', padding: '0.75rem', borderRadius: '8px' }}>
              {selectedRiskAssessment.predicted_outcome}
            </p>

            <div style={{ marginTop: '1.25rem' }}>
              <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.95rem', color: '#f8fafc' }}>
                Contributing Clinical Factors
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {(selectedRiskAssessment.contributing_factors_json || []).map((f, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: '#1e293b',
                      padding: '0.6rem 0.8rem',
                      borderRadius: '8px',
                      borderLeft: `4px solid ${getTierColor(f.severity)}`,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', fontWeight: 600 }}>
                      <span>{f.factor_name}</span>
                      <span style={{ color: getTierColor(f.severity), fontSize: '0.75rem' }}>{f.severity}</span>
                    </div>
                    {f.observed_value && (
                      <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.2rem' }}>
                        Observed: {f.observed_value}
                      </div>
                    )}
                    <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '0.25rem' }}>
                      {f.clinical_rationale}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ marginTop: '1.25rem' }}>
              <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.95rem', color: '#f8fafc' }}>
                Recommended Actionable Interventions
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {(selectedRiskAssessment.mitigation_recommendations_json || []).map((m, idx) => (
                  <div
                    key={idx}
                    style={{
                      background: 'rgba(59, 130, 246, 0.1)',
                      border: '1px solid rgba(59, 130, 246, 0.25)',
                      padding: '0.6rem 0.8rem',
                      borderRadius: '8px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', fontWeight: 600, color: '#60a5fa' }}>
                      <span>{m.action_title}</span>
                      <span style={{ fontSize: '0.75rem', color: '#f59e0b' }}>[{m.priority}]</span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '0.25rem' }}>
                      {m.rational}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
              <button
                type="button"
                onClick={() => setShowRiskDetailModal(false)}
                style={{ padding: '0.5rem 1.25rem', borderRadius: '8px', background: '#334155', color: '#fff', border: 'none', fontWeight: 600, cursor: 'pointer' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
