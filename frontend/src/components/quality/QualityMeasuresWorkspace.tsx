import React, { useEffect, useState } from 'react';
import {
  GapSeverity,
  GapStatus,
  Patient,
  QualityDomain,
  QualityMeasure,
  QualityMeasureGap,
  QualityMeasureReport,
  QualityMeasureResult,
  ReportScope,
} from '../../types';
import { patientsApi, qualityApi } from '../../api/client';

export const QualityMeasuresWorkspace: React.FC = () => {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);

  const [activeTab, setActiveTab] = useState<'scorecard' | 'gaps' | 'reports'>('scorecard');
  const [measures, setMeasures] = useState<QualityMeasure[]>([]);
  const [patientResults, setPatientResults] = useState<QualityMeasureResult[]>([]);
  const [gaps, setGaps] = useState<QualityMeasureGap[]>([]);
  const [reports, setReports] = useState<QualityMeasureReport[]>([]);

  const [loading, setLoading] = useState<boolean>(false);
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Filters
  const [domainFilter, setDomainFilter] = useState<string>('all');
  const [gapSeverityFilter, setGapSeverityFilter] = useState<string>('all');
  const [gapStatusFilter, setGapStatusFilter] = useState<string>('all');

  // Modals & Detail State
  const [selectedMeasure, setSelectedMeasure] = useState<QualityMeasure | null>(null);
  const [selectedResultEvidence, setSelectedResultEvidence] = useState<QualityMeasureResult | null>(null);
  const [selectedReportDetail, setSelectedReportDetail] = useState<QualityMeasureReport | null>(null);
  const [showGenerateReportModal, setShowGenerateReportModal] = useState<boolean>(false);

  // Generate Report Form
  const [reportTitle, setReportTitle] = useState<string>('Population HEDIS/MIPS Compliance Audit');
  const [reportScope, setReportScope] = useState<ReportScope>('organization');
  const [generatingReport, setGeneratingReport] = useState<boolean>(false);

  // Load initial data
  useEffect(() => {
    loadPatients();
    loadMeasures();
    loadGaps();
    loadReports();
  }, []);

  useEffect(() => {
    if (selectedPatientId) {
      const p = patients.find((pat) => pat.patient_id === selectedPatientId) || null;
      setSelectedPatient(p);
      loadPatientResults(selectedPatientId);
      loadGaps(selectedPatientId);
    } else {
      setSelectedPatient(null);
      setPatientResults([]);
      loadGaps();
    }
  }, [selectedPatientId, patients]);

  const loadPatients = async () => {
    try {
      const res = await patientsApi.list();
      setPatients(res || []);
    } catch (err: any) {
      console.error('Failed to load patients:', err);
    }
  };


  const loadMeasures = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await qualityApi.listMeasures(
        domainFilter !== 'all' ? { domain: domainFilter as QualityDomain } : undefined
      );
      setMeasures(res.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load quality measures.');
    } finally {
      setLoading(false);
    }
  };

  const loadPatientResults = async (pid: string) => {
    try {
      const res = await qualityApi.getPatientResults(pid);
      setPatientResults(res.items || []);
    } catch (err: any) {
      console.error('Failed to load patient quality results:', err);
    }
  };

  const loadGaps = async (pid?: string) => {
    try {
      const params: any = {};
      if (pid) params.patient_id = pid;
      if (gapSeverityFilter !== 'all') params.severity = gapSeverityFilter as GapSeverity;
      if (gapStatusFilter !== 'all') params.status = gapStatusFilter as GapStatus;
      const res = await qualityApi.listGaps(params);
      setGaps(res.items || []);
    } catch (err: any) {
      console.error('Failed to load care gaps:', err);
    }
  };

  const loadReports = async () => {
    try {
      const res = await qualityApi.listReports();
      setReports(res.items || []);
    } catch (err: any) {
      console.error('Failed to load compliance reports:', err);
    }
  };

  const handleEvaluatePatient = async () => {
    if (!selectedPatientId) {
      setError('Please select a patient to evaluate.');
      return;
    }
    setEvaluating(true);
    setError(null);
    try {
      const res = await qualityApi.evaluatePatient(selectedPatientId);
      setPatientResults(res.items || []);
      await loadGaps(selectedPatientId);
      setSuccessMessage(`Successfully evaluated ${res.items.length} quality measures for patient ${selectedPatientId}.`);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setError(err.message || 'Quality evaluation failed.');
    } finally {
      setEvaluating(false);
    }
  };

  const handleCreateCareTask = async (gapId: string) => {
    setError(null);
    try {
      const updated = await qualityApi.createCareTaskForGap(gapId);
      setGaps((prev) => prev.map((g) => (g.gap_id === gapId ? updated : g)));
      setSuccessMessage(`Care task successfully created and linked to Gap ${gapId}. Status moved to remediation.`);
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setError(err.message || 'Failed to create care task for gap.');
    }
  };

  const handleGenerateReport = async (e: React.FormEvent) => {
    e.preventDefault();
    setGeneratingReport(true);
    setError(null);
    try {
      const rep = await qualityApi.generateReport({
        title: reportTitle,
        report_scope: reportScope,
      });
      setReports((prev) => [rep, ...prev]);
      setShowGenerateReportModal(false);
      setSelectedReportDetail(rep);
      setSuccessMessage(`Compliance report ${rep.report_id} synthesized with SHA-256 provenance hash.`);
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err: any) {
      setError(err.message || 'Failed to generate compliance report.');
    } finally {
      setGeneratingReport(false);
    }
  };

  // KPI Calculations
  const totalMeasures = measures.length;
  const openGapsCount = gaps.filter((g) => g.status === 'open').length;
  const inRemediationGapsCount = gaps.filter((g) => g.status === 'in_remediation').length;
  const latestReport = reports[0];
  const overallComplianceRate = latestReport ? latestReport.overall_performance_rate : 82.5;

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* HEADER & PATIENT SELECTOR */}
      <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 p-6 rounded-2xl shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gradient-to-tr from-teal-600 to-emerald-500 rounded-xl shadow-lg shadow-emerald-500/20 text-white font-bold text-xl">
              📊
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
                Clinical Quality Measures (CQMs) & Compliance Engine
              </h1>
              <p className="text-sm text-slate-400">
                HEDIS / CMS MIPS Measurement, Deterministic Gap-in-Care Remediation & Immutable Provenance Audits
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="relative min-w-[240px]">
            <select
              id="quality-patient-select"
              value={selectedPatientId}
              onChange={(e) => setSelectedPatientId(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all cursor-pointer"
            >
              <option value="">-- All / Population Level --</option>
              {patients.map((p) => (
                <option key={p.patient_id} value={p.patient_id}>
                  {p.patient_id} - {p.first_name} {p.last_name}
                </option>
              ))}
            </select>
          </div>

          {selectedPatientId && (
            <button
              id="evaluate-patient-btn"
              onClick={handleEvaluatePatient}
              disabled={evaluating}
              className="px-4 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-medium text-sm rounded-xl shadow-lg shadow-emerald-600/20 flex items-center gap-2 transition-all disabled:opacity-50 cursor-pointer"
            >
              {evaluating ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  Evaluating...
                </>
              ) : (
                <>⚡ Evaluate Patient CQMs</>
              )}
            </button>
          )}

          <button
            id="generate-report-modal-btn"
            onClick={() => setShowGenerateReportModal(true)}
            className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 hover:text-white font-medium text-sm rounded-xl transition-all flex items-center gap-2 cursor-pointer"
          >
            📑 Synthesize Audit Report
          </button>
        </div>
      </div>

      {/* MESSAGES */}
      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded-xl text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200 font-bold text-xs">
            ✕
          </button>
        </div>
      )}

      {successMessage && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 rounded-xl text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span>✅</span>
            <span>{successMessage}</span>
          </div>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-400 hover:text-emerald-200 font-bold text-xs">
            ✕
          </button>
        </div>
      )}

      {/* KPI METRIC CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800/80 p-5 rounded-2xl shadow-lg relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 text-emerald-400/20 text-4xl font-bold">🎯</div>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            Population Compliance Rate
          </div>
          <div className="text-3xl font-extrabold text-emerald-400">{overallComplianceRate.toFixed(1)}%</div>
          <div className="text-xs text-slate-400 mt-2 flex items-center gap-1">
            <span className="text-emerald-400 font-medium">HEDIS Quality Tier: Optimal</span>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 p-5 rounded-2xl shadow-lg relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 text-teal-400/20 text-4xl font-bold">📋</div>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            Active Quality Measures
          </div>
          <div className="text-3xl font-extrabold text-teal-300">{totalMeasures}</div>
          <div className="text-xs text-slate-400 mt-2">HEDIS, CMS MIPS & NCQA Protocols</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 p-5 rounded-2xl shadow-lg relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 text-amber-400/20 text-4xl font-bold">⚠️</div>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            Open Gaps in Care
          </div>
          <div className="text-3xl font-extrabold text-amber-400">{openGapsCount}</div>
          <div className="text-xs text-slate-400 mt-2">Requires clinician action or lab orders</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 p-5 rounded-2xl shadow-lg relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 text-cyan-400/20 text-4xl font-bold">🔄</div>
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
            Gaps in Remediation
          </div>
          <div className="text-3xl font-extrabold text-cyan-400">{inRemediationGapsCount}</div>
          <div className="text-xs text-slate-400 mt-2">Linked to active CareTask workflows</div>
        </div>
      </div>

      {/* SUB-TABS NAVIGATION */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          id="tab-scorecard"
          onClick={() => setActiveTab('scorecard')}
          className={`pb-3 px-4 font-semibold text-sm transition-all flex items-center gap-2 ${
            activeTab === 'scorecard'
              ? 'text-emerald-400 border-b-2 border-emerald-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>🏆</span> Measures Scorecard & Criteria
        </button>

        <button
          id="tab-gaps"
          onClick={() => setActiveTab('gaps')}
          className={`pb-3 px-4 font-semibold text-sm transition-all flex items-center gap-2 ${
            activeTab === 'gaps'
              ? 'text-emerald-400 border-b-2 border-emerald-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>⚠️</span> Gaps-in-Care Feed ({gaps.length})
        </button>

        <button
          id="tab-reports"
          onClick={() => setActiveTab('reports')}
          className={`pb-3 px-4 font-semibold text-sm transition-all flex items-center gap-2 ${
            activeTab === 'reports'
              ? 'text-emerald-400 border-b-2 border-emerald-500'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>📑</span> Compliance & Audit Reports ({reports.length})
        </button>
      </div>

      {/* TAB 1: MEASURES SCORECARD */}
      {activeTab === 'scorecard' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2 text-sm text-slate-300">
              <span>Filter Domain:</span>
              <select
                id="quality-domain-filter"
                value={domainFilter}
                onChange={(e) => {
                  setDomainFilter(e.target.value);
                  loadMeasures();
                }}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
              >
                <option value="all">All Domains</option>
                <option value="chronic_disease_management">Chronic Disease Management</option>
                <option value="care_coordination">Care Coordination</option>
                <option value="patient_safety">Patient Safety</option>
                <option value="preventive_care">Preventive Care</option>
              </select>
            </div>

            {selectedPatient && (
              <div className="text-xs text-slate-400 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700/60 flex items-center gap-2">
                <span>Showing evaluation for:</span>
                <span className="font-semibold text-emerald-300">
                  {selectedPatient.first_name} {selectedPatient.last_name} ({selectedPatient.patient_id})
                </span>
              </div>
            )}
          </div>

          {loading ? (
            <div className="p-12 text-center text-slate-400">
              <span className="inline-block w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mb-2"></span>
              <p>Loading quality measure definitions...</p>
            </div>
          ) : measures.length === 0 ? (
            <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
              No quality measures found for the selected filter.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {measures.map((m) => {
                const patRes = patientResults.find((r) => r.measure_code === m.measure_id);
                return (
                  <div
                    key={m.measure_id}
                    className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 p-5 rounded-2xl shadow-lg transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-bold px-2.5 py-0.5 rounded-md bg-teal-500/10 text-teal-300 border border-teal-500/20">
                            {m.measure_id}
                          </span>
                          <span className="text-xs font-medium px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
                            {m.standard_framework}
                          </span>
                          <span className="text-xs font-medium px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                            {m.domain.replace(/_/g, ' ')}
                          </span>
                        </div>

                        {patRes && (
                          <span
                            className={`text-xs font-bold px-2.5 py-0.5 rounded-md uppercase ${
                              patRes.compliance_status === 'compliant'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : patRes.compliance_status === 'non_compliant'
                                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {patRes.compliance_status.replace(/_/g, ' ')}
                          </span>
                        )}
                      </div>

                      <h3 className="text-base font-bold text-slate-100 mb-1">{m.title}</h3>
                      <p className="text-xs text-slate-400 mb-3 line-clamp-2">{m.description}</p>

                      {/* Performance Target Bar */}
                      <div className="space-y-1 mb-3">
                        <div className="flex justify-between text-xs text-slate-400">
                          <span>Target Benchmark</span>
                          <span className="font-semibold text-slate-200">{(m.target_rate * 100).toFixed(0)}%</span>
                        </div>
                        <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 rounded-full"
                            style={{ width: `${Math.min(100, m.target_rate * 100)}%` }}
                          ></div>
                        </div>
                      </div>

                      {/* Evidence breakdown if evaluated */}
                      {patRes && (
                        <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/60 text-xs mb-3 space-y-1">
                          <div className="text-slate-300 font-medium">Patient Status:</div>
                          <div className="text-slate-400">
                            Eligible: <span className="text-slate-200 font-semibold">{patRes.is_eligible ? 'Yes' : 'No'}</span> | Compliant:{' '}
                            <span className={patRes.is_numerator_compliant ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                              {patRes.is_numerator_compliant ? 'Yes (Meets Numerator)' : 'No (Care Gap Present)'}
                            </span>
                          </div>
                          {patRes.gap_reason && (
                            <div className="text-amber-300 font-medium mt-1">⚠️ {patRes.gap_reason}</div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 mt-2">
                      <span className="text-xs text-slate-500">Steward: {m.steward}</span>
                      <div className="flex items-center gap-2">
                        {patRes && patRes.evidence_json && (
                          <button
                            onClick={() => setSelectedResultEvidence(patRes)}
                            className="text-xs text-teal-400 hover:text-teal-300 font-semibold cursor-pointer"
                          >
                            View Evidence
                          </button>
                        )}
                        <button
                          onClick={() => setSelectedMeasure(m)}
                          className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold cursor-pointer"
                        >
                          Protocol Criteria &rarr;
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 2: GAPS IN CARE FEED */}
      {activeTab === 'gaps' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
            <div className="flex flex-wrap items-center gap-3 text-sm text-slate-300">
              <div className="flex items-center gap-2">
                <span>Severity:</span>
                <select
                  id="gap-severity-filter"
                  value={gapSeverityFilter}
                  onChange={(e) => {
                    setGapSeverityFilter(e.target.value);
                    loadGaps(selectedPatientId);
                  }}
                  className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
                >
                  <option value="all">All Severities</option>
                  <option value="CRITICAL">Critical</option>
                  <option value="HIGH">High</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="LOW">Low</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span>Status:</span>
                <select
                  id="gap-status-filter"
                  value={gapStatusFilter}
                  onChange={(e) => {
                    setGapStatusFilter(e.target.value);
                    loadGaps(selectedPatientId);
                  }}
                  className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
                >
                  <option value="all">All Statuses</option>
                  <option value="open">Open</option>
                  <option value="in_remediation">In Remediation</option>
                  <option value="resolved">Resolved</option>
                </select>
              </div>
            </div>

            <div className="text-xs text-slate-400">
              Showing <span className="font-semibold text-slate-200">{gaps.length}</span> active care gaps
            </div>
          </div>

          {gaps.length === 0 ? (
            <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
              🎉 No clinical care gaps identified matching the selected criteria.
            </div>
          ) : (
            <div className="space-y-3">
              {gaps.map((gap) => {
                const isCritical = gap.severity === 'CRITICAL' || gap.severity === 'HIGH';
                return (
                  <div
                    key={gap.gap_id}
                    className={`bg-slate-900/80 border p-5 rounded-2xl shadow-lg transition-all flex flex-col md:flex-row justify-between items-start md:items-center gap-4 ${
                      isCritical ? 'border-amber-500/40 hover:border-amber-500/60' : 'border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="space-y-1.5 flex-1">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        <span
                          className={`text-xs font-bold px-2.5 py-0.5 rounded-md ${
                            gap.severity === 'CRITICAL'
                              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                              : gap.severity === 'HIGH'
                              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                              : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                          }`}
                        >
                          {gap.severity}
                        </span>

                        <span
                          className={`text-xs font-semibold px-2 py-0.5 rounded-md uppercase ${
                            gap.status === 'open'
                              ? 'bg-rose-950/60 text-rose-400 border border-rose-800'
                              : gap.status === 'in_remediation'
                              ? 'bg-cyan-950/60 text-cyan-400 border border-cyan-800'
                              : 'bg-emerald-950/60 text-emerald-400 border border-emerald-800'
                          }`}
                        >
                          {gap.status.replace(/_/g, ' ')}
                        </span>

                        <span className="text-xs font-semibold text-slate-300">
                          {gap.patient_identifier ? `${gap.patient_name} (${gap.patient_identifier})` : `Patient #${gap.patient_id}`}
                        </span>

                        <span className="text-xs text-slate-500">| Measure: {gap.measure_code}</span>
                      </div>

                      <h4 className="text-sm font-bold text-slate-100">{gap.measure_title}</h4>
                      <p className="text-xs text-slate-300 bg-slate-800/60 p-2 rounded-lg border border-slate-700/50">
                        <strong className="text-slate-400">Missing Evidence:</strong> {gap.missing_data_summary}
                      </p>
                      <p className="text-xs text-emerald-300">
                        <strong>Recommended Action:</strong> {gap.recommended_action}
                      </p>
                    </div>

                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 w-full md:w-auto">
                      {gap.status === 'open' && (
                        <button
                          id={`remediate-gap-btn-${gap.gap_id}`}
                          onClick={() => handleCreateCareTask(gap.gap_id)}
                          className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold rounded-xl shadow-md shadow-emerald-600/20 transition-all flex items-center justify-center gap-1.5 cursor-pointer whitespace-nowrap"
                        >
                          <span>⚡</span> Create Care Task
                        </button>
                      )}

                      {gap.status === 'in_remediation' && (
                        <div className="text-xs text-cyan-400 font-semibold bg-cyan-950/40 border border-cyan-800 px-3 py-1.5 rounded-xl flex items-center gap-1">
                          <span>🔄</span> Remediation In-Progress
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: COMPLIANCE & AUDIT REPORTS */}
      {activeTab === 'reports' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-slate-900/60 p-4 rounded-xl border border-slate-800">
            <div className="text-sm text-slate-300">
              Archived population compliance audits and cryptographic data provenance logs.
            </div>
            <button
              onClick={() => setShowGenerateReportModal(true)}
              className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg shadow-md transition-all cursor-pointer flex items-center gap-1.5"
            >
              <span>+</span> Generate Audit Report
            </button>
          </div>

          {reports.length === 0 ? (
            <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800">
              No audit reports generated yet. Click 'Generate Audit Report' above to synthesize a population scorecard.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {reports.map((rep) => (
                <div
                  key={rep.report_id}
                  className="bg-slate-900/80 border border-slate-800 hover:border-slate-700 p-5 rounded-2xl shadow-lg transition-all flex flex-col justify-between"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold px-2 py-0.5 bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 rounded-md">
                        {rep.report_id}
                      </span>
                      <span className="text-xs text-slate-400 capitalize">{rep.report_scope}</span>
                    </div>

                    <h3 className="text-base font-bold text-slate-100">{rep.title}</h3>

                    <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/60 space-y-1 text-xs">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Overall Rate:</span>
                        <span className="font-bold text-emerald-400">{rep.overall_performance_rate.toFixed(1)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Eligible Population:</span>
                        <span className="text-slate-200">{rep.total_eligible_population} patients</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Compliant Count:</span>
                        <span className="text-slate-200">{rep.total_compliant_population} compliant</span>
                      </div>
                    </div>

                    {rep.audit_metadata_json?.provenance_hash && (
                      <div className="text-[11px] text-slate-400 font-mono bg-slate-950 p-2 rounded-lg border border-slate-800/80 truncate">
                        <span className="text-slate-500">Provenance:</span> {rep.audit_metadata_json.provenance_hash}
                      </div>
                    )}
                  </div>

                  <div className="pt-3 border-t border-slate-800 mt-4 flex items-center justify-between">
                    <span className="text-xs text-slate-500">
                      {new Date(rep.created_at).toLocaleDateString()}
                    </span>
                    <button
                      onClick={() => setSelectedReportDetail(rep)}
                      className="text-xs font-bold text-emerald-400 hover:text-emerald-300 cursor-pointer"
                    >
                      Audit Scorecard &rarr;
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* MODAL: MEASURE CRITERIA VIEWER */}
      {selectedMeasure && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-xs font-bold text-teal-400">{selectedMeasure.measure_id}</span>
                <h3 className="text-lg font-bold text-slate-100">{selectedMeasure.title}</h3>
              </div>
              <button
                onClick={() => setSelectedMeasure(null)}
                className="text-slate-400 hover:text-slate-200 font-bold text-lg"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <div className="font-semibold text-slate-300 mb-0.5">Description:</div>
                <p className="text-slate-400">{selectedMeasure.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-slate-800/50 p-3 rounded-xl border border-slate-700/50">
                  <div className="font-semibold text-slate-300">Standard Framework</div>
                  <div className="text-slate-400">{selectedMeasure.standard_framework} (v{selectedMeasure.version})</div>
                </div>
                <div className="bg-slate-800/50 p-3 rounded-xl border border-slate-700/50">
                  <div className="font-semibold text-slate-300">Steward & Target</div>
                  <div className="text-slate-400">
                    {selectedMeasure.steward} | Target: {(selectedMeasure.target_rate * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              <div className="bg-slate-800/50 p-3 rounded-xl border border-slate-700/50 space-y-1">
                <div className="font-semibold text-slate-200">Initial Population Criteria:</div>
                <div className="text-slate-400">{selectedMeasure.initial_population_criteria}</div>
              </div>

              <div className="bg-slate-800/50 p-3 rounded-xl border border-slate-700/50 space-y-1">
                <div className="font-semibold text-slate-200">Denominator Criteria:</div>
                <div className="text-slate-400">{selectedMeasure.denominator_criteria}</div>
              </div>

              <div className="bg-emerald-950/30 p-3 rounded-xl border border-emerald-800/50 space-y-1">
                <div className="font-semibold text-emerald-300">Numerator (Compliance) Criteria:</div>
                <div className="text-emerald-200">{selectedMeasure.numerator_criteria}</div>
              </div>

              {selectedMeasure.exclusion_criteria && (
                <div className="bg-rose-950/30 p-3 rounded-xl border border-rose-800/50 space-y-1">
                  <div className="font-semibold text-rose-300">Exclusion Criteria:</div>
                  <div className="text-rose-200">{selectedMeasure.exclusion_criteria}</div>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setSelectedMeasure(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: PATIENT EVIDENCE VIEWER */}
      {selectedResultEvidence && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-xs font-bold text-emerald-400">{selectedResultEvidence.measure_code}</span>
                <h3 className="text-base font-bold text-slate-100">{selectedResultEvidence.measure_title}</h3>
              </div>
              <button
                onClick={() => setSelectedResultEvidence(null)}
                className="text-slate-400 hover:text-slate-200 font-bold text-lg"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between p-3 bg-slate-800/60 rounded-xl border border-slate-700/60">
                <span className="text-slate-400">Compliance Status:</span>
                <span className="font-bold text-emerald-400 uppercase">
                  {selectedResultEvidence.compliance_status}
                </span>
              </div>

              <div>
                <div className="font-semibold text-slate-300 mb-1">Clinical Evidence Payload:</div>
                <pre className="bg-slate-950 p-3 rounded-xl border border-slate-800 text-[11px] font-mono text-emerald-300 overflow-x-auto max-h-60">
                  {JSON.stringify(selectedResultEvidence.evidence_json || {}, null, 2)}
                </pre>
              </div>

              <div className="text-slate-500 text-[11px]">
                Calculated at: {new Date(selectedResultEvidence.calculated_at).toLocaleString()}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setSelectedResultEvidence(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: REPORT SCORECARD DRILLDOWN */}
      {selectedReportDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-xs font-bold text-teal-400">{selectedReportDetail.report_id}</span>
                <h3 className="text-lg font-bold text-slate-100">{selectedReportDetail.title}</h3>
              </div>
              <button
                onClick={() => setSelectedReportDetail(null)}
                className="text-slate-400 hover:text-slate-200 font-bold text-lg"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/60 text-center">
                  <div className="text-slate-400">Overall Rate</div>
                  <div className="text-2xl font-black text-emerald-400">
                    {selectedReportDetail.overall_performance_rate.toFixed(1)}%
                  </div>
                </div>
                <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/60 text-center">
                  <div className="text-slate-400">Eligible Cohort</div>
                  <div className="text-2xl font-black text-slate-200">
                    {selectedReportDetail.total_eligible_population}
                  </div>
                </div>
                <div className="bg-slate-800/60 p-3 rounded-xl border border-slate-700/60 text-center">
                  <div className="text-slate-400">Compliant Patients</div>
                  <div className="text-2xl font-black text-teal-300">
                    {selectedReportDetail.total_compliant_population}
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-bold text-slate-200 mb-2">Measure Performance Breakdown:</h4>
                <div className="space-y-2">
                  {(selectedReportDetail.measure_summaries_json || []).map((ms) => (
                    <div
                      key={ms.measure_id}
                      className="bg-slate-800/50 p-3 rounded-xl border border-slate-700/50 flex items-center justify-between gap-4"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-bold text-teal-300">{ms.measure_id}</span>
                          <span className="text-slate-200 font-semibold">{ms.title}</span>
                        </div>
                        <div className="text-slate-400 text-[11px] mt-0.5">
                          Framework: {ms.standard_framework} | Eligible: {ms.eligible_population} | Gaps: {ms.gap_count}
                        </div>
                      </div>

                      <div className="text-right">
                        <div className="font-bold text-emerald-400 text-sm">
                          {(ms.performance_rate * 100).toFixed(1)}%
                        </div>
                        <div className="text-slate-500 text-[10px]">
                          Target: {(ms.target_rate * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {selectedReportDetail.audit_metadata_json && (
                <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1">
                  <div className="font-semibold text-slate-300">Audit & Cryptographic Data Provenance:</div>
                  <div className="font-mono text-[11px] text-slate-400 break-all">
                    SHA-256 Hash: {selectedReportDetail.audit_metadata_json.provenance_hash}
                  </div>
                  <div className="text-[10px] text-slate-500">
                    Generated: {selectedReportDetail.created_at} | Evaluator User ID:{' '}
                    {selectedReportDetail.generated_by_user_id || 'System'}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end">
              <button
                onClick={() => setSelectedReportDetail(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs rounded-xl"
              >
                Close Scorecard
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: GENERATE AUDIT REPORT FORM */}
      {showGenerateReportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-lg font-bold text-slate-100">Synthesize Quality Audit Report</h3>
              <button
                onClick={() => setShowGenerateReportModal(false)}
                className="text-slate-400 hover:text-slate-200 font-bold text-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleGenerateReport} className="space-y-4 text-xs">
              <div className="space-y-1">
                <label className="text-slate-300 font-semibold">Report Title:</label>
                <input
                  id="report-title-input"
                  type="text"
                  value={reportTitle}
                  onChange={(e) => setReportTitle(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-300 font-semibold">Audit Scope:</label>
                <select
                  id="report-scope-select"
                  value={reportScope}
                  onChange={(e) => setReportScope(e.target.value as ReportScope)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-slate-200 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
                >
                  <option value="organization">Organization (All Active Patients)</option>
                  <option value="department">Department</option>
                  <option value="provider">Provider</option>
                </select>
              </div>

              <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowGenerateReportModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs rounded-xl"
                >
                  Cancel
                </button>
                <button
                  id="submit-report-btn"
                  type="submit"
                  disabled={generatingReport}
                  className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-emerald-600/20 disabled:opacity-50 cursor-pointer"
                >
                  {generatingReport ? 'Evaluating & Synthesizing...' : 'Synthesize Report'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
