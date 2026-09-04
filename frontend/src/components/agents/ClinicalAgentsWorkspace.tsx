import React, { useState, useEffect, useMemo } from 'react';
import { agentsApi, patientsApi, fhirApi } from '../../api/client';
import {
  AgentType,
  ApprovalStatus,
  CareCoordinationSynthesisResponse,
  ClinicalAgentDefinition,
  ClinicalAgentRecommendation,
  ClinicalAgentRun,
  Patient,
  RecommendationActionClass,
  RecommendationPriority,
} from '../../types';

export const ClinicalAgentsWorkspace: React.FC = () => {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');
  const [definitions, setDefinitions] = useState<ClinicalAgentDefinition[]>([]);
  const [synthesis, setSynthesis] = useState<CareCoordinationSynthesisResponse | null>(null);
  const [runs, setRuns] = useState<ClinicalAgentRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<ClinicalAgentRun | null>(null);

  const [loading, setLoading] = useState<boolean>(false);
  const [synthesizing, setSynthesizing] = useState<boolean>(false);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [executingRunId, setExecutingRunId] = useState<string | null>(null);
  const [reviewNotes, setReviewNotes] = useState<{ [key: string]: string }>({});

  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [actionClassFilter, setActionClassFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [expandedRecId, setExpandedRecId] = useState<string | null>(null);

  const [fhirModalContent, setFhirModalContent] = useState<string | null>(null);
  const [fhirModalTitle, setFhirModalTitle] = useState<string>('');
  const [notification, setNotification] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);

  // Live Agent Inquiry Pipeline (Google Gemini)
  const [prompt, setPrompt] = useState<string>('');
  const [agentType, setAgentType] = useState<AgentType>('clinical_context');

  const [queryLoading, setQueryLoading] = useState<boolean>(false);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [agentResponse, setAgentResponse] = useState<any | null>(null);


  const selectedPatient = useMemo(
    () => patients.find((p) => p.patient_id === selectedPatientId || String(p.id) === selectedPatientId),
    [patients, selectedPatientId]
  );

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedPatientId) {
      loadPatientCareCoordination(selectedPatientId);
      loadPatientRuns(selectedPatientId);
    }
  }, [selectedPatientId]);

  const showNotification = (type: 'success' | 'error' | 'info', message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  const loadInitialData = async () => {
    setLoading(true);
    try {
      const [ptsRes, defsRes] = await Promise.all([
        patientsApi.list(),
        agentsApi.listDefinitions(),
      ]);
      const patientItems: Patient[] = Array.isArray(ptsRes) ? ptsRes : (ptsRes as any).items || [];
      const defItems: ClinicalAgentDefinition[] = Array.isArray(defsRes) ? defsRes : (defsRes as any).items || [];
      setDefinitions(defItems);

      if (patientItems.length > 0) {
        setSelectedPatientId(patientItems[0].patient_id);
      }
    } catch (err: any) {
      showNotification('error', `Failed to load clinical workspace data: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  };


  const loadPatientCareCoordination = async (patientId: string) => {
    setLoading(true);
    try {
      const res = await agentsApi.getPatientCareCoordination(patientId);
      setSynthesis(res);
    } catch (err: any) {
      showNotification('error', `Error loading care coordination: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  };

  const loadPatientRuns = async (patientId: string) => {
    try {
      const res = await agentsApi.listRuns({ patient_id: patientId });
      setRuns(res.items || []);
    } catch (err: any) {
      console.error('Failed to load runs:', err);
    }
  };

  const handleTriggerSynthesis = async () => {
    if (!selectedPatientId) return;
    setSynthesizing(true);
    try {
      const res = await agentsApi.synthesizePatientCareCoordination(selectedPatientId);
      setSynthesis(res);
      await loadPatientRuns(selectedPatientId);
      showNotification('success', 'Multi-Agent Care Coordination synthesis completed successfully.');
    } catch (err: any) {
      showNotification('error', `Synthesis failed: ${err.message || err}`);
    } finally {
      setSynthesizing(false);
    }
  };

  const handleTriggerSpecializedAgent = async (agentType: AgentType) => {
    if (!selectedPatientId) return;
    setLoading(true);
    try {
      await agentsApi.triggerRun({ patient_id: selectedPatientId, agent_type: agentType });
      await loadPatientCareCoordination(selectedPatientId);
      await loadPatientRuns(selectedPatientId);
      showNotification('success', `Specialized agent [${agentType}] executed successfully.`);
    } catch (err: any) {
      showNotification('error', `Agent execution failed: ${err.message || err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApproveRecommendation = async (recId: string) => {
    setReviewingId(recId);
    try {
      const notes = reviewNotes[recId];
      await agentsApi.approveRecommendation(recId, { review_notes: notes });
      await loadPatientCareCoordination(selectedPatientId);
      showNotification('success', `Recommendation ${recId} approved by clinician.`);
    } catch (err: any) {
      showNotification('error', `Approval failed: ${err.message || err}`);
    } finally {
      setReviewingId(null);
    }
  };

  const handleRejectRecommendation = async (recId: string) => {
    setReviewingId(recId);
    try {
      const notes = reviewNotes[recId] || 'Clinician rejected during review.';
      await agentsApi.rejectRecommendation(recId, { review_notes: notes });
      await loadPatientCareCoordination(selectedPatientId);
      showNotification('info', `Recommendation ${recId} rejected.`);
    } catch (err: any) {
      showNotification('error', `Rejection failed: ${err.message || err}`);
    } finally {
      setReviewingId(null);
    }
  };

  const handleExecuteRun = async (runId: string) => {
    setExecutingRunId(runId);
    try {
      await agentsApi.executeRun(runId);
      await loadPatientCareCoordination(selectedPatientId);
      await loadPatientRuns(selectedPatientId);
      showNotification('success', `Approved recommendations for run ${runId} executed.`);
    } catch (err: any) {
      showNotification('error', `Execution failed: ${err.message || err}`);
    } finally {
      setExecutingRunId(null);
    }
  };

  const handleViewFhirTask = async (recId: string) => {
    try {
      const res = await fhirApi.exportAgentTask(recId);
      setFhirModalTitle(`FHIR R4 Task: ${recId}`);
      setFhirModalContent(JSON.stringify(res, null, 2));
    } catch (err: any) {
      showNotification('error', `Failed to export FHIR Task: ${err.message || err}`);
    }
  };

  const handleViewFhirProvenance = async (runId: string) => {
    try {
      const res = await fhirApi.exportAgentProvenance(runId);
      setFhirModalTitle(`FHIR R4 Provenance: PROV-${runId}`);
      setFhirModalContent(JSON.stringify(res, null, 2));
    } catch (err: any) {
      showNotification('error', `Failed to export FHIR Provenance: ${err.message || err}`);
    }
  };

  const handleSendAgentQuery = async (e: React.FormEvent) => {

    e.preventDefault();
    if (!prompt.trim()) return;
    setQueryLoading(true);
    setQueryError(null);
    setAgentResponse(null);
    try {
      const res = await agentsApi.queryAgent({
        prompt,
        agent_type: agentType,
        patient_id: selectedPatientId || undefined,
      });
      setAgentResponse(res);
      showNotification('success', `Clinical response synthesized via ${(res as any).model_name || res.model_used || 'AI Provider'}.`);

    } catch (err: any) {
      const msg = err.message || '';
      if (err.status === 501 || msg.includes('501') || msg.toLowerCase().includes('not configured')) {
        setQueryError('AI service is not configured for this environment.');
      } else if (err.status === 401 || msg.includes('401') || msg.toLowerCase().includes('auth') || msg.toLowerCase().includes('credential')) {
        setQueryError('AI service authentication failed. Please verify provider credentials.');
      } else if (err.status === 429 || msg.includes('429') || msg.toLowerCase().includes('rate limit') || msg.toLowerCase().includes('quota')) {
        setQueryError('AI provider rate limit or quota exceeded. Please try again shortly.');
      } else {
        setQueryError(msg || 'An unexpected error occurred while communicating with the AI service.');
      }
    } finally {
      setQueryLoading(false);
    }
  };


  const filteredRecommendations = useMemo(() => {
    if (!synthesis?.recommendations) return [];
    return synthesis.recommendations.filter((rec) => {
      if (priorityFilter !== 'all' && rec.priority !== priorityFilter) return false;
      if (actionClassFilter !== 'all' && rec.action_class !== actionClassFilter) return false;
      if (statusFilter !== 'all' && rec.approval_status !== statusFilter) return false;
      return true;
    });
  }, [synthesis, priorityFilter, actionClassFilter, statusFilter]);

  const getPriorityBadgeClass = (priority: RecommendationPriority) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-500/20 text-red-400 border border-red-500/30 font-semibold';
      case 'high':
        return 'bg-amber-500/20 text-amber-400 border border-amber-500/30';
      case 'medium':
        return 'bg-blue-500/20 text-blue-400 border border-blue-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border border-slate-500/30';
    }
  };

  const getActionClassBadge = (actionClass: RecommendationActionClass) => {
    switch (actionClass) {
      case 'HIGH_RISK':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950 text-rose-300 border border-rose-800/60">
            ⚠️ High-Risk (Clinician Sign-off Required)
          </span>
        );
      case 'CLINICIAN_APPROVAL_REQUIRED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-950 text-amber-300 border border-amber-800/60">
            🔒 Clinician Approval Required
          </span>
        );
      case 'RECOMMENDATION':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950 text-blue-300 border border-blue-800/60">
            ✨ Clinical Recommendation
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">
            📄 Read-Only Synthesis
          </span>
        );
    }
  };

  const getApprovalStatusBadge = (status: ApprovalStatus) => {
    switch (status) {
      case 'approved':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            ✓ Approved
          </span>
        );
      case 'rejected':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-500/20 text-red-400 border border-red-500/30">
            ✕ Rejected
          </span>
        );
      case 'executed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-500/20 text-purple-400 border border-purple-500/30">
            ⚡ Executed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30">
            ⏱ Pending Clinician Review
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`p-4 rounded-xl shadow-lg border flex items-center justify-between transition-all ${
            notification.type === 'success'
              ? 'bg-emerald-950/80 border-emerald-800 text-emerald-200'
              : notification.type === 'error'
              ? 'bg-red-950/80 border-red-800 text-red-200'
              : 'bg-blue-950/80 border-blue-800 text-blue-200'
          }`}
        >
          <div className="flex items-center gap-3">
            <span className="text-lg">
              {notification.type === 'success' ? '✓' : notification.type === 'error' ? '⚠️' : 'ℹ️'}
            </span>
            <span className="text-sm font-medium">{notification.message}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-slate-400 hover:text-white text-xs font-semibold px-2 py-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* Clinician Supervision Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-indigo-800/40 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-indigo-600/20 border border-indigo-500/30 rounded-xl text-2xl">
              🤖
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-white tracking-wide">
                  Autonomous Care Coordination & Multi-Agent Engine
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Phase 9.0.17
                </span>
              </div>
              <p className="text-xs text-indigo-200/80 mt-1 max-w-3xl leading-relaxed">
                Multi-agent clinical synthesis orchestrating encounters, vitals, CDS alerts, diagnostic loops, medication safety,
                quality gaps, RPM/telehealth, transitions of care, and clinical trials.
              </p>
              <div className="flex items-center gap-4 mt-3 text-xs text-slate-400">
                <span className="flex items-center gap-1.5 text-emerald-400">
                  🛡️ Clinician Supervision Required (Assistive AI Only)
                </span>
                <span className="flex items-center gap-1.5 text-blue-400">
                  🔒 SHA-256 Provenance Verifiable
                </span>
                <span className="flex items-center gap-1.5 text-purple-400">
                  ⚡ FHIR R4 Interoperable
                </span>
              </div>
            </div>
          </div>

          {/* Master Synthesis Action */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleTriggerSynthesis}
              disabled={synthesizing || !selectedPatientId}
              className="flex items-center gap-2 px-5 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold text-sm shadow-lg shadow-indigo-900/30 transition-all disabled:opacity-50"
            >
              {synthesizing ? (
                <>⏳ Synthesizing Multi-Agent Plan...</>
              ) : (
                <>✨ Synthesize Care Coordination</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Patient Selector & Context Strip */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-lg">🩺</span>
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Patient:</label>
          <select
            value={selectedPatientId}
            onChange={(e) => setSelectedPatientId(e.target.value)}
            className="bg-slate-950 border border-slate-700 text-white text-sm rounded-xl px-3 py-2 focus:ring-2 focus:ring-indigo-500 outline-none"
          >
            {patients.map((p) => (
              <option key={p.patient_id} value={p.patient_id}>
                {p.first_name} {p.last_name} ({p.patient_id}) — DOB: {p.date_of_birth} ({p.gender})
              </option>
            ))}
          </select>
        </div>

        {synthesis && (
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800">
              Run: <strong className="text-slate-200">{synthesis.run_id}</strong>
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800">
              Urgent: <strong className="text-red-400">{synthesis.urgent_recommendations_count}</strong>
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800">
              Pending Sign-off: <strong className="text-amber-400">{synthesis.pending_approvals_count}</strong>
            </span>
            <button
              onClick={() => handleViewFhirProvenance(synthesis.run_id)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-950/60 hover:bg-indigo-900/80 text-indigo-300 border border-indigo-800/60 transition-colors"
            >
              📋 FHIR Provenance
            </button>
          </div>
        )}
      </div>

      {/* Live Clinical Agent Inquiry & Reasoning Pipeline (Google Gemini) */}
      <div className="bg-slate-900/90 border border-indigo-800/40 rounded-2xl p-6 shadow-xl space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">⚡</span>
            <div>
              <h3 className="text-base font-bold text-white">Live Clinical Agent Inquiry & Reasoning Pipeline</h3>
              <p className="text-xs text-indigo-200/70">
                Direct Gemini API reasoning with patient context grounding, differential diagnosis, and medication safety checks.
              </p>
            </div>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/30">
            FHIR & HIPAA Audit Compliant
          </span>
        </div>

        <form onSubmit={handleSendAgentQuery} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Target Specialist Agent
              </label>
              <select
                value={agentType}
                onChange={(e) => setAgentType(e.target.value as AgentType)}
                className="w-full bg-slate-950 border border-slate-700 text-white text-sm rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-indigo-500 outline-none"
              >
                <option value="clinical_context">Clinical Context Specialist</option>
                <option value="risk_surveillance">Risk Surveillance & Early Sepsis Warning Specialist</option>
                <option value="diagnostic_followup">Diagnostic Follow-up Specialist</option>
                <option value="medication_safety">Medication Safety & PGx Specialist</option>
                <option value="quality_gap">Quality Measures & Care Gap Specialist</option>
                <option value="rpm_telehealth">Remote Patient Monitoring Specialist</option>
                <option value="transition_discharge">Transitional Care Specialist</option>
                <option value="trial_genomics">Precision Clinical Trials Specialist</option>
                <option value="care_coordination">Care Coordination Specialist</option>
              </select>


            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                Clinical Context
              </label>
              <div className="bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-300 flex items-center justify-between">
                <span>Patient Grounding:</span>
                <span className="font-semibold text-indigo-300">
                  {selectedPatient ? `${selectedPatient.first_name} ${selectedPatient.last_name} (${selectedPatient.patient_id})` : 'All / Population Level'}
                </span>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
              Clinical Inquiry or Directive
            </label>
            <textarea
              rows={3}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., Evaluate glycemic control and cardiovascular risks for this patient, checking for contraindications and HEDIS care gaps."
              className="w-full bg-slate-950 border border-slate-700 text-white text-sm rounded-xl p-3.5 focus:ring-2 focus:ring-indigo-500 outline-none resize-y"
              required
            />
          </div>

          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="text-xs text-slate-500">
              Model: <code className="text-indigo-400 font-mono">gemini-3.5-flash-lite</code> (Grounded Clinical Protocol)
            </div>
            <button
              type="submit"
              disabled={queryLoading || !prompt.trim()}
              className="px-5 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold text-sm rounded-xl shadow-lg shadow-indigo-900/30 transition-all disabled:opacity-50 flex items-center gap-2 cursor-pointer"
            >
              {queryLoading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  Synthesizing with Gemini...
                </>
              ) : (
                <>🚀 Run Agent Query</>
              )}
            </button>
          </div>
        </form>

        {queryError && (
          <div className="p-4 bg-rose-950/80 border border-rose-800 text-rose-200 rounded-xl text-xs space-y-1">
            <div className="font-semibold flex items-center gap-1.5">
              <span>⚠️</span>
              <span>AI Provider Error</span>
            </div>
            <p>{queryError}</p>
          </div>
        )}

        {agentResponse && (
          <div className="p-5 bg-slate-950 border border-indigo-500/40 rounded-xl space-y-3 animate-fadeIn">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-emerald-400">✓ Grounded Response</span>
                <span className="text-xs px-2 py-0.5 rounded bg-indigo-950 border border-indigo-800 text-indigo-300 font-mono">
                  {agentResponse.model_name || 'gemini-3.5-flash-lite'}
                </span>
                {agentResponse.latency_ms && (
                  <span className="text-xs px-2 py-0.5 rounded bg-slate-900 text-slate-400 font-mono">
                    {agentResponse.latency_ms.toFixed(0)} ms
                  </span>
                )}
              </div>
              <span className="text-xs text-slate-500 font-mono">ID: {agentResponse.query_id}</span>
            </div>

            <div className="text-xs text-slate-200 leading-relaxed whitespace-pre-wrap font-sans bg-slate-900/50 p-4 rounded-xl border border-slate-800/80">
              {agentResponse.response_text}
            </div>

            {agentResponse.grounded_chunks && agentResponse.grounded_chunks.length > 0 && (
              <div className="pt-2">
                <h5 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                  Clinical Evidence Citations ({agentResponse.grounded_chunks.length})
                </h5>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {agentResponse.grounded_chunks.map((chunk: any, i: number) => (
                    <div key={i} className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800 text-[11px]">
                      <div className="font-semibold text-slate-300">{chunk.source || `Evidence Citation #${i + 1}`}</div>
                      <div className="text-slate-400 mt-1 line-clamp-2">{chunk.content}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Main Grid: Specialized Agents & Prioritized Action Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Left Column: Registered Specialized Clinical AI Agents (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                🏛️ Specialized Agent Registry
              </h2>
              <span className="text-xs text-slate-500 font-medium">{definitions.length} Active Agents</span>
            </div>

            <div className="space-y-3 max-h-[700px] overflow-y-auto pr-1">
              {definitions.map((def, idx) => (
                <div
                  key={def.agent_id || def.id || idx}
                  className="bg-slate-950/80 border border-slate-800 hover:border-indigo-500/40 rounded-xl p-3.5 transition-all group"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="text-xs font-bold text-slate-200 group-hover:text-indigo-300 transition-colors">
                        {def.name}
                      </h3>
                      <p className="text-[11px] text-slate-400 mt-1 leading-snug">{def.description}</p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-900 text-[10px]">
                    <span className="text-slate-500">Default: {def.default_action_class}</span>
                    <button
                      onClick={() => handleTriggerSpecializedAgent(def.agent_type)}
                      disabled={loading || synthesizing}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-indigo-950 text-indigo-300 border border-indigo-800/60 hover:bg-indigo-900 transition-colors disabled:opacity-40"
                    >
                      ▶ Execute
                    </button>
                  </div>
                </div>
              ))}

            </div>

          </div>
        </div>

        {/* Right Column: Prioritized Care Coordination Recommendations & Clinician Actions (8 cols) */}
        <div className="lg:col-span-8 space-y-4">
          {/* Filters Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-400">Filter:</span>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="bg-slate-950 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 outline-none"
              >
                <option value="all">All Priorities</option>
                <option value="urgent">Urgent</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>

              <select
                value={actionClassFilter}
                onChange={(e) => setActionClassFilter(e.target.value)}
                className="bg-slate-950 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 outline-none"
              >
                <option value="all">All Action Classes</option>
                <option value="HIGH_RISK">High Risk</option>
                <option value="CLINICIAN_APPROVAL_REQUIRED">Approval Required</option>
                <option value="RECOMMENDATION">Recommendation</option>
                <option value="READ_ONLY">Read Only</option>
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-950 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 outline-none"
              >
                <option value="all">All Review Statuses</option>
                <option value="pending_review">Pending Review</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
                <option value="executed">Executed</option>
              </select>
            </div>

            {synthesis && (
              <button
                onClick={() => handleExecuteRun(synthesis.run_id)}
                disabled={executingRunId === synthesis.run_id}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-800/60 text-xs font-semibold transition-colors disabled:opacity-40"
              >
                ⚡ Execute Approved Recommendations
              </button>
            )}
          </div>

          {/* Recommendations Feed */}
          <div className="space-y-4">
            {filteredRecommendations.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
                <div className="text-4xl mb-3">🤖</div>
                <h3 className="text-base font-semibold text-slate-200">No Care Coordination Items</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                  Click "Synthesize Care Coordination" above to trigger deterministic multi-agent evaluation across patient records.
                </p>
              </div>
            ) : (
              filteredRecommendations.map((rec) => {
                const isExpanded = expandedRecId === rec.recommendation_id;
                return (
                  <div
                    key={rec.recommendation_id}
                    className={`bg-slate-900 border rounded-2xl p-5 shadow-sm transition-all ${
                      rec.priority === 'urgent'
                        ? 'border-red-900/60 hover:border-red-700'
                        : rec.action_class === 'HIGH_RISK'
                        ? 'border-amber-900/60 hover:border-amber-700'
                        : 'border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    {/* Header Strip */}
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`px-2 py-0.5 rounded text-[11px] uppercase ${getPriorityBadgeClass(rec.priority)}`}>
                          {rec.priority}
                        </span>
                        {getActionClassBadge(rec.action_class)}
                        {getApprovalStatusBadge(rec.approval_status)}
                      </div>

                      <div className="flex items-center gap-2 text-xs text-slate-500">
                        <span className="font-mono text-[10px]">{rec.recommendation_id}</span>
                        <button
                          onClick={() => handleViewFhirTask(rec.recommendation_id)}
                          className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 text-xs transition-colors"
                          title="Export as FHIR R4 Task"
                        >
                          FHIR Task
                        </button>
                      </div>
                    </div>

                    {/* Title & Description */}
                    <h3 className="text-sm font-bold text-white tracking-wide">{rec.title}</h3>
                    <p className="text-xs text-slate-300 mt-1.5 leading-relaxed">{rec.description}</p>

                    {/* Clinical Rationale Box */}
                    <div className="mt-3 p-3 bg-slate-950/70 border border-slate-800/80 rounded-xl text-xs text-slate-400">
                      <strong className="text-indigo-300 font-semibold">Clinical Rationale: </strong>
                      {rec.rationale}
                    </div>

                    {/* Expandable Evidence Reference Trace */}
                    <div className="mt-3">
                      <button
                        onClick={() => setExpandedRecId(isExpanded ? null : rec.recommendation_id)}
                        className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
                      >
                        <span>{isExpanded ? '▼' : '▶'}</span>
                        Evidence References & Provenance ({rec.evidence_references?.length || 0})
                      </button>

                      {isExpanded && (
                        <div className="mt-2.5 p-3.5 bg-slate-950 border border-slate-800/90 rounded-xl space-y-2 text-xs">
                          <div className="text-[11px] text-slate-400 font-mono flex items-center justify-between pb-2 border-b border-slate-900">
                            <span>SHA-256 Hash: {rec.provenance_hash.slice(0, 24)}...</span>
                            <span>Action Type: {rec.suggested_action_type || 'N/A'}</span>
                          </div>

                          <div className="space-y-2 mt-2">
                            {rec.evidence_references?.map((ev, idx) => (
                              <div key={idx} className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800/50">
                                <div className="flex items-center justify-between text-[11px] text-slate-300">
                                  <span className="font-semibold text-slate-200">
                                    [{ev.entity_type.toUpperCase()}] {ev.title}
                                  </span>
                                  <span className="text-emerald-400 font-mono">
                                    Score: {(ev.confidence_score * 100).toFixed(0)}%
                                  </span>
                                </div>
                                {ev.excerpt && (
                                  <p className="text-[11px] text-slate-400 mt-1 italic leading-snug">
                                    "{ev.excerpt}"
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Clinician Review / Action Controls */}
                    {rec.approval_status === 'pending_review' && (
                      <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
                        <input
                          type="text"
                          placeholder="Optional clinician sign-off notes or instructions..."
                          value={reviewNotes[rec.recommendation_id] || ''}
                          onChange={(e) =>
                            setReviewNotes({ ...reviewNotes, [rec.recommendation_id]: e.target.value })
                          }
                          className="flex-1 bg-slate-950 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-2 outline-none focus:ring-1 focus:ring-indigo-500"
                        />

                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleApproveRecommendation(rec.recommendation_id)}
                            disabled={reviewingId === rec.recommendation_id}
                            className="flex items-center gap-1 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition-colors shadow-md shadow-emerald-950/40 disabled:opacity-40"
                          >
                            ✓ Approve Action
                          </button>
                          <button
                            onClick={() => handleRejectRecommendation(rec.recommendation_id)}
                            disabled={reviewingId === rec.recommendation_id}
                            className="flex items-center gap-1 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-red-950 hover:text-red-300 text-slate-300 font-semibold text-xs border border-slate-700 transition-colors disabled:opacity-40"
                          >
                            ✕ Reject
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Reviewed Metadata */}
                    {rec.reviewed_at && (
                      <div className="mt-3 pt-2 border-t border-slate-900 text-[11px] text-slate-500 flex items-center justify-between">
                        <span>Reviewed by: {rec.reviewed_by_name || 'Authorized Clinician'}</span>
                        <span>{new Date(rec.reviewed_at).toLocaleString()}</span>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* FHIR Interoperability Modal */}
      {fhirModalContent && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                📄 {fhirModalTitle}
              </h3>
              <button
                onClick={() => setFhirModalContent(null)}
                className="text-slate-400 hover:text-white text-sm font-bold px-2 py-1"
              >
                ✕
              </button>
            </div>

            <div className="p-4 overflow-y-auto flex-1 bg-slate-950">
              <pre className="text-[11px] font-mono text-emerald-400 leading-relaxed overflow-x-auto">
                {fhirModalContent}
              </pre>
            </div>

            <div className="p-4 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(fhirModalContent);
                  showNotification('success', 'FHIR R4 JSON copied to clipboard.');
                }}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors"
              >
                Copy FHIR JSON
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
