// ==============================================================================
// MediGen AI - Clinical Workflow Orchestration & Care Plan Workspace
// ==============================================================================

import React, { useEffect, useState, useCallback } from 'react';
import { carePlansApi } from '../../api/client';
import { CarePlan, CarePlanCategory, CareTask, CareTaskType, TaskPriority } from '../../types';

interface CarePlanWorkspaceProps {
  patientId?: string;
  onTriggerSynthesis?: (category: CarePlanCategory, customInstructions?: string) => Promise<void>;
}

export const CarePlanWorkspace: React.FC<CarePlanWorkspaceProps> = ({
  patientId,
  onTriggerSynthesis,
}) => {
  const [carePlans, setCarePlans] = useState<CarePlan[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<CarePlan | null>(null);
  const [careTasks, setCareTasks] = useState<CareTask[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSynthModalOpen, setIsSynthModalOpen] = useState<boolean>(false);
  const [synthCategory, setSynthCategory] = useState<CarePlanCategory>('chronic_disease_management');
  const [customInstructions, setCustomInstructions] = useState<string>('');
  const [completingTaskId, setCompletingTaskId] = useState<string | null>(null);
  const [completionNotes, setCompletionNotes] = useState<string>('');
  const [isReviewModalOpen, setIsReviewModalOpen] = useState<boolean>(false);
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [confirmAccuracy, setConfirmAccuracy] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!patientId) {
      setCarePlans([]);
      setSelectedPlan(null);
      setCareTasks([]);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const [plansRes, tasksRes] = await Promise.all([
        carePlansApi.list(patientId),
        carePlansApi.listTasks(patientId),
      ]);
      setCarePlans(plansRes.items);
      setCareTasks(tasksRes.items);

      if (plansRes.items.length > 0) {
        // Default select active or first plan
        const activePlan = plansRes.items.find((p) => p.status === 'active') || plansRes.items[0];
        setSelectedPlan(activePlan);
      } else {
        setSelectedPlan(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load care plans or clinical tasks.');
    } finally {
      setIsLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSynthesize = async () => {
    if (!patientId) return;
    setIsLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      if (onTriggerSynthesis) {
        await onTriggerSynthesis(synthCategory, customInstructions);
        setSuccessMsg('Background AI Care Plan synthesis enqueued.');
      } else {
        await carePlansApi.enqueueSynthesis(patientId, synthCategory, customInstructions);
        setSuccessMsg('AI Care Plan draft generation initiated.');
      }
      setIsSynthModalOpen(false);
      setCustomInstructions('');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to synthesize care plan.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleReviewSignoff = async () => {
    if (!selectedPlan) return;
    if (!confirmAccuracy) {
      setError('You must confirm clinical review before signoff.');
      return;
    }
    setError(null);
    try {
      const updated = await carePlansApi.review(selectedPlan.plan_id, true, reviewNotes, true);
      setSelectedPlan(updated);
      setIsReviewModalOpen(false);
      setReviewNotes('');
      setConfirmAccuracy(false);
      setSuccessMsg('Care plan reviewed and activated by physician.');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to review care plan.');
    }
  };

  const handleCompleteTask = async (taskId: string) => {
    setError(null);
    try {
      await carePlansApi.completeTask(taskId, completionNotes.trim() || undefined);
      setCompletingTaskId(null);
      setCompletionNotes('');
      setSuccessMsg('Care task marked complete.');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to complete care task.');
    }
  };

  const getPriorityBadgeClass = (priority: TaskPriority) => {
    switch (priority) {
      case 'STAT':
        return 'badge-danger';
      case 'URGENT':
        return 'badge-warning';
      case 'ROUTINE':
        return 'badge-primary';
      default:
        return 'badge-secondary';
    }
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'active':
        return 'badge-success';
      case 'completed':
        return 'badge-info';
      case 'draft':
        return 'badge-warning';
      case 'cancelled':
        return 'badge-danger';
      default:
        return 'badge-secondary';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%', overflowY: 'auto' }}>
      {/* Top Header & Actions */}
      <div className="glass-panel" style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>📋</span> Clinical Workflow Orchestration & Care Plans
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Longitudinal care coordination, health goal tracking & follow-up task orchestration
          </span>
        </div>

        {patientId && (
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => setIsSynthModalOpen(true)}
              disabled={isLoading}
            >
              ⚡ Generate AI Care Plan
            </button>
            <button className="btn btn-secondary btn-sm" onClick={loadData} disabled={isLoading}>
              ↻
            </button>
          </div>
        )}
      </div>

      {/* Clinical Disclaimer */}
      <div style={{ padding: '8px 14px', background: 'rgba(2, 132, 199, 0.08)', border: '1px solid rgba(2, 132, 199, 0.25)', borderRadius: 'var(--radius-sm)', color: '#38bdf8', fontSize: '0.75rem', lineHeight: '1.4' }}>
        ℹ️ <strong>Assistive Decision Support:</strong> AI-generated care plans and recommendations are assistive drafts and require attending clinician review and formal activation.
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

      {/* Main Workspace Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '16px' }}>
        {/* Left Column: Active Care Plan Details */}
        <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {carePlans.length > 1 && (
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', overflowX: 'auto', paddingBottom: '6px' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Plans:</span>
              {carePlans.map((p) => (
                <button
                  key={p.plan_id}
                  className={`btn btn-sm ${selectedPlan?.plan_id === p.plan_id ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setSelectedPlan(p)}
                  style={{ fontSize: '0.75rem', padding: '2px 8px', whiteSpace: 'nowrap' }}
                >
                  {p.title.length > 24 ? `${p.title.slice(0, 24)}...` : p.title}
                </button>
              ))}
            </div>
          )}

          {selectedPlan ? (
            <>
              {/* Care Plan Card Header */}
              <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                  <div>
                    <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                      {selectedPlan.title}
                    </h4>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                      Category: <strong style={{ textTransform: 'capitalize' }}>{selectedPlan.category ? selectedPlan.category.replace(/_/g, ' ') : 'General'}</strong> | ID: {selectedPlan.plan_id}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                    <span className={`badge ${getStatusBadgeClass(selectedPlan.status)}`} style={{ fontSize: '0.7rem' }}>
                      {(selectedPlan.status || 'draft').toUpperCase()}
                    </span>
                    {selectedPlan.is_ai_generated && (
                      <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>
                        🤖 AI-Generated
                      </span>
                    )}
                  </div>
                </div>

                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginTop: '10px' }}>
                  {selectedPlan.description}
                </p>

                {/* Review / Activation Action */}
                {selectedPlan.status === 'draft' && (
                  <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => setIsReviewModalOpen(true)}
                    >
                      ✓ Review & Activate Plan
                    </button>
                  </div>
                )}
              </div>

              {/* Structured Health Goals */}
              <div>
                <h5 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                  🎯 Clinical Health Goals ({selectedPlan.goals_json?.length || 0})
                </h5>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {selectedPlan.goals_json && selectedPlan.goals_json.length > 0 ? (
                    selectedPlan.goals_json.map((g, idx) => (
                      <div
                        key={g.goal_id || idx}
                        style={{
                          padding: '10px 12px',
                          background: 'rgba(255,255,255,0.02)',
                          border: '1px solid var(--border-color)',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <strong style={{ fontSize: '0.8125rem', color: 'var(--text-primary)' }}>
                            {g.title}
                          </strong>
                          <span className="badge badge-secondary" style={{ fontSize: '0.65rem' }}>
                            {g.status || 'in_progress'}
                          </span>
                        </div>
                        {g.target_metric && (
                          <div style={{ fontSize: '0.75rem', color: '#38bdf8', marginTop: '2px' }}>
                            Target: {g.target_metric}
                          </div>
                        )}
                        {g.notes && (
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                            {g.notes}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>No explicit goals specified.</div>
                  )}
                </div>
              </div>

              {/* Structured Interventions */}
              <div>
                <h5 style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                  ⚡ Planned Interventions ({selectedPlan.interventions_json?.length || 0})
                </h5>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {selectedPlan.interventions_json && selectedPlan.interventions_json.length > 0 ? (
                    selectedPlan.interventions_json.map((i, idx) => (
                      <div
                        key={i.intervention_id || idx}
                        style={{
                          padding: '10px 12px',
                          background: 'rgba(255,255,255,0.02)',
                          border: '1px solid var(--border-color)',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        <div style={{ fontSize: '0.8125rem', color: 'var(--text-primary)' }}>
                          {i.description}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                          <span>Category: <strong>{i.category}</strong></span>
                          <span>Party: <strong>{i.responsible_party || 'clinician'}</strong></span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>No interventions defined.</div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
              No care plans recorded for this patient. Click <strong>⚡ Generate AI Care Plan</strong> to draft one.
            </div>
          )}
        </div>

        {/* Right Column: Follow-up Tasks & Actionable Workflows */}
        <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span>📌</span> Clinical Follow-Up Tasks ({careTasks.length})
            </h4>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', overflowY: 'auto', maxHeight: '520px' }}>
            {careTasks.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '48px 0', color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
                No active follow-up tasks.
              </div>
            ) : (
              careTasks.map((task) => (
                <div
                  key={task.task_id}
                  style={{
                    padding: '12px',
                    borderRadius: 'var(--radius-sm)',
                    background: task.is_overdue ? 'rgba(239,68,68,0.1)' : 'rgba(255,255,255,0.02)',
                    border: task.is_overdue ? '1px solid rgba(239,68,68,0.35)' : '1px solid var(--border-color)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <strong style={{ fontSize: '0.8125rem', color: 'var(--text-primary)' }}>
                        {task.title}
                      </strong>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        Type: {task.task_type.replace(/_/g, ' ')}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      <span className={`badge ${getPriorityBadgeClass(task.priority)}`} style={{ fontSize: '0.65rem' }}>
                        {task.priority}
                      </span>
                      {task.is_overdue && (
                        <span className="badge badge-danger" style={{ fontSize: '0.65rem' }}>
                          OVERDUE
                        </span>
                      )}
                    </div>
                  </div>

                  {task.instructions && (
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>
                      {task.instructions}
                    </p>
                  )}

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    <span>Due: {new Date(task.due_date).toLocaleDateString()}</span>
                    <span>Status: <strong style={{ textTransform: 'uppercase' }}>{task.status}</strong></span>
                  </div>

                  {/* Complete Task Workflow */}
                  {task.status !== 'completed' && task.status !== 'cancelled' && (
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                        onClick={() => setCompletingTaskId(task.task_id)}
                      >
                        ✓ Complete
                      </button>
                    </div>
                  )}

                  {/* Task Completion Note Form */}
                  {completingTaskId === task.task_id && (
                    <div style={{ marginTop: '8px', padding: '8px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="Optional completion outcome notes..."
                        value={completionNotes}
                        onChange={(e) => setCompletionNotes(e.target.value)}
                        style={{ fontSize: '0.75rem' }}
                      />
                      <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '0.65rem', padding: '2px 6px' }}
                          onClick={() => { setCompletingTaskId(null); setCompletionNotes(''); }}
                        >
                          Cancel
                        </button>
                        <button
                          className="btn btn-primary btn-sm"
                          style={{ fontSize: '0.65rem', padding: '2px 6px' }}
                          onClick={() => handleCompleteTask(task.task_id)}
                        >
                          Confirm Completion
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

      {/* Modal: AI Care Plan Synthesis */}
      {isSynthModalOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="glass-panel" style={{ width: '480px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              ⚡ Synthesize AI Care Plan Draft
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Care Domain Category:</label>
              <select
                className="form-select"
                value={synthCategory}
                onChange={(e) => setSynthCategory(e.target.value as CarePlanCategory)}
                style={{ fontSize: '0.8125rem' }}
              >
                <option value="chronic_disease_management">Chronic Disease Management</option>
                <option value="post_discharge_followup">Post-Discharge Transitional Follow-Up</option>
                <option value="preventive_care">Preventive Care & Wellness</option>
                <option value="rehabilitation">Rehabilitation & Recovery</option>
                <option value="acute_care_plan">Acute Episode Care Plan</option>
              </select>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Optional Clinician Directives:</label>
              <textarea
                className="form-input"
                rows={3}
                placeholder="e.g. Focus on post-hypertensive crisis medication stabilization and telemetry monitoring..."
                value={customInstructions}
                onChange={(e) => setCustomInstructions(e.target.value)}
                style={{ fontSize: '0.75rem' }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '6px' }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setIsSynthModalOpen(false)}>
                Cancel
              </button>
              <button className="btn btn-primary btn-sm" onClick={handleSynthesize} disabled={isLoading}>
                Generate Draft Plan
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Physician Review & Activation */}
      {isReviewModalOpen && selectedPlan && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="glass-panel" style={{ width: '480px', padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              ✓ Physician Review & Care Plan Signoff
            </h4>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: 0 }}>
              Reviewing: <strong>{selectedPlan.title}</strong>
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Physician Directives / Remarks:</label>
              <textarea
                className="form-input"
                rows={3}
                placeholder="Optional signoff notes or clinical directives..."
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                style={{ fontSize: '0.75rem' }}
              />
            </div>
            <label style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-primary)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={confirmAccuracy}
                onChange={(e) => setConfirmAccuracy(e.target.checked)}
              />
              I confirm clinical review of this care plan and authorize its activation.
            </label>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '6px' }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setIsReviewModalOpen(false)}>
                Cancel
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleReviewSignoff}
                disabled={!confirmAccuracy || isLoading}
              >
                Sign & Activate Plan
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
