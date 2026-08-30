import React, { useState, useEffect, useMemo } from 'react';
import {
  imagingApi,
  fhirApi,
  patientsApi,
} from '../../api/client';

import {
  ImagingStudy,
  ImagingAsset,
  ImagingFinding,
  RadiologyReport,
  ImagingTimelineItem,
  MultimodalContextSnapshot,
  Patient,
  User,
  ImagingModality,
  ImagingBodySite,
  FindingReviewStatus,
} from '../../types';

interface ImagingRadiologyWorkspaceProps {
  currentUser?: User | null;
  selectedPatientId?: string | null;
}

export const ImagingRadiologyWorkspace: React.FC<ImagingRadiologyWorkspaceProps> = ({
  currentUser,
  selectedPatientId: initialPatientId,
}) => {
  // Navigation tabs
  const [activeTab, setActiveTab] = useState<'studies' | 'analysis' | 'report' | 'timeline' | 'fhir'>('studies');

  // Patient & study state
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>(initialPatientId || '');
  const [studies, setStudies] = useState<ImagingStudy[]>([]);
  const [selectedStudy, setSelectedStudy] = useState<ImagingStudy | null>(null);
  const [studyAssets, setStudyAssets] = useState<ImagingAsset[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<ImagingAsset | null>(null);

  // Analysis & Findings state
  const [findings, setFindings] = useState<ImagingFinding[]>([]);
  const [selectedFinding, setSelectedFinding] = useState<ImagingFinding | null>(null);
  const [multimodalContext, setMultimodalContext] = useState<MultimodalContextSnapshot | null>(null);
  const [activeReport, setActiveReport] = useState<RadiologyReport | null>(null);
  const [timelineItems, setTimelineItems] = useState<ImagingTimelineItem[]>([]);

  // Modality & filter state
  const [modalityFilter, setModalityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // UI state
  const [loading, setLoading] = useState<boolean>(false);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [showBoundingBoxes, setShowBoundingBoxes] = useState<boolean>(true);

  // Modals & Form states
  const [showCreateStudyModal, setShowCreateStudyModal] = useState<boolean>(false);
  const [showReviewFindingModal, setShowReviewFindingModal] = useState<boolean>(false);
  const [showFinalizeModal, setShowFinalizeModal] = useState<boolean>(false);
  const [showAmendModal, setShowAmendModal] = useState<boolean>(false);
  const [fhirExportType, setFhirExportType] = useState<'study' | 'report' | 'observation'>('study');
  const [fhirExportData, setFhirExportData] = useState<any>(null);
  const [fhirExportLoading, setFhirExportLoading] = useState<boolean>(false);

  // Form input fields
  const [newStudyForm, setNewStudyForm] = useState({
    modality: 'XRAY' as ImagingModality,
    body_site: 'CHEST' as ImagingBodySite,
    study_description: '',
    accession_number: '',
    performing_department: 'Radiology & Diagnostic Imaging',
    referring_provider: '',
  });

  const [reviewFindingForm, setReviewFindingForm] = useState<{
    review_status: FindingReviewStatus;
    review_notes: string;
  }>({
    review_status: 'confirmed',
    review_notes: '',
  });

  const [reportEditForm, setReportEditForm] = useState<{
    clinical_indication: string;
    technique: string;
    comparison_studies: string;
    findings: string;
    impression: string;
    recommendations: string;
  }>({
    clinical_indication: '',
    technique: '',
    comparison_studies: '',
    findings: '',
    impression: '',
    recommendations: '',
  });

  const [signatureNotes, setSignatureNotes] = useState<string>('');
  const [amendmentReason, setAmendmentReason] = useState<string>('');

  // Fetch initial patients
  useEffect(() => {
    const fetchPatients = async () => {
      try {
        const res = await patientsApi.list();
        setPatients(res || []);
        if (res && res.length > 0 && !selectedPatientId) {
          setSelectedPatientId(res[0].patient_id);
        }

      } catch (err: any) {
        console.error('Failed to load patients', err);
      }
    };
    fetchPatients();
  }, []);

  // Fetch studies whenever patient or modality filter changes
  useEffect(() => {
    fetchStudies();
  }, [selectedPatientId, modalityFilter]);

  // Load study details when a study is selected
  useEffect(() => {
    if (selectedStudy) {
      fetchStudyDetails(selectedStudy.study_id);
    }
  }, [selectedStudy?.study_id]);

  const fetchStudies = async () => {
    setLoading(true);
    setActionError(null);
    try {
      const modality = modalityFilter === 'ALL' ? undefined : modalityFilter;
      const res = await imagingApi.listStudies(selectedPatientId || undefined, modality);
      setStudies(res.items || []);
      if (res.items && res.items.length > 0) {
        if (!selectedStudy || !res.items.some((s) => s.study_id === selectedStudy.study_id)) {
          setSelectedStudy(res.items[0]);
        }
      } else {
        setSelectedStudy(null);
        setFindings([]);
        setActiveReport(null);
      }
    } catch (err: any) {
      setActionError(err.message || 'Failed to retrieve imaging studies');
    } finally {
      setLoading(false);
    }
  };

  const fetchStudyDetails = async (studyId: string) => {
    try {
      const [assetsRes, findingsRes] = await Promise.all([
        imagingApi.listAssets(studyId),
        imagingApi.listFindings(studyId),
      ]);
      setStudyAssets(assetsRes.items || []);
      setSelectedAsset(assetsRes.items && assetsRes.items.length > 0 ? assetsRes.items[0] : null);
      setFindings(findingsRes.items || []);
    } catch (err: any) {
      console.error('Failed to fetch study details', err);
    }
  };

  const fetchTimeline = async () => {
    if (!selectedPatientId) return;
    setLoading(true);
    try {
      const res = await imagingApi.getTimeline(selectedPatientId);
      setTimelineItems(res.items || []);
    } catch (err: any) {
      setActionError(err.message || 'Failed to load imaging timeline');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateStudy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatientId) return;
    setLoading(true);
    setActionError(null);
    try {
      const created = await imagingApi.createStudy(selectedPatientId, newStudyForm);
      setActionSuccess(`Successfully ingested imaging study ${created.study_id}`);
      setShowCreateStudyModal(false);
      setNewStudyForm({
        modality: 'XRAY',
        body_site: 'CHEST',
        study_description: '',
        accession_number: '',
        performing_department: 'Radiology & Diagnostic Imaging',
        referring_provider: '',
      });
      await fetchStudies();
      setSelectedStudy(created);
    } catch (err: any) {
      setActionError(err.message || 'Failed to create imaging study');
    } finally {
      setLoading(false);
    }
  };

  const handleRunAiAnalysis = async () => {
    if (!selectedStudy) return;
    setAnalyzing(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await imagingApi.analyzeStudy(selectedStudy.study_id);
      setFindings(res.findings || []);
      setMultimodalContext(res.multimodal_context);
      if (res.draft_report) {
        setActiveReport(res.draft_report);
        setReportEditForm({
          clinical_indication: res.draft_report.clinical_indication,
          technique: res.draft_report.technique,
          comparison_studies: res.draft_report.comparison_studies,
          findings: res.draft_report.findings,
          impression: res.draft_report.impression,
          recommendations: res.draft_report.recommendations,
        });
      }
      setActionSuccess(
        `AI Multimodal Interpretation complete: Identified ${res.findings_count} finding(s) with ${res.critical_findings_count} critical alert(s).`
      );
      setActiveTab('analysis');
      await fetchStudies();
    } catch (err: any) {
      setActionError(err.message || 'AI Multimodal Interpretation failed');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleReviewFinding = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFinding) return;
    setLoading(true);
    try {
      const updated = await imagingApi.reviewFinding(
        selectedFinding.finding_id,
        reviewFindingForm.review_status,
        reviewFindingForm.review_notes
      );
      setFindings((prev) => prev.map((f) => (f.finding_id === updated.finding_id ? updated : f)));
      setShowReviewFindingModal(false);
      setActionSuccess(`Finding ${updated.finding_id} status updated to ${updated.clinician_review_status}`);
    } catch (err: any) {
      setActionError(err.message || 'Failed to submit finding review');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveReportDraft = async () => {
    if (!activeReport) return;
    setLoading(true);
    try {
      const updated = await imagingApi.updateReport(activeReport.report_id, reportEditForm);
      setActiveReport(updated);
      setActionSuccess('Draft report saved successfully.');
    } catch (err: any) {
      setActionError(err.message || 'Failed to save draft report');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitForReview = async () => {
    if (!activeReport) return;
    setLoading(true);
    try {
      const updated = await imagingApi.submitReportReview(activeReport.report_id);
      setActiveReport(updated);
      setActionSuccess('Report submitted to Radiologist Review Queue.');
    } catch (err: any) {
      setActionError(err.message || 'Failed to submit report for review');
    } finally {
      setLoading(false);
    }
  };

  const handleFinalizeReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeReport) return;
    setLoading(true);
    try {
      const updated = await imagingApi.finalizeReport(activeReport.report_id, signatureNotes);
      setActiveReport(updated);
      setShowFinalizeModal(false);
      setSignatureNotes('');
      setActionSuccess(`Report ${updated.report_id} formally signed and finalized.`);
      await fetchStudies();
    } catch (err: any) {
      setActionError(err.message || 'Failed to finalize report');
    } finally {
      setLoading(false);
    }
  };

  const handleAmendReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeReport || !amendmentReason) return;
    setLoading(true);
    try {
      const amended = await imagingApi.amendReport(
        activeReport.report_id,
        amendmentReason,
        reportEditForm.impression,
        reportEditForm.findings,
        reportEditForm.recommendations
      );
      setActiveReport(amended);
      setShowAmendModal(false);
      setAmendmentReason('');
      setActionSuccess(`Amended report version ${amended.report_id} generated and signed.`);
      await fetchStudies();
    } catch (err: any) {
      setActionError(err.message || 'Failed to amend report');
    } finally {
      setLoading(false);
    }
  };

  const handleFetchFhir = async (type: 'study' | 'report' | 'observation') => {
    setFhirExportType(type);
    setFhirExportLoading(true);
    setFhirExportData(null);
    try {
      let data: any = null;
      if (type === 'study' && selectedStudy) {
        data = await fhirApi.exportImagingStudy(selectedStudy.study_id);
      } else if (type === 'report' && activeReport) {
        data = await fhirApi.exportRadiologyReport(activeReport.report_id);
      } else if (type === 'observation' && selectedFinding) {
        data = await fhirApi.exportImagingObservation(selectedFinding.finding_id);
      }
      setFhirExportData(data);
    } catch (err: any) {
      setFhirExportData({ error: err.message || 'FHIR resource export failed' });
    } finally {
      setFhirExportLoading(false);
    }
  };

  // Filtered studies
  const filteredStudies = useMemo(() => {
    return studies.filter((s) => {
      const matchesSearch =
        s.study_description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.accession_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.study_id.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesSearch;
    });
  }, [studies, searchQuery]);

  const hasCriticalFinding = useMemo(() => {
    return findings.some((f) => f.is_critical);
  }, [findings]);

  return (
    <div className="space-y-6" data-testid="imaging-workspace">
      {/* Top Banner / Clinical Decision Support Safety Disclaimer */}
      <div className="bg-gradient-to-r from-blue-950 via-slate-900 to-indigo-950 border border-blue-800/60 rounded-xl p-4 shadow-lg text-white">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start space-x-3">
            <div className="p-2.5 bg-blue-600/30 rounded-lg border border-blue-500/40 text-blue-400 mt-0.5 text-xl">
              🛡️
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold tracking-tight text-white">
                  Medical Imaging AI & Multimodal Radiology
                </h1>
                <span className="px-2.5 py-0.5 bg-indigo-500/20 text-indigo-300 text-xs font-semibold rounded-full border border-indigo-500/30">
                  Phase 9.0.18
                </span>
                <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 text-xs font-medium rounded-full border border-amber-500/30">
                  Assistive AI Support
                </span>
              </div>
              <p className="text-xs text-slate-300 mt-1 max-w-4xl leading-relaxed">
                Assistive clinical diagnostic imaging decision support with multimodal patient context. All AI-generated observations and draft reports remain preliminary until reviewed and electronically signed by an authorized physician or radiologist.
              </p>
            </div>
          </div>
          <button
            onClick={() => setShowCreateStudyModal(true)}
            className="flex items-center space-x-2 px-3.5 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg shadow-sm transition-all whitespace-nowrap"
            data-testid="ingest-study-btn"
          >
            <span>+ Ingest Imaging Study</span>
          </button>
        </div>
      </div>

      {/* Critical Alert Emergency Banner if critical findings are present */}
      {hasCriticalFinding && (
        <div
          className="bg-red-950/80 border-2 border-red-500 rounded-xl p-4 shadow-md text-red-100 flex items-start space-x-3 animate-pulse"
          data-testid="critical-finding-banner"
        >
          <span className="text-2xl text-red-400 shrink-0 mt-0.5">⚠️</span>
          <div>
            <div className="font-bold text-red-200 text-sm tracking-wide flex items-center space-x-2">
              <span>POTENTIALLY CRITICAL AI-ASSISTED FINDING — REQUIRES IMMEDIATE CLINICIAN REVIEW</span>
            </div>
            <p className="text-xs text-red-300 mt-0.5">
              One or more acute, urgent imaging findings have been identified for study {selectedStudy?.accession_number}. Please correlate immediately with clinical telemetry and initiate prompt emergency evaluation if indicated.
            </p>
          </div>
        </div>
      )}

      {/* Notifications */}
      {actionSuccess && (
        <div className="bg-emerald-950/60 border border-emerald-800 text-emerald-300 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span>✅</span>
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-400 hover:text-emerald-200">
            ✕
          </button>
        </div>
      )}

      {actionError && (
        <div className="bg-red-950/60 border border-red-800 text-red-300 px-4 py-3 rounded-lg text-sm flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span>⚠️</span>
            <span>{actionError}</span>
          </div>
          <button onClick={() => setActionError(null)} className="text-red-400 hover:text-red-200">
            ✕
          </button>
        </div>
      )}

      {/* Patient & Modality Toolbar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm flex flex-wrap items-center justify-between gap-4 text-white">
        <div className="flex items-center space-x-3">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Patient:</label>
          <select
            value={selectedPatientId}
            onChange={(e) => setSelectedPatientId(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
            data-testid="patient-selector"
          >
            {patients.map((p) => (
              <option key={p.patient_id} value={p.patient_id}>
                {p.first_name} {p.last_name} ({p.patient_id})
              </option>
            ))}
          </select>
        </div>

        {/* Modality Filter Chips */}
        <div className="flex items-center space-x-1 overflow-x-auto py-1">
          {['ALL', 'XRAY', 'CT', 'MRI', 'ULTRASOUND', 'PET_CT', 'MAMMOGRAPHY'].map((mod) => (
            <button
              key={mod}
              onClick={() => setModalityFilter(mod)}
              className={`px-3 py-1 text-xs font-medium rounded-lg transition-all ${
                modalityFilter === mod
                  ? 'bg-blue-600 text-white font-semibold shadow-sm'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-200'
              }`}
            >
              {mod}
            </button>
          ))}
        </div>

        {/* Search input */}
        <div className="relative">
          <input
            type="text"
            placeholder="🔍 Search studies..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 w-48"
          />
        </div>
      </div>

      {/* Main View Tabs */}
      <div className="border-b border-slate-800 flex space-x-6 text-sm font-medium">
        <button
          onClick={() => setActiveTab('studies')}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition-all ${
            activeTab === 'studies'
              ? 'border-blue-500 text-blue-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
          data-testid="tab-studies"
        >
          <span>🗂️ PACS Study Browser ({studies.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('analysis')}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition-all ${
            activeTab === 'analysis'
              ? 'border-blue-500 text-blue-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
          data-testid="tab-analysis"
        >
          <span>✨ Multimodal AI Interpretation ({findings.length})</span>
        </button>
        <button
          onClick={() => setActiveTab('report')}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition-all ${
            activeTab === 'report'
              ? 'border-blue-500 text-blue-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
          data-testid="tab-report"
        >
          <span>📄 Structured Radiology Report</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('timeline');
            fetchTimeline();
          }}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition-all ${
            activeTab === 'timeline'
              ? 'border-blue-500 text-blue-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
          data-testid="tab-timeline"
        >
          <span>⏱️ Longitudinal Timeline</span>
        </button>
        <button
          onClick={() => {
            setActiveTab('fhir');
            handleFetchFhir('study');
          }}
          className={`pb-3 flex items-center space-x-2 border-b-2 transition-all ${
            activeTab === 'fhir'
              ? 'border-blue-500 text-blue-400 font-semibold'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
          data-testid="tab-fhir"
        >
          <span>🌐 FHIR R4 Resources</span>
        </button>
      </div>

      {/* TAB CONTENT 1: PACS STUDIES BROWSER */}
      {activeTab === 'studies' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Studies List */}
          <div className="lg:col-span-1 space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 px-1">
              Ingested Imaging Studies
            </h2>
            {loading ? (
              <div className="p-8 text-center text-slate-400 text-sm animate-pulse">Loading imaging studies...</div>
            ) : filteredStudies.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-sm">
                No imaging studies found. Click "Ingest Imaging Study" to register a new study.
              </div>
            ) : (
              filteredStudies.map((study) => {
                const isSelected = selectedStudy?.study_id === study.study_id;
                return (
                  <div
                    key={study.study_id}
                    onClick={() => setSelectedStudy(study)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-slate-800/90 border-blue-500 shadow-md ring-1 ring-blue-500'
                        : 'bg-slate-900 border-slate-800 hover:bg-slate-800/60 hover:border-slate-700'
                    }`}
                    data-testid={`study-card-${study.study_id}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 bg-blue-900/60 text-blue-300 text-xs font-semibold rounded border border-blue-700/50">
                        {study.modality}
                      </span>
                      <span
                        className={`px-2 py-0.5 text-xs font-medium rounded ${
                          study.status === 'FINAL'
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                            : 'bg-amber-950 text-amber-300 border border-amber-800'
                        }`}
                      >
                        {study.status}
                      </span>
                    </div>

                    <h3 className="text-sm font-semibold text-white mt-2 line-clamp-1">{study.study_description}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">Acc: {study.accession_number} • Site: {study.body_site}</p>

                    <div className="flex items-center justify-between text-xs text-slate-500 mt-3 pt-2 border-t border-slate-800/80">
                      <span>{new Date(study.study_datetime).toLocaleDateString()}</span>
                      {study.has_critical_findings && (
                        <span className="text-red-400 font-semibold flex items-center space-x-1">
                          <span>⚠️ Critical</span>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Selected Study Overview & Assets */}
          <div className="lg:col-span-2 space-y-6">
            {selectedStudy ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm space-y-6">
                <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                  <div>
                    <div className="flex items-center space-x-3">
                      <span className="text-lg font-bold text-white">{selectedStudy.study_description}</span>
                      <span className="px-2.5 py-0.5 bg-blue-900/60 text-blue-300 text-xs font-semibold rounded border border-blue-700/50">
                        {selectedStudy.modality}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      Study ID: <span className="font-mono text-slate-300">{selectedStudy.study_id}</span> • Accession: <span className="font-mono text-slate-300">{selectedStudy.accession_number}</span>
                    </p>
                  </div>
                  <button
                    onClick={handleRunAiAnalysis}
                    disabled={analyzing}
                    className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-sm font-semibold rounded-lg shadow-md transition-all disabled:opacity-50"
                    data-testid="run-analysis-btn"
                  >
                    <span>{analyzing ? '⚙️ Interpreting Study...' : '✨ Run Multimodal AI Interpretation'}</span>
                  </button>
                </div>

                {/* Study Metadata Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-slate-950/60 p-4 rounded-lg border border-slate-800 text-xs">
                  <div>
                    <span className="text-slate-400 block">Body Region:</span>
                    <span className="font-semibold text-slate-200 mt-0.5 block">{selectedStudy.body_site}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Department:</span>
                    <span className="font-semibold text-slate-200 mt-0.5 block">{selectedStudy.performing_department}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Referring Doctor:</span>
                    <span className="font-semibold text-slate-200 mt-0.5 block">{selectedStudy.referring_provider || 'Not recorded'}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Provenance Hash:</span>
                    <span className="font-mono text-slate-400 mt-0.5 block truncate" title={selectedStudy.provenance_hash}>
                      {selectedStudy.provenance_hash.slice(0, 16)}...
                    </span>
                  </div>
                </div>

                {/* DICOM Series / Assets Preview */}
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
                    DICOM Series & Image Assets ({studyAssets.length})
                  </h3>
                  {studyAssets.length === 0 ? (
                    <div className="bg-slate-950/40 border border-slate-800/80 rounded-lg p-6 text-center text-xs text-slate-400">
                      No standalone asset attached yet. Ingested as PACS direct study reference.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {studyAssets.map((asset) => (
                        <div
                          key={asset.asset_id}
                          onClick={() => setSelectedAsset(asset)}
                          className={`p-3 rounded-lg border cursor-pointer text-xs transition-all ${
                            selectedAsset?.asset_id === asset.asset_id
                              ? 'bg-blue-950/40 border-blue-500'
                              : 'bg-slate-950/40 border-slate-800 hover:border-slate-700'
                          }`}
                        >
                          <div className="font-semibold text-slate-200">{asset.series_description || 'Series 1'}</div>
                          <div className="text-slate-400 mt-1">SOP UID: {asset.sop_instance_uid?.slice(0, 16)}...</div>
                          <div className="text-slate-500 mt-1">Format: {asset.mime_type}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Quick Action Navigation Buttons */}
                <div className="flex items-center justify-end space-x-3 pt-2">
                  <button
                    onClick={() => setActiveTab('analysis')}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition-all"
                  >
                    View AI Findings →
                  </button>
                  <button
                    onClick={() => setActiveTab('report')}
                    className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-all"
                  >
                    Generate Structured Report →
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-400 text-sm">
                Select an imaging study on the left to view diagnostic details.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT 2: MULTIMODAL AI INTERPRETATION & IMAGE VIEWER */}
      {activeTab === 'analysis' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Canvas: Simulated Diagnostic Viewer with Annotations */}
          <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-bold text-white">Diagnostic Image Canvas</span>
                <span className="px-2 py-0.5 bg-slate-800 text-slate-300 text-xs font-medium rounded">
                  {selectedStudy?.modality} • {selectedStudy?.body_site}
                </span>
              </div>
              <div className="flex items-center space-x-2 text-xs">
                <button
                  onClick={() => setShowBoundingBoxes(!showBoundingBoxes)}
                  className={`px-2.5 py-1 rounded border transition-all ${
                    showBoundingBoxes
                      ? 'bg-blue-600/30 border-blue-500 text-blue-300 font-semibold'
                      : 'bg-slate-800 border-slate-700 text-slate-400'
                  }`}
                >
                  AI Anomaly Overlays: {showBoundingBoxes ? 'ON' : 'OFF'}
                </button>
                <button
                  onClick={() => setZoomLevel((prev) => (prev === 1 ? 1.25 : prev === 1.25 ? 1.5 : 1))}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700"
                >
                  Zoom {zoomLevel}x
                </button>
              </div>
            </div>

            {/* Canvas Display */}
            <div
              className="relative w-full aspect-video bg-black rounded-lg border border-slate-800 overflow-hidden flex items-center justify-center select-none"
              data-testid="imaging-canvas"
            >
              {/* Simulated Radiograph Grid Background */}
              <div
                className="w-full h-full flex flex-col items-center justify-center text-center p-6 transition-transform duration-200"
                style={{ transform: `scale(${zoomLevel})` }}
              >
                <div className="relative w-64 h-64 border border-slate-800 rounded-full flex items-center justify-center bg-gradient-to-br from-slate-900 via-zinc-900 to-black opacity-80 shadow-2xl">
                  <div className="text-slate-600 text-xs font-mono">
                    <p className="font-bold text-slate-400">{selectedStudy?.modality || 'XRAY'} SIMULATION</p>
                    <p>{selectedStudy?.body_site}</p>
                    <p className="mt-2 text-[10px] text-slate-600">DICOM SOP VIEW</p>
                  </div>

                  {/* Render Bounding Box Overlays for Findings */}
                  {showBoundingBoxes &&
                    findings.map((f, i) => {
                      if (!f.bounding_box_json) return null;
                      const { x, y, width, height } = f.bounding_box_json;
                      const isHovered = selectedFinding?.finding_id === f.finding_id;
                      return (
                        <div
                          key={f.finding_id}
                          onClick={() => setSelectedFinding(f)}
                          className={`absolute cursor-pointer border-2 transition-all ${
                            f.is_critical
                              ? 'border-red-500 bg-red-500/20 animate-pulse'
                              : 'border-amber-400 bg-amber-400/20'
                          } ${isHovered ? 'ring-2 ring-white ring-offset-1' : ''}`}
                          style={{
                            left: `${(x / 400) * 100}%`,
                            top: `${(y / 400) * 100}%`,
                            width: `${(width / 400) * 100}%`,
                            height: `${(height / 400) * 100}%`,
                          }}
                          title={`${f.finding_type}: ${f.description}`}
                        >
                          <span
                            className={`absolute -top-5 left-0 px-1 py-0.5 text-[9px] font-bold rounded ${
                              f.is_critical ? 'bg-red-600 text-white' : 'bg-amber-600 text-white'
                            }`}
                          >
                            #{i + 1} {f.finding_type.replace('POSSIBLE_', '')}
                          </span>
                        </div>
                      );
                    })}
                </div>
              </div>

              {/* Bottom Canvas Telemetry Overlay */}
              <div className="absolute bottom-2 left-3 right-3 flex items-center justify-between text-[10px] font-mono text-slate-500 bg-black/60 px-2 py-1 rounded backdrop-blur-sm">
                <span>Accession: {selectedStudy?.accession_number}</span>
                <span>WL: 40 / WW: 400 (Simulated CT/X-Ray Window)</span>
                <span>SHA-256: {selectedStudy?.provenance_hash.slice(0, 10)}...</span>
              </div>
            </div>

            {/* Multimodal Diagnostic Context Bar */}
            <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 text-xs space-y-2">
              <span className="font-semibold text-slate-300 block">Multimodal Patient Context Evaluated:</span>
              <div className="flex flex-wrap gap-2 text-slate-400">
                <span className="px-2 py-0.5 bg-slate-900 rounded border border-slate-800">
                  Indication: <strong className="text-slate-200">{selectedStudy?.study_description}</strong>
                </span>
                {multimodalContext?.recent_vitals && multimodalContext.recent_vitals.length > 0 && (
                  <span className="px-2 py-0.5 bg-slate-900 rounded border border-slate-800">
                    Latest Vitals: HR {multimodalContext.recent_vitals[0].heart_rate || '--'} bpm • SpO2{' '}
                    {multimodalContext.recent_vitals[0].spo2 || '--'}%
                  </span>
                )}
                {multimodalContext?.active_diagnoses && multimodalContext.active_diagnoses.length > 0 && (
                  <span className="px-2 py-0.5 bg-slate-900 rounded border border-slate-800">
                    Diagnoses: {multimodalContext.active_diagnoses.slice(0, 2).join(', ')}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Right Panel: Structured Findings List & Review */}
          <div className="lg:col-span-5 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Structured Findings ({findings.length})
              </h2>
              <button
                onClick={handleRunAiAnalysis}
                disabled={analyzing}
                className="flex items-center space-x-1.5 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition-all"
              >
                <span>🔄 Re-Analyze</span>
              </button>
            </div>

            {findings.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-xs space-y-3">
                <p>No findings recorded yet.</p>
                <button
                  onClick={handleRunAiAnalysis}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-semibold"
                >
                  Run AI Interpretation
                </button>
              </div>
            ) : (
              <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
                {findings.map((finding, idx) => {
                  const isSelected = selectedFinding?.finding_id === finding.finding_id;
                  return (
                    <div
                      key={finding.finding_id}
                      onClick={() => setSelectedFinding(finding)}
                      className={`p-4 rounded-xl border transition-all ${
                        finding.is_critical
                          ? 'bg-red-950/40 border-red-500/80 shadow-md ring-1 ring-red-500'
                          : isSelected
                          ? 'bg-slate-800 border-blue-500 ring-1 ring-blue-500'
                          : 'bg-slate-900 border-slate-800 hover:bg-slate-800/60'
                      }`}
                      data-testid={`finding-card-${finding.finding_id}`}
                    >
                      <div className="flex items-center justify-between">
                        <span
                          className={`px-2 py-0.5 text-xs font-bold rounded ${
                            finding.is_critical
                              ? 'bg-red-900 text-red-200 border border-red-700'
                              : 'bg-blue-900/60 text-blue-300 border border-blue-700/50'
                          }`}
                        >
                          #{idx + 1} {finding.finding_type}
                        </span>
                        <span
                          className={`px-2 py-0.5 text-xs font-medium rounded ${
                            finding.clinician_review_status === 'confirmed'
                              ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                              : finding.clinician_review_status === 'rejected'
                              ? 'bg-rose-950 text-rose-300 border border-rose-800'
                              : 'bg-amber-950 text-amber-300 border border-amber-800'
                          }`}
                        >
                          {finding.clinician_review_status}
                        </span>
                      </div>

                      <p className="text-xs text-slate-200 mt-2 font-medium leading-relaxed">{finding.description}</p>
                      <p className="text-xs text-slate-400 mt-1 italic">Recommendation: {finding.recommendation}</p>

                      <div className="flex items-center justify-between text-[11px] text-slate-400 mt-3 pt-2 border-t border-slate-800">
                        <span>Confidence: {Math.round(finding.confidence_score * 100)}%</span>
                        <span className="font-mono text-slate-500">{finding.anatomical_location}</span>
                      </div>

                      {/* Review Action Trigger */}
                      <div className="flex items-center justify-end space-x-2 mt-3 pt-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedFinding(finding);
                            setReviewFindingForm({
                              review_status: 'confirmed',
                              review_notes: finding.review_notes || '',
                            });
                            setShowReviewFindingModal(true);
                          }}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded border border-slate-700 transition-all"
                          data-testid={`review-finding-btn-${finding.finding_id}`}
                        >
                          Clinician Review
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT 3: STRUCTURED RADIOLOGY REPORT WORKFLOW */}
      {activeTab === 'report' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm space-y-6">
          <div className="flex items-start justify-between border-b border-slate-800 pb-4">
            <div>
              <div className="flex items-center space-x-3">
                <span className="text-lg font-bold text-white">Diagnostic Radiology Report</span>
                <span
                  className={`px-2.5 py-0.5 text-xs font-semibold rounded ${
                    activeReport?.status === 'FINALIZED'
                      ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                      : activeReport?.status === 'AMENDED'
                      ? 'bg-purple-950 text-purple-300 border border-purple-800'
                      : 'bg-amber-950 text-amber-300 border border-amber-800'
                  }`}
                  data-testid="report-status-badge"
                >
                  {activeReport?.status || 'DRAFT'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Report ID: <span className="font-mono text-slate-300">{activeReport?.report_id || 'PENDING'}</span> • Study: {selectedStudy?.accession_number}
              </p>
            </div>

            {/* Governance Action Buttons */}
            <div className="flex items-center space-x-2">
              <button
                onClick={handleSaveReportDraft}
                disabled={loading || activeReport?.status === 'FINALIZED'}
                className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition-all disabled:opacity-40"
              >
                Save Draft
              </button>
              {activeReport?.status !== 'FINALIZED' && activeReport?.status !== 'AMENDED' ? (
                <>
                  <button
                    onClick={handleSubmitForReview}
                    disabled={loading}
                    className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition-all"
                  >
                    Submit for Review
                  </button>
                  <button
                    onClick={() => setShowFinalizeModal(true)}
                    disabled={loading}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg shadow-sm transition-all"
                    data-testid="finalize-report-btn"
                  >
                    Sign & Finalize Report
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setShowAmendModal(true)}
                  disabled={loading}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-lg shadow-sm transition-all"
                  data-testid="amend-report-btn"
                >
                  Create Amendment Addendum
                </button>
              )}
            </div>
          </div>

          {/* Structured Report Form Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Clinical Indication</label>
                <input
                  type="text"
                  value={reportEditForm.clinical_indication}
                  onChange={(e) => setReportEditForm({ ...reportEditForm, clinical_indication: e.target.value })}
                  disabled={activeReport?.status === 'FINALIZED'}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Technique</label>
                <input
                  type="text"
                  value={reportEditForm.technique}
                  onChange={(e) => setReportEditForm({ ...reportEditForm, technique: e.target.value })}
                  disabled={activeReport?.status === 'FINALIZED'}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Comparison Studies</label>
                <input
                  type="text"
                  value={reportEditForm.comparison_studies}
                  onChange={(e) => setReportEditForm({ ...reportEditForm, comparison_studies: e.target.value })}
                  disabled={activeReport?.status === 'FINALIZED'}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                />
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Diagnostic Findings</label>
                <textarea
                  rows={4}
                  value={reportEditForm.findings}
                  onChange={(e) => setReportEditForm({ ...reportEditForm, findings: e.target.value })}
                  disabled={activeReport?.status === 'FINALIZED'}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 font-mono"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Impression</label>
                <textarea
                  rows={3}
                  value={reportEditForm.impression}
                  onChange={(e) => setReportEditForm({ ...reportEditForm, impression: e.target.value })}
                  disabled={activeReport?.status === 'FINALIZED'}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60 font-mono"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Recommendations</label>
                <textarea
                  rows={2}
                  value={reportEditForm.recommendations}
                  onChange={(e) => setReportEditForm({ ...reportEditForm, recommendations: e.target.value })}
                  disabled={activeReport?.status === 'FINALIZED'}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-60"
                />
              </div>
            </div>
          </div>

          {/* Electronic Signature Audit Box if Finalized */}
          {activeReport?.status === 'FINALIZED' && (
            <div className="bg-emerald-950/40 border border-emerald-800 rounded-lg p-4 text-xs space-y-1">
              <div className="text-emerald-400 font-bold">
                ✓ Digitally Signed & Attested by Radiologist / Physician
              </div>
              <p className="text-slate-300">Signed At: {activeReport.signed_at ? new Date(activeReport.signed_at).toLocaleString() : 'N/A'}</p>
              <p className="text-slate-400 font-mono">Provenance Hash: {activeReport.provenance_hash}</p>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT 4: LONGITUDINAL IMAGING TIMELINE */}
      {activeTab === 'timeline' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h2 className="text-sm font-bold text-white">Longitudinal Patient Imaging Trajectory</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Chronological diagnostic radiology timeline for patient {selectedPatientId}
              </p>
            </div>
            <button
              onClick={fetchTimeline}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition-all"
            >
              🔄 Refresh Timeline
            </button>
          </div>

          {timelineItems.length === 0 ? (
            <div className="text-center py-12 text-slate-400 text-xs">No prior imaging timeline events recorded.</div>
          ) : (
            <div className="relative border-l border-slate-800 ml-4 space-y-6">
              {timelineItems.map((item) => (
                <div key={item.event_id} className="relative pl-6">
                  <div
                    className={`absolute -left-2.5 top-1.5 h-5 w-5 rounded-full border-2 flex items-center justify-center ${
                      item.has_critical
                        ? 'bg-red-950 border-red-500 text-red-400'
                        : 'bg-blue-950 border-blue-500 text-blue-400'
                    }`}
                  >
                    <div className="h-1.5 w-1.5 rounded-full bg-current" />
                  </div>

                  <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/80 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white">{item.description}</span>
                      <span className="px-2 py-0.5 bg-slate-800 text-slate-300 text-[10px] font-semibold rounded">
                        {item.modality}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Date: {new Date(item.study_datetime).toLocaleDateString()} • Acc: {item.accession_number} • Region: {item.body_site}
                    </p>
                    <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                      <span>Findings: {item.findings_count} observation(s)</span>
                      <span>Report Status: {item.report_status || 'PENDING'}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT 5: FHIR R4 RESOURCE VIEWER */}
      {activeTab === 'fhir' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center space-x-3">
              <span className="text-sm font-bold text-white">FHIR R4 Diagnostic Interoperability</span>
              <div className="flex items-center space-x-1">
                {(['study', 'report', 'observation'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => handleFetchFhir(t)}
                    className={`px-3 py-1 text-xs font-medium rounded-lg transition-all ${
                      fhirExportType === t
                        ? 'bg-blue-600 text-white font-semibold'
                        : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                    }`}
                  >
                    FHIR {t === 'study' ? 'ImagingStudy' : t === 'report' ? 'DiagnosticReport' : 'Observation'}
                  </button>
                ))}
              </div>
            </div>
            <button
              onClick={() => {
                if (fhirExportData) {
                  navigator.clipboard.writeText(JSON.stringify(fhirExportData, null, 2));
                  setActionSuccess('FHIR JSON copied to clipboard.');
                }
              }}
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition-all"
            >
              📋 Copy JSON
            </button>
          </div>

          {fhirExportLoading ? (
            <div className="p-8 text-center text-slate-400 text-xs animate-pulse">Assembling standard FHIR R4 resource...</div>
          ) : (
            <pre className="p-4 bg-slate-950 rounded-lg border border-slate-800 text-xs font-mono text-emerald-400 overflow-x-auto max-h-[500px]">
              {JSON.stringify(fhirExportData, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* MODAL 1: INGEST IMAGING STUDY */}
      {showCreateStudyModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4 text-white">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-base font-bold">Ingest Medical Imaging Study</span>
              <button onClick={() => setShowCreateStudyModal(false)} className="text-slate-400 hover:text-slate-200">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateStudy} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Modality</label>
                  <select
                    value={newStudyForm.modality}
                    onChange={(e) => setNewStudyForm({ ...newStudyForm, modality: e.target.value as ImagingModality })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200"
                  >
                    {['XRAY', 'CT', 'MRI', 'ULTRASOUND', 'PET_CT', 'MAMMOGRAPHY', 'ECHOCARDIOGRAPHY', 'OTHER'].map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Anatomical Body Site</label>
                  <select
                    value={newStudyForm.body_site}
                    onChange={(e) => setNewStudyForm({ ...newStudyForm, body_site: e.target.value as ImagingBodySite })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200"
                  >
                    {['CHEST', 'ABDOMEN', 'PELVIS', 'HEAD_BRAIN', 'SPINE', 'EXTREMITY', 'CARDIAC', 'BREAST', 'NECK', 'OTHER'].map((b) => (
                      <option key={b} value={b}>
                        {b}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Study Description / Clinical Indication</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. CXR 2 Views for acute chest pain and SOB"
                  value={newStudyForm.study_description}
                  onChange={(e) => setNewStudyForm({ ...newStudyForm, study_description: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-slate-400 block mb-1">Accession Number (Optional)</label>
                  <input
                    type="text"
                    placeholder="Auto-generated if empty"
                    value={newStudyForm.accession_number}
                    onChange={(e) => setNewStudyForm({ ...newStudyForm, accession_number: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Referring Physician</label>
                  <input
                    type="text"
                    placeholder="e.g. Dr. Jane Smith"
                    value={newStudyForm.referring_provider}
                    onChange={(e) => setNewStudyForm({ ...newStudyForm, referring_provider: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateStudyModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg"
                >
                  Ingest Study
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: CLINICIAN FINDING REVIEW */}
      {showReviewFindingModal && selectedFinding && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4 text-white">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-base font-bold">Clinician Finding Review Sign-off</span>
              <button onClick={() => setShowReviewFindingModal(false)} className="text-slate-400 hover:text-slate-200">
                ✕
              </button>
            </div>

            <form onSubmit={handleReviewFinding} className="space-y-4 text-xs">
              <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-1">
                <span className="font-semibold text-slate-300 block">{selectedFinding.finding_type}</span>
                <p className="text-slate-400">{selectedFinding.description}</p>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Clinician Determination</label>
                <select
                  value={reviewFindingForm.review_status}
                  onChange={(e) =>
                    setReviewFindingForm({
                      ...reviewFindingForm,
                      review_status: e.target.value as FindingReviewStatus,
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-slate-200 font-semibold"
                >
                  <option value="confirmed">Confirm Finding (Clinician Verified)</option>
                  <option value="rejected">Reject Finding (False Positive / Artifact)</option>
                  <option value="amended">Amend Finding</option>
                </select>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Clinical Review Notes</label>
                <textarea
                  rows={3}
                  placeholder="Notes on anatomical correlation or diagnostic nuances..."
                  value={reviewFindingForm.review_notes}
                  onChange={(e) => setReviewFindingForm({ ...reviewFindingForm, review_notes: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowReviewFindingModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg"
                >
                  Record Review
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: FINALIZE & SIGN REPORT */}
      {showFinalizeModal && activeReport && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4 text-white">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-base font-bold">Attest & Electronically Sign Radiology Report</span>
              <button onClick={() => setShowFinalizeModal(false)} className="text-slate-400 hover:text-slate-200">
                ✕
              </button>
            </div>

            <form onSubmit={handleFinalizeReport} className="space-y-4 text-xs">
              <div className="p-3 bg-blue-950/40 border border-blue-800 rounded-lg space-y-1 text-slate-300">
                <span className="font-bold text-blue-300 block">Clinician Attestation Requirement</span>
                <p>
                  By finalizing this report, you certify that you have reviewed the diagnostic imaging data and that the findings, impression, and recommendations reflect your professional medical judgment.
                </p>
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Electronic Signature Remarks / Notes</label>
                <input
                  type="text"
                  placeholder="e.g. Electronically verified and signed after full radiologic examination review."
                  value={signatureNotes}
                  onChange={(e) => setSignatureNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowFinalizeModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg shadow-sm"
                  data-testid="confirm-finalize-btn"
                >
                  Confirm & Finalize Sign-Off
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: REPORT AMENDMENT ADDENDUM */}
      {showAmendModal && activeReport && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4 text-white">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <span className="text-base font-bold">Issue Report Amendment Addendum</span>
              <button onClick={() => setShowAmendModal(false)} className="text-slate-400 hover:text-slate-200">
                ✕
              </button>
            </div>

            <form onSubmit={handleAmendReport} className="space-y-4 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Reason for Clinical Amendment</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Comparative reassessment with prior film indicates clearing infiltrate"
                  value={amendmentReason}
                  onChange={(e) => setAmendmentReason(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Amended Impression Narrative</label>
                <textarea
                  rows={3}
                  value={reportEditForm.impression}
                  onChange={(e) => setReportEditForm({ ...reportEditForm, impression: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 font-mono"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAmendModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading || !amendmentReason}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded-lg shadow-sm disabled:opacity-50"
                  data-testid="confirm-amend-btn"
                >
                  Issue Amended Version
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
