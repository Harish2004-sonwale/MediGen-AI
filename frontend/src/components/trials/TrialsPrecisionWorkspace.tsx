import React, { useEffect, useMemo, useState } from 'react';
import {
  BiomarkerObservation,
  ClinicalTrial,
  ClinicalTrialDetail,
  ClinicianReviewStatus,
  CriterionEvaluationResult,
  GenomicProfileDetail,
  MatchStatus,
  Patient,
  PrecisionEligibilityStatus,
  PrecisionTreatmentEligibility,
  TrialMatch,
} from '../../types';
import { patientsApi, trialsApi } from '../../api/client';

interface TrialsPrecisionWorkspaceProps {
  initialPatientId?: string;
}

export const TrialsPrecisionWorkspace: React.FC<TrialsPrecisionWorkspaceProps> = ({ initialPatientId }) => {
  // Navigation & Sub-views
  const [activeTab, setActiveTab] = useState<'matching' | 'genomics' | 'precision' | 'registry'>('matching');

  // Patient Context
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>(initialPatientId || '');
  const [loadingPatients, setLoadingPatients] = useState<boolean>(false);

  // Data States
  const [trialMatches, setTrialMatches] = useState<TrialMatch[]>([]);
  const [genomicProfiles, setGenomicProfiles] = useState<GenomicProfileDetail[]>([]);
  const [precisionEligibilities, setPrecisionEligibilities] = useState<PrecisionTreatmentEligibility[]>([]);
  const [trialsRegistry, setTrialsRegistry] = useState<ClinicalTrial[]>([]);
  const [selectedTrialDetail, setSelectedTrialDetail] = useState<ClinicalTrialDetail | null>(null);

  // Loading & Processing States
  const [loading, setLoading] = useState<boolean>(false);
  const [matchingInProgress, setMatchingInProgress] = useState<boolean>(false);
  const [actionSuccessMessage, setActionSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Modals & Drawers
  const [selectedMatchForEvidence, setSelectedMatchForEvidence] = useState<TrialMatch | null>(null);
  const [reviewModalMatch, setReviewModalMatch] = useState<TrialMatch | null>(null);
  const [reviewModalPrecision, setReviewModalPrecision] = useState<PrecisionTreatmentEligibility | null>(null);
  const [selectedReviewStatus, setSelectedReviewStatus] = useState<ClinicianReviewStatus>('confirmed_eligible');
  const [reviewNotes, setReviewNotes] = useState<string>('');
  const [submittingReview, setSubmittingReview] = useState<boolean>(false);

  // Filtering
  const [matchStatusFilter, setMatchStatusFilter] = useState<string>('ALL');
  const [trialSearchQuery, setTrialSearchQuery] = useState<string>('');

  // 1. Load initial patients and registry trials
  useEffect(() => {
    loadPatients();
    loadTrialsRegistry();
  }, []);

  // 2. Load patient data when active patient changes
  useEffect(() => {
    if (selectedPatientId) {
      loadPatientData(selectedPatientId);
    }
  }, [selectedPatientId]);

  const loadPatients = async () => {
    setLoadingPatients(true);
    try {
      const items = await patientsApi.list();
      setPatients(items);
      if (!selectedPatientId && items.length > 0) {
        setSelectedPatientId(items[0].patient_id);
      }
    } catch (err: any) {
      console.error('Failed to load patients list', err);
    } finally {
      setLoadingPatients(false);
    }
  };


  const loadTrialsRegistry = async () => {
    try {
      const res = await trialsApi.listTrials();
      setTrialsRegistry(res.items);
    } catch (err: any) {
      console.error('Failed to load clinical trials registry', err);
    }
  };

  const loadPatientData = async (patientId: string) => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const [matchesRes, profilesRes, precRes] = await Promise.all([
        trialsApi.listPatientTrialMatches(patientId),
        trialsApi.listPatientGenomicProfiles(patientId),
        trialsApi.listPatientPrecisionEligibility(patientId),
      ]);
      setTrialMatches(matchesRes.items);
      setGenomicProfiles(profilesRes.items);
      setPrecisionEligibilities(precRes.items);
    } catch (err: any) {
      console.error('Failed to load precision data for patient', err);
      setErrorMessage(err.message || 'Failed to load patient genomic and trial data.');
    } finally {
      setLoading(false);
    }
  };

  // Run Batch Matching
  const handleRunBatchMatching = async () => {
    if (!selectedPatientId) return;
    setMatchingInProgress(true);
    setErrorMessage(null);
    try {
      const res = await trialsApi.batchMatchPatient(selectedPatientId);
      setTrialMatches(res.matches);
      setActionSuccessMessage(
        `Batch matching complete! Evaluated ${res.total_evaluated_trials} trials: ${res.matched_trials_count} matched, ${res.potential_trials_count} potential.`
      );
      setTimeout(() => setActionSuccessMessage(null), 6000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to execute deterministic trial matching.');
    } finally {
      setMatchingInProgress(false);
    }
  };

  // Synthesize Precision Treatment Eligibility
  const handleSynthesizePrecisionOncology = async () => {
    if (!selectedPatientId) return;
    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await trialsApi.evaluatePrecisionEligibility(selectedPatientId);
      setPrecisionEligibilities(res.items);
      setActionSuccessMessage(`Generated ${res.total} precision oncology treatment eligibility recommendations.`);
      setTimeout(() => setActionSuccessMessage(null), 6000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to evaluate precision treatment eligibility.');
    } finally {
      setLoading(false);
    }
  };

  // Clinician Sign-off / Review on Trial Match
  const handleConfirmMatchReview = async () => {
    if (!reviewModalMatch) return;
    setSubmittingReview(true);
    try {
      const updated = await trialsApi.reviewTrialMatch(reviewModalMatch.match_id, {
        clinician_review_status: selectedReviewStatus,
        review_notes: reviewNotes,
      });
      setTrialMatches((prev) => prev.map((m) => (m.match_id === updated.match_id ? updated : m)));
      setReviewModalMatch(null);
      setReviewNotes('');
      setActionSuccessMessage(`Clinician review recorded: ${updated.clinician_review_status}`);
      setTimeout(() => setActionSuccessMessage(null), 5000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to submit clinician match review.');
    } finally {
      setSubmittingReview(false);
    }
  };

  // Clinician Sign-off on Precision Eligibility
  const handleConfirmPrecisionReview = async () => {
    if (!reviewModalPrecision) return;
    setSubmittingReview(true);
    try {
      const updated = await trialsApi.reviewPrecisionEligibility(reviewModalPrecision.eligibility_id, {
        clinician_review_status: selectedReviewStatus,
        review_notes: reviewNotes,
      });
      setPrecisionEligibilities((prev) => prev.map((p) => (p.eligibility_id === updated.eligibility_id ? updated : p)));
      setReviewModalPrecision(null);
      setReviewNotes('');
      setActionSuccessMessage(`Precision protocol review saved: ${updated.clinician_review_status}`);
      setTimeout(() => setActionSuccessMessage(null), 5000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to submit precision treatment review.');
    } finally {
      setSubmittingReview(false);
    }
  };

  // Filtered trial matches
  const filteredMatches = useMemo(() => {
    return trialMatches.filter((m) => {
      if (matchStatusFilter !== 'ALL' && m.match_status !== matchStatusFilter) return false;
      if (trialSearchQuery) {
        const q = trialSearchQuery.toLowerCase();
        const title = (m.trial_title || '').toLowerCase();
        const condition = (m.disease_condition || '').toLowerCase();
        const intervention = (m.intervention_name || '').toLowerCase();
        const tid = (m.trial_identifier || '').toLowerCase();
        if (!title.includes(q) && !condition.includes(q) && !intervention.includes(q) && !tid.includes(q)) {
          return false;
        }
      }
      return true;
    });
  }, [trialMatches, matchStatusFilter, trialSearchQuery]);

  // Selected Patient Object
  const selectedPatient = useMemo(() => {
    return patients.find((p) => p.patient_id === selectedPatientId) || null;
  }, [patients, selectedPatientId]);

  // Match Status Badge Helper
  const renderMatchStatusBadge = (status: MatchStatus) => {
    switch (status) {
      case 'MATCHED':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">✅ MATCHED (100%)</span>;
      case 'POTENTIAL_MATCH':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-800 border border-amber-300">🟡 POTENTIAL MATCH</span>;
      case 'INSUFFICIENT_DATA':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-indigo-100 text-indigo-800 border border-indigo-300">ℹ️ INSUFFICIENT DATA</span>;
      case 'MANUAL_REVIEW':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-purple-100 text-purple-800 border border-purple-300">🔍 MANUAL REVIEW</span>;
      case 'INELIGIBLE':
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-rose-100 text-rose-800 border border-rose-300">❌ INELIGIBLE</span>;
      default:
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800 border border-gray-300">{status}</span>;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto p-4 sm:p-6" data-testid="trials-precision-workspace">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-teal-900 via-indigo-950 to-slate-900 rounded-2xl p-6 text-white shadow-xl border border-teal-800/40 relative overflow-hidden">
        <div className="absolute right-0 top-0 w-96 h-96 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="px-2.5 py-0.5 text-xs font-medium tracking-wider uppercase bg-teal-400/20 text-teal-300 rounded-full border border-teal-400/30">
                Phase 9.0.16 Precision Oncology
              </span>
              <span className="text-xs text-gray-300">Deterministic Engine v2026.1</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>🧬</span> Clinical Trials Matching & Biomarker Precision Oncology
            </h1>
            <p className="text-sm text-teal-100/80 mt-1 max-w-2xl">
              Deterministic rule-based clinical trial eligibility evaluation, genomic NGS panel profiling, and auditable assistive precision treatment decision support.
            </p>
          </div>

          {/* Patient Selection Dropdown */}
          <div className="bg-white/10 backdrop-blur-md rounded-xl p-3 border border-white/20 flex flex-col gap-1.5 min-w-[260px]">
            <label className="text-xs font-medium text-teal-200 uppercase tracking-wider">Active Patient Context</label>
            <select
              data-testid="patient-selector"
              value={selectedPatientId}
              onChange={(e) => setSelectedPatientId(e.target.value)}
              className="bg-slate-900 text-white text-sm rounded-lg px-3 py-2 border border-teal-500/40 focus:outline-none focus:ring-2 focus:ring-teal-400"
            >
              {patients.map((p) => (
                <option key={p.id} value={p.patient_id}>
                  {p.first_name} {p.last_name} ({p.patient_id})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Selected Patient Mini Summary Bar */}
        {selectedPatient && (
          <div className="mt-4 pt-4 border-t border-white/10 flex flex-wrap items-center gap-4 text-xs text-teal-200/90">
            <div><span className="text-gray-400">DOB:</span> {selectedPatient.date_of_birth}</div>
            <div><span className="text-gray-400">Gender:</span> {selectedPatient.gender}</div>
            <div><span className="text-gray-400">Genomic Panels:</span> <span className="font-semibold text-white">{genomicProfiles.length}</span></div>
            <div><span className="text-gray-400">Trial Matches:</span> <span className="font-semibold text-white">{trialMatches.length}</span></div>
            <div><span className="text-gray-400">Precision Therapies:</span> <span className="font-semibold text-white">{precisionEligibilities.length}</span></div>
          </div>
        )}
      </div>

      {/* Decision Support Assistive Notice */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex items-start gap-3 text-amber-900 text-sm">
        <span className="text-lg">⚠️</span>
        <div>
          <span className="font-semibold">Clinical Decision Support Disclaimer:</span> Trial matching and precision oncology recommendations provided by MediGen-AI are deterministic assistive decision support only. They do not constitute autonomous medical prescription or enrollment and require independent clinician validation, review notes, and signed approval.
        </div>
      </div>

      {/* Alerts */}
      {actionSuccessMessage && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-3 text-emerald-800 text-sm flex items-center justify-between">
          <span>{actionSuccessMessage}</span>
          <button onClick={() => setActionSuccessMessage(null)} className="text-emerald-700 hover:text-emerald-950 text-xs font-bold">✕</button>
        </div>
      )}

      {errorMessage && (
        <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-3 text-rose-800 text-sm flex items-center justify-between">
          <span>{errorMessage}</span>
          <button onClick={() => setErrorMessage(null)} className="text-rose-700 hover:text-rose-950 text-xs font-bold">✕</button>
        </div>
      )}

      {/* Sub-Navigation Tabs */}
      <div className="flex border-b border-gray-200 space-x-4">
        <button
          data-testid="tab-matching"
          onClick={() => setActiveTab('matching')}
          className={`py-2.5 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'matching'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          <span>🎯</span> Trial Matching Hub ({trialMatches.length})
        </button>

        <button
          data-testid="tab-genomics"
          onClick={() => setActiveTab('genomics')}
          className={`py-2.5 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'genomics'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          <span>🧪</span> Genomic Profiles & Biomarkers ({genomicProfiles.length})
        </button>

        <button
          data-testid="tab-precision"
          onClick={() => setActiveTab('precision')}
          className={`py-2.5 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'precision'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          <span>💊</span> Precision Oncology Eligibility ({precisionEligibilities.length})
        </button>

        <button
          data-testid="tab-registry"
          onClick={() => setActiveTab('registry')}
          className={`py-2.5 px-4 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'registry'
              ? 'border-teal-600 text-teal-700'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          <span>📚</span> Clinical Trials Registry ({trialsRegistry.length})
        </button>
      </div>

      {/* ========================================================================= */}
      {/* TAB 1: TRIAL MATCHING HUB */}
      {/* ========================================================================= */}
      {activeTab === 'matching' && (
        <div className="space-y-6" data-testid="matching-hub-tab">
          {/* Action & Filter Controls */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              <button
                data-testid="btn-batch-match"
                onClick={handleRunBatchMatching}
                disabled={matchingInProgress || !selectedPatientId}
                className="bg-teal-700 hover:bg-teal-800 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg shadow-sm flex items-center gap-2 transition"
              >
                {matchingInProgress ? (
                  <>
                    <span className="animate-spin">🔄</span>
                    Evaluating Eligibility Criteria...
                  </>
                ) : (
                  <>
                    <span>⚡</span>
                    Run Batch Clinical Trial Matching
                  </>
                )}
              </button>

              <div className="flex items-center gap-2">
                <label className="text-xs font-semibold text-gray-600">Match Status:</label>
                <select
                  value={matchStatusFilter}
                  onChange={(e) => setMatchStatusFilter(e.target.value)}
                  className="text-xs border border-gray-300 rounded-lg px-2.5 py-1.5 focus:ring-teal-500 focus:border-teal-500"
                >
                  <option value="ALL">All Statuses ({trialMatches.length})</option>
                  <option value="MATCHED">Matched</option>
                  <option value="POTENTIAL_MATCH">Potential Match</option>
                  <option value="MANUAL_REVIEW">Manual Review</option>
                  <option value="INELIGIBLE">Ineligible</option>
                  <option value="INSUFFICIENT_DATA">Insufficient Data</option>
                </select>
              </div>
            </div>

            <div className="w-full md:w-64">
              <input
                type="text"
                placeholder="Search trial title, condition..."
                value={trialSearchQuery}
                onChange={(e) => setTrialSearchQuery(e.target.value)}
                className="w-full text-xs border border-gray-300 rounded-lg px-3 py-2 focus:ring-teal-500 focus:border-teal-500"
              />
            </div>
          </div>

          {/* Match Scorecards Grid */}
          {filteredMatches.length === 0 ? (
            <div className="text-center py-12 bg-white rounded-xl border border-dashed border-gray-300">
              <span className="text-3xl">🔍</span>
              <h3 className="text-base font-semibold text-gray-800 mt-2">No Clinical Trial Matches Found</h3>
              <p className="text-xs text-gray-500 mt-1">
                {trialMatches.length === 0
                  ? 'Click "Run Batch Clinical Trial Matching" above to evaluate active protocols against patient genomics and clinical history.'
                  : 'No matches meet the active search or status filter.'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4" data-testid="trial-matches-list">
              {filteredMatches.map((m) => (
                <div
                  key={m.match_id}
                  data-testid={`match-card-${m.trial_identifier}`}
                  className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition space-y-4"
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 border-b border-gray-100 pb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                          {m.trial_identifier}
                        </span>
                        <span className="text-xs font-medium text-gray-500 capitalize">{m.trial_phase?.replace('_', ' ')}</span>
                        <span className="text-xs font-medium text-gray-400">• Sponsor: {m.trial_sponsor}</span>
                      </div>
                      <h2 className="text-base font-bold text-gray-900 mt-1">{m.trial_title}</h2>
                      <div className="flex flex-wrap items-center gap-3 text-xs text-gray-600 mt-1">
                        <div><span className="font-semibold text-gray-700">Condition:</span> {m.disease_condition}</div>
                        <div><span className="font-semibold text-gray-700">Intervention:</span> {m.intervention_name}</div>
                      </div>
                    </div>

                    <div className="flex flex-col sm:items-end gap-1.5">
                      {renderMatchStatusBadge(m.match_status)}
                      <div className="text-xs font-semibold text-gray-700">
                        Score: <span className="text-teal-700 font-bold">{m.match_score.toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>

                  {/* Summary Explanation */}
                  <p className="text-xs text-gray-700 bg-gray-50 p-2.5 rounded-lg border border-gray-100">
                    {m.overall_explanation}
                  </p>

                  {/* Criteria Breakdown Chips */}
                  <div className="space-y-2">
                    <div className="text-xs font-semibold text-gray-700">Criteria Evaluation Breakdown:</div>
                    <div className="flex flex-wrap gap-2">
                      {(m.matched_criteria_json || []).map((c, idx) => (
                        <span
                          key={`pass-${idx}`}
                          className="px-2 py-1 text-xs rounded bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center gap-1"
                        >
                          <span>✓</span>
                          <span>{c.description || c.field_name}</span>
                        </span>
                      ))}

                      {(m.failed_criteria_json || []).map((c, idx) => (
                        <span
                          key={`fail-${idx}`}
                          className="px-2 py-1 text-xs rounded bg-rose-50 text-rose-800 border border-rose-200 flex items-center gap-1"
                        >
                          <span>✕</span>
                          <span>{c.description || c.field_name}</span>
                        </span>
                      ))}

                      {(m.unknown_criteria_json || []).map((c, idx) => (
                        <span
                          key={`unk-${idx}`}
                          className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-700 border border-gray-200 flex items-center gap-1"
                        >
                          <span>?</span>
                          <span>{c.description || c.field_name}</span>
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Clinician Review & Audit Provenance Footer */}
                  <div className="pt-3 border-t border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-gray-600">Clinician Review:</span>
                      <span className="px-2 py-0.5 rounded font-medium bg-slate-100 text-slate-800 capitalize">
                        {m.clinician_review_status.replace(/_/g, ' ')}
                      </span>
                      {m.reviewed_by_name && <span className="text-gray-500">by {m.reviewed_by_name}</span>}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        data-testid={`btn-evidence-${m.trial_identifier}`}
                        onClick={() => setSelectedMatchForEvidence(m)}
                        className="text-teal-700 hover:text-teal-900 font-semibold px-2.5 py-1 rounded bg-teal-50 border border-teal-200 transition"
                      >
                        Explainability & Audit Hash
                      </button>

                      <button
                        data-testid={`btn-review-${m.trial_identifier}`}
                        onClick={() => {
                          setReviewModalMatch(m);
                          setSelectedReviewStatus(m.clinician_review_status || 'confirmed_eligible');
                          setReviewNotes(m.review_notes || '');
                        }}
                        className="text-white bg-slate-800 hover:bg-slate-900 font-semibold px-3 py-1 rounded transition"
                      >
                        Clinician Sign-off
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 2: GENOMIC PROFILES & BIOMARKERS */}
      {/* ========================================================================= */}
      {activeTab === 'genomics' && (
        <div className="space-y-6" data-testid="genomics-tab">
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-bold text-gray-900">Next-Generation Sequencing (NGS) Genomic Profiles</h2>
                <p className="text-xs text-gray-500">Structured molecular pathology reports and actionable biomarker alterations.</p>
              </div>
            </div>

            {genomicProfiles.length === 0 ? (
              <div className="text-center py-8 text-xs text-gray-500 border border-dashed border-gray-200 rounded-lg">
                No genomic sequencing panels recorded for this patient.
              </div>
            ) : (
              <div className="space-y-4">
                {genomicProfiles.map((prof) => (
                  <div key={prof.profile_id} className="border border-gray-200 rounded-lg p-4 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 pb-2">
                      <div>
                        <span className="font-mono text-xs font-bold text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                          {prof.profile_id}
                        </span>
                        <span className="font-semibold text-sm text-gray-900 ml-2">{prof.test_name}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <span className="bg-indigo-50 text-indigo-800 px-2 py-0.5 rounded border border-indigo-200">
                          TMB: {prof.tumor_mutation_burden !== undefined ? `${prof.tumor_mutation_burden} mut/Mb` : 'N/A'}
                        </span>
                        <span className="bg-purple-50 text-purple-800 px-2 py-0.5 rounded border border-purple-200">
                          MSI: {prof.microsatellite_instability_status || 'MSS'}
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-gray-700 italic bg-gray-50 p-2 rounded">
                      Interpretation: {prof.overall_interpretation || 'No overall clinical interpretation documented.'}
                    </p>

                    {/* Biomarkers Table */}
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs text-gray-600">
                        <thead className="bg-gray-100 text-gray-700 uppercase font-semibold text-[10px]">
                          <tr>
                            <th className="py-2 px-3">Gene</th>
                            <th className="py-2 px-3">Variant</th>
                            <th className="py-2 px-3">Type</th>
                            <th className="py-2 px-3">Expression / VAF</th>
                            <th className="py-2 px-3">Pathogenicity Tier</th>
                            <th className="py-2 px-3">Evidence Level</th>
                            <th className="py-2 px-3">Clinical Actionability</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {(prof.biomarkers || []).map((bm) => (
                            <tr key={bm.observation_id} className="hover:bg-gray-50">
                              <td className="py-2 px-3 font-bold text-gray-900">{bm.gene_symbol}</td>
                              <td className="py-2 px-3 font-mono font-semibold text-teal-800">{bm.variant_name}</td>
                              <td className="py-2 px-3 capitalize">{bm.alteration_type.replace(/_/g, ' ')}</td>
                              <td className="py-2 px-3 font-semibold text-gray-800">
                                {bm.numeric_expression_value !== undefined && bm.numeric_expression_value !== null
                                  ? `${bm.numeric_expression_value} ${bm.expression_unit || '%'}`
                                  : bm.variant_allele_fraction !== undefined && bm.variant_allele_fraction !== null
                                  ? `${bm.variant_allele_fraction}% VAF`
                                  : '—'}
                              </td>
                              <td className="py-2 px-3">
                                <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
                                  {bm.pathogenicity.replace(/_/g, ' ')}
                                </span>
                              </td>
                              <td className="py-2 px-3 font-medium text-purple-700">{bm.evidence_level}</td>
                              <td className="py-2 px-3 text-gray-800">{bm.clinical_significance || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 3: PRECISION ONCOLOGY ELIGIBILITY */}
      {/* ========================================================================= */}
      {activeTab === 'precision' && (
        <div className="space-y-6" data-testid="precision-tab">
          <div className="flex items-center justify-between bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
            <div>
              <h2 className="text-base font-bold text-gray-900">Precision Oncology Targeted Therapy Syntheses</h2>
              <p className="text-xs text-gray-500">
                Actionable molecular therapy recommendations matched against NCCN guidelines and FDA-approved precision labels.
              </p>
            </div>
            <button
              data-testid="btn-synthesize-precision"
              onClick={handleSynthesizePrecisionOncology}
              disabled={loading || !selectedPatientId}
              className="bg-indigo-700 hover:bg-indigo-800 disabled:opacity-50 text-white text-xs font-semibold px-3.5 py-2 rounded-lg shadow-sm transition flex items-center gap-2"
            >
              <span>🔬</span>
              Synthesize Targeted Protocols
            </button>
          </div>

          {precisionEligibilities.length === 0 ? (
            <div className="text-center py-10 bg-white rounded-xl border border-dashed border-gray-300">
              <span className="text-2xl">💊</span>
              <h3 className="text-sm font-semibold text-gray-800 mt-2">No Precision Treatment Recommendations</h3>
              <p className="text-xs text-gray-500 mt-1">
                Click "Synthesize Targeted Protocols" to evaluate actionable therapies against patient biomarker observations.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {precisionEligibilities.map((pe) => (
                <div
                  key={pe.eligibility_id}
                  className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-3"
                  data-testid={`precision-card-${pe.gene_symbol}`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-100 pb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded bg-indigo-50 text-indigo-800 border border-indigo-200 font-mono text-xs font-bold">
                          {pe.gene_symbol} {pe.variant_name}
                        </span>
                        <span className="text-xs font-medium text-gray-500">{pe.drug_class}</span>
                      </div>
                      <h3 className="text-base font-bold text-gray-900 mt-1">{pe.recommended_intervention}</h3>
                      <p className="text-xs text-gray-600"><span className="font-semibold">Indication:</span> {pe.indication}</p>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                        {pe.eligibility_status}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <div>
                      <span className="font-semibold text-gray-700">Evidence Source:</span>
                      <p className="text-gray-600 mt-0.5">{pe.evidence_source}</p>
                    </div>
                    <div>
                      <span className="font-semibold text-gray-700">Audit Provenance Hash:</span>
                      <p className="font-mono text-[10px] text-gray-500 break-all mt-0.5">{pe.provenance_hash}</p>
                    </div>
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-gray-100 text-xs">
                    <div>
                      <span className="font-semibold text-gray-600">Review Status:</span>{' '}
                      <span className="font-medium capitalize text-slate-800">{pe.clinician_review_status.replace(/_/g, ' ')}</span>
                      {pe.reviewed_by_name && <span className="text-gray-500 ml-1">by {pe.reviewed_by_name}</span>}
                    </div>

                    <button
                      onClick={() => {
                        setReviewModalPrecision(pe);
                        setSelectedReviewStatus(pe.clinician_review_status || 'approved_for_protocol');
                        setReviewNotes(pe.review_notes || '');
                      }}
                      className="text-white bg-indigo-700 hover:bg-indigo-800 font-semibold px-3 py-1 rounded transition text-xs"
                    >
                      Clinician Protocol Review
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* TAB 4: CLINICAL TRIALS REGISTRY */}
      {/* ========================================================================= */}
      {activeTab === 'registry' && (
        <div className="space-y-6" data-testid="registry-tab">
          <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm space-y-3">
            <h2 className="text-base font-bold text-gray-900">Standard Clinical Trials Protocol Registry</h2>
            <p className="text-xs text-gray-500">
              Active precision oncology and targeted therapy clinical trials available for automated cohort matching.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {trialsRegistry.map((tr) => (
                <div key={tr.trial_id} className="border border-gray-200 rounded-lg p-4 space-y-2 hover:border-teal-400 transition">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                      {tr.trial_id}
                    </span>
                    <span className="text-xs font-semibold capitalize text-gray-600">{tr.phase?.replace('_', ' ')}</span>
                  </div>
                  <h3 className="text-sm font-bold text-gray-900">{tr.title}</h3>
                  <p className="text-xs text-gray-600"><span className="font-semibold">Condition:</span> {tr.disease_condition}</p>
                  <p className="text-xs text-gray-600"><span className="font-semibold">Intervention:</span> {tr.intervention_name}</p>
                  <p className="text-xs text-gray-500 italic line-clamp-2">{tr.summary}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 1: EXPLAINABILITY & PROVENANCE DRAWER */}
      {/* ========================================================================= */}
      {selectedMatchForEvidence && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="evidence-modal">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl border border-gray-100 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <span className="text-xs font-mono text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                  {selectedMatchForEvidence.trial_identifier}
                </span>
                <h3 className="text-lg font-bold text-gray-900 mt-1">Audit Trail & Criterion Explainability</h3>
              </div>
              <button
                onClick={() => setSelectedMatchForEvidence(null)}
                className="text-gray-400 hover:text-gray-700 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="bg-slate-50 p-3 rounded-lg border">
                <div className="font-semibold text-gray-700">Cryptographic Audit Provenance SHA-256 Hash:</div>
                <div className="font-mono text-teal-800 break-all mt-1 bg-white p-2 rounded border">
                  {selectedMatchForEvidence.provenance_hash}
                </div>
                <div className="text-gray-500 mt-1">Engine Version: {selectedMatchForEvidence.algorithm_version}</div>
              </div>

              <div>
                <h4 className="font-bold text-sm text-gray-800 mb-2">Evaluated Criteria & Decision Rules:</h4>
                <div className="space-y-2">
                  {[
                    ...(selectedMatchForEvidence.matched_criteria_json || []),
                    ...(selectedMatchForEvidence.failed_criteria_json || []),
                    ...(selectedMatchForEvidence.unknown_criteria_json || []),
                  ].map((crit: CriterionEvaluationResult, i) => (
                    <div
                      key={i}
                      className={`p-3 rounded-lg border text-xs space-y-1 ${
                        crit.status === 'PASS'
                          ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
                          : crit.status === 'FAIL'
                          ? 'bg-rose-50/70 border-rose-200 text-rose-900'
                          : 'bg-gray-50 border-gray-200 text-gray-800'
                      }`}
                    >
                      <div className="flex items-center justify-between font-bold">
                        <span>{crit.description}</span>
                        <span className="uppercase text-[10px] px-2 py-0.5 rounded bg-white font-mono">{crit.status}</span>
                      </div>
                      <div className="text-[11px]"><span className="font-semibold">Evidence:</span> {crit.evidence}</div>
                      <div className="text-[11px]"><span className="font-semibold">Reasoning:</span> {crit.reason}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-3 border-t flex justify-end">
              <button
                onClick={() => setSelectedMatchForEvidence(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold rounded-lg"
              >
                Close Audit View
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 2: CLINICIAN TRIAL MATCH SIGN-OFF */}
      {/* ========================================================================= */}
      {reviewModalMatch && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="review-modal">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl border border-gray-100">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-base font-bold text-gray-900">Clinician Trial Match Review & Sign-Off</h3>
              <button onClick={() => setReviewModalMatch(null)} className="text-gray-400 hover:text-gray-700">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="font-semibold text-gray-700">Protocol:</span> {reviewModalMatch.trial_title} ({reviewModalMatch.trial_identifier})
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Select Clinician Determination:</label>
                <select
                  data-testid="select-review-status"
                  value={selectedReviewStatus}
                  onChange={(e) => setSelectedReviewStatus(e.target.value as ClinicianReviewStatus)}
                  className="w-full border border-gray-300 rounded-lg p-2 text-xs focus:ring-teal-500 focus:border-teal-500"
                >
                  <option value="confirmed_eligible">Confirmed Eligible for Screening</option>
                  <option value="enrolled_in_trial">Enrolled in Trial Protocol</option>
                  <option value="declined_by_clinician">Declined by Clinician (Contraindication / Alternative Protocol)</option>
                  <option value="patient_declined">Patient Declined Enrollment</option>
                  <option value="pending_review">Pending Review</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Clinician Review Notes & Justification:</label>
                <textarea
                  data-testid="textarea-review-notes"
                  rows={3}
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="Document clinical rationale, eligibility confirmation, or patient preferences..."
                  className="w-full border border-gray-300 rounded-lg p-2 text-xs focus:ring-teal-500 focus:border-teal-500"
                />
              </div>
            </div>

            <div className="pt-3 border-t flex justify-end gap-2 text-xs">
              <button
                onClick={() => setReviewModalMatch(null)}
                className="px-3 py-2 border rounded-lg hover:bg-gray-50 text-gray-700 font-semibold"
              >
                Cancel
              </button>
              <button
                data-testid="btn-submit-review"
                onClick={handleConfirmMatchReview}
                disabled={submittingReview}
                className="px-4 py-2 bg-teal-700 hover:bg-teal-800 text-white rounded-lg font-semibold disabled:opacity-50"
              >
                {submittingReview ? 'Saving Sign-off...' : 'Sign & Submit Review'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* MODAL 3: CLINICIAN PRECISION THERAPY PROTOCOL SIGN-OFF */}
      {/* ========================================================================= */}
      {reviewModalPrecision && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl border border-gray-100">
            <div className="flex items-center justify-between border-b pb-3">
              <h3 className="text-base font-bold text-gray-900">Precision Oncology Protocol Sign-Off</h3>
              <button onClick={() => setReviewModalPrecision(null)} className="text-gray-400 hover:text-gray-700">✕</button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="font-semibold text-gray-700">Intervention:</span> {reviewModalPrecision.recommended_intervention}
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Determination:</label>
                <select
                  value={selectedReviewStatus}
                  onChange={(e) => setSelectedReviewStatus(e.target.value as ClinicianReviewStatus)}
                  className="w-full border border-gray-300 rounded-lg p-2 text-xs focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="approved_for_protocol">Approve for Treatment Protocol</option>
                  <option value="rejected_by_clinician">Reject / Defer Recommendation</option>
                  <option value="pending_review">Pending Review</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-gray-700 mb-1">Clinical Notes:</label>
                <textarea
                  rows={3}
                  value={reviewNotes}
                  onChange={(e) => setReviewNotes(e.target.value)}
                  placeholder="Document protocol dosage, line of therapy, or clinical notes..."
                  className="w-full border border-gray-300 rounded-lg p-2 text-xs focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="pt-3 border-t flex justify-end gap-2 text-xs">
              <button
                onClick={() => setReviewModalPrecision(null)}
                className="px-3 py-2 border rounded-lg hover:bg-gray-50 text-gray-700 font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmPrecisionReview}
                disabled={submittingReview}
                className="px-4 py-2 bg-indigo-700 hover:bg-indigo-800 text-white rounded-lg font-semibold disabled:opacity-50"
              >
                {submittingReview ? 'Saving Protocol...' : 'Save Decision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
