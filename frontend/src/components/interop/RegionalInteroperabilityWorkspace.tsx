import React, { useState, useEffect } from 'react';
import {
  empiApi,
  ccdaApi,
  pathwaysApi,
  patientsApi,
} from '../../api/client';
import {
  Patient,
  EMPICandidateMatch,
  EMPIMatchReviewItem,
  CCDAExportResponse,
  CCDAImportResponse,
  CCDADocumentExchange,
  RegionalPathway,
  PatientPathwayEnrollment,
} from '../../types';

export const RegionalInteroperabilityWorkspace: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'empi' | 'ccda' | 'pathways'>('empi');
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // EMPI State
  const [candidates, setCandidates] = useState<EMPICandidateMatch[]>([]);
  const [reviews, setReviews] = useState<EMPIMatchReviewItem[]>([]);
  const [empiThreshold, setEmpiThreshold] = useState<number>(0.65);
  const [isMergeModalOpen, setIsMergeModalOpen] = useState<boolean>(false);
  const [mergeTargetPatientId, setMergeTargetPatientId] = useState<string>('');
  const [mergeSourcePatientId, setMergeSourcePatientId] = useState<string>('');
  const [mergeReason, setMergeReason] = useState<string>('Probable duplicate patient record resolution');

  // C-CDA State
  const [ccdaDocType, setCcdaDocType] = useState<string>('continuity_of_care_document');
  const [exportedCCDA, setExportedCCDA] = useState<CCDAExportResponse | null>(null);
  const [importXmlText, setImportXmlText] = useState<string>('');
  const [importedCCDA, setImportedCCDA] = useState<CCDAImportResponse | null>(null);
  const [docExchanges, setDocExchanges] = useState<CCDADocumentExchange[]>([]);

  // Regional Pathways State
  const [pathways, setPathways] = useState<RegionalPathway[]>([]);
  const [selectedPathwayId, setSelectedPathwayId] = useState<string>('');
  const [patientEnrollments, setPatientEnrollments] = useState<PatientPathwayEnrollment[]>([]);
  const [varianceReason, setVarianceReason] = useState<string>('');

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedPatientId) {
      if (activeTab === 'empi') loadEMPICandidates(selectedPatientId);
      if (activeTab === 'ccda') loadCCDADocuments(selectedPatientId);
      if (activeTab === 'pathways') loadPatientPathways(selectedPatientId);
    }
  }, [selectedPatientId, activeTab]);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      const patientList = await patientsApi.list();
      setPatients(patientList || []);
      const firstPatientId = patientList && patientList.length > 0 ? patientList[0].patient_id : '';
      if (firstPatientId) {
        setSelectedPatientId(firstPatientId);
        await Promise.all([
          loadEMPICandidates(firstPatientId),
          loadCCDADocuments(firstPatientId),
          loadPatientPathways(firstPatientId),
        ]);
      }

      const revRes = await empiApi.listReviews();
      setReviews(revRes || []);

      const pathRes = await pathwaysApi.listPathways();
      setPathways(pathRes.pathways || []);
      if (pathRes.pathways?.length > 0) {
        setSelectedPathwayId(pathRes.pathways[0].pathway_id);
      }
    } catch (err: any) {
      console.error('Failed to load initial interop data:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadEMPICandidates = async (patientId: string) => {
    try {
      setLoading(true);
      const res = await empiApi.findCandidateMatches(patientId, empiThreshold);
      setCandidates(res.candidates || []);
    } catch (err: any) {
      console.error('Failed to load candidate matches:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLinkPatient = async (targetId: string, candId: string) => {
    try {
      setLoading(true);
      await empiApi.linkPatient({ target_patient_id: targetId, patient_id: candId });
      setStatusMessage({ type: 'success', text: `Successfully linked patient ${candId} to enterprise identity.` });
      await loadEMPICandidates(targetId);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to link patient.' });
    } finally {
      setLoading(false);
    }
  };

  const handleUnlinkPatient = async (patientId: string) => {
    try {
      setLoading(true);
      await empiApi.unlinkPatient(patientId, 'Clinical decoupling requested');
      setStatusMessage({ type: 'success', text: `Successfully unlinked patient ${patientId}.` });
      if (selectedPatientId) await loadEMPICandidates(selectedPatientId);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to unlink patient.' });
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteMerge = async () => {
    if (!mergeTargetPatientId || !mergeSourcePatientId) return;
    try {
      setLoading(true);
      const res = await empiApi.mergeIdentities({
        target_patient_id: mergeTargetPatientId,
        source_patient_id: mergeSourcePatientId,
        reason: mergeReason,
      });
      setStatusMessage({ type: 'success', text: res.message });
      setIsMergeModalOpen(false);
      if (selectedPatientId) await loadEMPICandidates(selectedPatientId);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to merge patient identities.' });
    } finally {
      setLoading(false);
    }
  };

  const handleResolveReview = async (reviewId: string, action: 'confirm_link' | 'reject_match') => {
    try {
      setLoading(true);
      await empiApi.resolveReview(reviewId, action, 'Resolved from Clinical Interop Workspace');
      setStatusMessage({ type: 'success', text: `Review ${reviewId} resolved as ${action}.` });
      const revRes = await empiApi.listReviews();
      setReviews(revRes);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to resolve review.' });
    } finally {
      setLoading(false);
    }
  };

  // C-CDA Actions
  const handleExportCCDA = async () => {
    if (!selectedPatientId) return;
    try {
      setLoading(true);
      const res = await ccdaApi.exportDocument(selectedPatientId, ccdaDocType);
      setExportedCCDA(res);
      setImportXmlText(res.xml_content);
      setStatusMessage({ type: 'success', text: `Generated HL7 C-CDA R2.1 document (ID: ${res.document_id}).` });
      await loadCCDADocuments(selectedPatientId);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to export C-CDA document.' });
    } finally {
      setLoading(false);
    }
  };

  const handleImportCCDA = async () => {
    if (!selectedPatientId || !importXmlText.trim()) return;
    try {
      setLoading(true);
      const res = await ccdaApi.importDocument({
        patient_id: selectedPatientId,
        xml_content: importXmlText,
        source_facility: 'External Regional Health Network',
      });
      setImportedCCDA(res);
      setStatusMessage({ type: 'success', text: `Successfully parsed C-CDA document. Extracted ${res.sections.length} clinical sections.` });
      await loadCCDADocuments(selectedPatientId);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to parse C-CDA document.' });
    } finally {
      setLoading(false);
    }
  };

  const loadCCDADocuments = async (patientId: string) => {
    try {
      const res = await ccdaApi.listDocuments(patientId);
      setDocExchanges(res.documents || []);
    } catch (err: any) {
      console.error('Failed to load C-CDA documents:', err);
    }
  };

  // Regional Pathways Actions
  const loadPatientPathways = async (patientId: string) => {
    try {
      const res = await pathwaysApi.getPatientEnrollments(patientId);
      setPatientEnrollments(res || []);
    } catch (err: any) {
      console.error('Failed to load patient pathways:', err);
    }
  };

  const handleEnrollPathway = async () => {
    if (!selectedPatientId || !selectedPathwayId) return;
    try {
      setLoading(true);
      await pathwaysApi.enrollPatient({
        patient_id: selectedPatientId,
        pathway_id: selectedPathwayId,
      });
      setStatusMessage({ type: 'success', text: `Patient successfully enrolled in clinical pathway.` });
      await loadPatientPathways(selectedPatientId);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to enroll patient in pathway.' });
    } finally {
      setLoading(false);
    }
  };

  const handleAdvanceStage = async (enrollmentId: string) => {
    try {
      setLoading(true);
      await pathwaysApi.advanceStage(enrollmentId, {
        variance_reason: varianceReason.trim() ? varianceReason.trim() : undefined,
      });
      setVarianceReason('');
      setStatusMessage({ type: 'success', text: `Clinical pathway advanced to next stage.` });
      if (selectedPatientId) await loadPatientPathways(selectedPatientId);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to advance pathway stage.' });
    } finally {
      setLoading(false);
    }
  };

  const handleToggleMilestone = async (enrollmentId: string, milestoneId: string) => {
    try {
      await pathwaysApi.completeMilestone(enrollmentId, milestoneId);
      if (selectedPatientId) await loadPatientPathways(selectedPatientId);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to update milestone.' });
    }
  };

  const getGradeBadge = (grade: string) => {
    switch (grade) {
      case 'exact':
        return <span className="badge badge-success">Exact Match</span>;
      case 'probable':
        return <span className="badge badge-warning">Probable Match</span>;
      case 'possible':
        return <span className="badge badge-info">Possible Match</span>;
      default:
        return <span className="badge">Distinct</span>;
    }
  };

  return (
    <div className="space-y-6" style={{ padding: '16px' }}>
      {/* Header Banner */}
      <div className="card" style={{ padding: '20px', background: 'linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%)', color: '#ffffff', borderRadius: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: '0 0 6px 0', color: '#e0e7ff' }}>
              🌐 Regional Interoperability & Care Orchestration
            </h2>
            <p style={{ margin: 0, fontSize: '13px', color: '#94a3b8' }}>
              Federated EMPI Identity Resolution • HL7 C-CDA R2.1 Exchange • Regional Multi-Hospital Clinical Pathways
            </p>
          </div>

          {/* Patient Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(30, 41, 59, 0.8)', padding: '8px 12px', borderRadius: '8px', border: '1px solid #334155' }}>
            <span style={{ fontSize: '12px', fontWeight: 'bold', color: '#38bdf8' }}>Active Patient:</span>
            <select
              value={selectedPatientId}
              onChange={(e) => setSelectedPatientId(e.target.value)}
              style={{ background: '#0f172a', color: '#ffffff', border: '1px solid #475569', borderRadius: '6px', padding: '4px 8px', fontSize: '12px' }}
            >
              {patients.map((p) => (
                <option key={p.patient_id} value={p.patient_id}>
                  {p.first_name} {p.last_name} ({p.patient_id}) - {p.facility_id || 'FAC-MAIN'}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Status Alert */}
      {statusMessage && (
        <div
          style={{
            padding: '12px 16px',
            borderRadius: '8px',
            fontSize: '13px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: statusMessage.type === 'success' ? '#064e3b' : statusMessage.type === 'error' ? '#881337' : '#0c4a6e',
            color: '#f8fafc',
            border: '1px solid rgba(255,255,255,0.2)',
          }}
        >
          <span>{statusMessage.text}</span>
          <button onClick={() => setStatusMessage(null)} style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', textDecoration: 'underline' }}>
            Dismiss
          </button>
        </div>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid #334155', paddingBottom: '8px' }}>
        <button
          onClick={() => setActiveTab('empi')}
          className={`btn btn-sm ${activeTab === 'empi' ? 'btn-primary' : 'btn-secondary'}`}
        >
          🔀 Federated EMPI Identity Resolution
        </button>
        <button
          onClick={() => setActiveTab('ccda')}
          className={`btn btn-sm ${activeTab === 'ccda' ? 'btn-primary' : 'btn-secondary'}`}
        >
          📄 Cross-Hospital C-CDA Exchange
        </button>
        <button
          onClick={() => setActiveTab('pathways')}
          className={`btn btn-sm ${activeTab === 'pathways' ? 'btn-primary' : 'btn-secondary'}`}
        >
          🏥 Regional Clinical Pathways
        </button>
      </div>

      {/* TAB 1: EMPI */}
      {activeTab === 'empi' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card" style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <label style={{ fontSize: '13px', fontWeight: 'bold' }}>Match Sensitivity Threshold:</label>
              <input
                type="range"
                min="0.40"
                max="0.95"
                step="0.05"
                value={empiThreshold}
                onChange={(e) => setEmpiThreshold(parseFloat(e.target.value))}
                style={{ width: '120px' }}
              />
              <span style={{ fontSize: '12px', fontFamily: 'monospace', fontWeight: 'bold', color: '#6366f1' }}>
                {(empiThreshold * 100).toFixed(0)}%
              </span>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => selectedPatientId && loadEMPICandidates(selectedPatientId)}
                className="btn btn-sm btn-secondary"
              >
                🔍 Scan Candidates
              </button>
              <button
                onClick={() => {
                  setMergeTargetPatientId(selectedPatientId);
                  setIsMergeModalOpen(true);
                }}
                className="btn btn-sm btn-primary"
              >
                🔀 Merge Duplicate Records
              </button>
            </div>
          </div>

          {/* Candidates Table */}
          <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 'bold' }}>Probabilistic Identity Resolution Candidates</h3>
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>
                  Weighted scoring: Names (0.35), DOB (0.25), Phone (0.15), Address (0.15), Gender (0.10)
                </span>
              </div>
              <span className="badge badge-info">{candidates.length} Candidate(s) Found</span>
            </div>

            {candidates.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
                No duplicate candidate identities detected above {(empiThreshold * 100).toFixed(0)}% threshold.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'rgba(255,255,255,0.03)', textAlign: 'left', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                      <th style={{ padding: '10px 16px' }}>Candidate Record</th>
                      <th style={{ padding: '10px 16px' }}>Facility</th>
                      <th style={{ padding: '10px 16px' }}>Match Confidence</th>
                      <th style={{ padding: '10px 16px' }}>Feature Breakdown</th>
                      <th style={{ padding: '10px 16px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {candidates.map((cand) => (
                      <tr key={cand.patient_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '10px 16px' }}>
                          <div style={{ fontWeight: 'bold' }}>{cand.first_name} {cand.last_name}</div>
                          <div style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'monospace' }}>
                            ID: {cand.patient_id} • DOB: {cand.date_of_birth} • {cand.gender}
                          </div>
                          {cand.address && <div style={{ fontSize: '11px', color: '#64748b' }}>{cand.address}</div>}
                        </td>
                        <td style={{ padding: '10px 16px' }}>
                          <span className="badge">{cand.facility_id || 'FAC-METRO-WEST'}</span>
                        </td>
                        <td style={{ padding: '10px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontFamily: 'monospace', fontWeight: 'bold' }}>
                              {(cand.match_score * 100).toFixed(1)}%
                            </span>
                            {getGradeBadge(cand.grade)}
                          </div>
                        </td>
                        <td style={{ padding: '10px 16px' }}>
                          <div style={{ display: 'flex', gap: '4px', fontSize: '10px', fontFamily: 'monospace' }}>
                            <span style={{ padding: '2px 6px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px' }}>
                              Name: {(cand.feature_breakdown.name_score * 100).toFixed(0)}%
                            </span>
                            <span style={{ padding: '2px 6px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px' }}>
                              DOB: {(cand.feature_breakdown.dob_score * 100).toFixed(0)}%
                            </span>
                            <span style={{ padding: '2px 6px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px' }}>
                              Phone: {(cand.feature_breakdown.phone_score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: '10px 16px', textAlign: 'right' }}>
                          <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                            <button
                              onClick={() => handleLinkPatient(selectedPatientId, cand.patient_id)}
                              className="btn btn-sm btn-primary"
                              style={{ fontSize: '11px', padding: '4px 8px' }}
                            >
                              🔗 Link Identity
                            </button>
                            <button
                              onClick={() => handleUnlinkPatient(cand.patient_id)}
                              className="btn btn-sm btn-secondary"
                              style={{ fontSize: '11px', padding: '4px 8px' }}
                            >
                              🔓 Unlink
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Pending Match Reviews */}
          <div className="card" style={{ padding: '16px' }}>
            <h3 style={{ margin: '0 0 4px 0', fontSize: '14px', fontWeight: 'bold' }}>EMPI Manual Match Review Queue</h3>
            <p style={{ margin: '0 0 12px 0', fontSize: '11px', color: '#94a3b8' }}>
              Flagged intermediate confidence pairs (65% - 85%) awaiting clinical data steward validation.
            </p>
            {reviews.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '16px', color: '#64748b', fontSize: '12px' }}>
                No active candidate pairs pending manual steward review.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {reviews.map((rev) => (
                  <div
                    key={rev.review_id}
                    style={{
                      padding: '10px 14px',
                      background: 'rgba(255,255,255,0.03)',
                      borderRadius: '8px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '11px', fontFamily: 'monospace', color: '#818cf8', fontWeight: 'bold' }}>
                        {rev.review_id} • Score: {(rev.match_score * 100).toFixed(1)}% • Status: {rev.status}
                      </div>
                      <div style={{ fontSize: '12px', fontWeight: 'bold', marginTop: '2px' }}>
                        Patient {rev.patient_id_a} ({rev.facility_id_a}) ➔ Patient {rev.patient_id_b} ({rev.facility_id_b})
                      </div>
                    </div>
                    {rev.status === 'pending_review' && (
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button
                          onClick={() => handleResolveReview(rev.review_id, 'confirm_link')}
                          className="btn btn-sm btn-primary"
                          style={{ fontSize: '11px', padding: '4px 8px' }}
                        >
                          Confirm Link
                        </button>
                        <button
                          onClick={() => handleResolveReview(rev.review_id, 'reject_match')}
                          className="btn btn-sm btn-secondary"
                          style={{ fontSize: '11px', padding: '4px 8px' }}
                        >
                          Reject
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: C-CDA */}
      {activeTab === 'ccda' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {/* Export */}
            <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <h3 style={{ margin: '0 0 4px 0', fontSize: '14px', fontWeight: 'bold' }}>📤 Export HL7 C-CDA R2.1 Document</h3>
                <p style={{ margin: 0, fontSize: '11px', color: '#94a3b8' }}>
                  Generate Continuity of Care Document (CCD), Referral Note, or Discharge Summary
                </p>
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <select
                  value={ccdaDocType}
                  onChange={(e) => setCcdaDocType(e.target.value)}
                  style={{ flex: 1, padding: '6px 8px', borderRadius: '6px', fontSize: '12px' }}
                >
                  <option value="continuity_of_care_document">Continuity of Care Document (CCD)</option>
                  <option value="referral_note">Referral Note</option>
                  <option value="discharge_summary">Discharge Summary</option>
                </select>

                <button onClick={handleExportCCDA} className="btn btn-sm btn-primary">
                  Generate XML
                </button>
              </div>

              {exportedCCDA && (
                <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8' }}>
                    <span>Doc ID: {exportedCCDA.document_id}</span>
                    <a
                      href={ccdaApi.downloadRawXmlUrl(exportedCCDA.patient_id, exportedCCDA.document_type)}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#38bdf8', textDecoration: 'underline' }}
                    >
                      Download XML
                    </a>
                  </div>
                  <pre
                    style={{
                      maxHeight: '180px',
                      overflowY: 'auto',
                      padding: '8px',
                      background: '#090d16',
                      borderRadius: '6px',
                      fontSize: '11px',
                      fontFamily: 'monospace',
                    }}
                  >
                    {exportedCCDA.xml_content.slice(0, 1200)}...
                  </pre>
                </div>
              )}
            </div>

            {/* Import */}
            <div className="card" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <h3 style={{ margin: '0 0 4px 0', fontSize: '14px', fontWeight: 'bold' }}>📥 Ingest & Parse Inbound C-CDA XML</h3>
                <p style={{ margin: 0, fontSize: '11px', color: '#94a3b8' }}>
                  XXE-safe parsing & automatic clinical section extraction into EHR records
                </p>
              </div>

              <textarea
                value={importXmlText}
                onChange={(e) => setImportXmlText(e.target.value)}
                placeholder="Paste inbound C-CDA XML document content here..."
                rows={5}
                style={{ width: '100%', padding: '8px', fontSize: '11px', fontFamily: 'monospace', borderRadius: '6px' }}
              />

              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  onClick={handleImportCCDA}
                  disabled={!importXmlText.trim()}
                  className="btn btn-sm btn-primary"
                >
                  Validate & Ingest C-CDA
                </button>
              </div>

              {importedCCDA && (
                <div style={{ padding: '10px', background: 'rgba(56, 189, 248, 0.1)', borderRadius: '6px', fontSize: '12px' }}>
                  <div style={{ fontWeight: 'bold', marginBottom: '6px', color: '#38bdf8' }}>
                    Summary: {importedCCDA.title}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '6px', textAlign: 'center', fontFamily: 'monospace' }}>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '4px', borderRadius: '4px' }}>
                      Problems: <b>{importedCCDA.problems_count}</b>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '4px', borderRadius: '4px' }}>
                      Allergies: <b>{importedCCDA.allergies_count}</b>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '4px', borderRadius: '4px' }}>
                      Meds: <b>{importedCCDA.medications_count}</b>
                    </div>
                    <div style={{ background: 'rgba(0,0,0,0.3)', padding: '4px', borderRadius: '4px' }}>
                      Vitals: <b>{importedCCDA.vitals_count}</b>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Audit History */}
          <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 'bold' }}>Cross-Hospital Document Exchange Audit Log</h3>
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Cryptographic SHA-256 integrity verification</span>
            </div>

            {docExchanges.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
                No document exchanges logged for active patient.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', fontSize: '12px', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: 'rgba(255,255,255,0.03)', textAlign: 'left' }}>
                      <th style={{ padding: '8px 12px' }}>Document ID</th>
                      <th style={{ padding: '8px 12px' }}>Direction</th>
                      <th style={{ padding: '8px 12px' }}>Title</th>
                      <th style={{ padding: '8px 12px' }}>SHA-256 Hash</th>
                      <th style={{ padding: '8px 12px' }}>Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {docExchanges.map((doc) => (
                      <tr key={doc.document_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: '#38bdf8' }}>{doc.document_id}</td>
                        <td style={{ padding: '8px 12px' }}>
                          <span className={`badge ${doc.direction === 'export' ? 'badge-info' : 'badge-primary'}`}>
                            {doc.direction.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding: '8px 12px' }}>{doc.title}</td>
                        <td style={{ padding: '8px 12px', fontFamily: 'monospace', color: '#94a3b8' }}>{doc.sha256_hash.slice(0, 16)}...</td>
                        <td style={{ padding: '8px 12px', color: '#94a3b8' }}>{new Date(doc.created_at).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: REGIONAL PATHWAYS */}
      {activeTab === 'pathways' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="card" style={{ padding: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <label style={{ fontSize: '13px', fontWeight: 'bold' }}>Enroll in Regional Protocol:</label>
              <select
                value={selectedPathwayId}
                onChange={(e) => setSelectedPathwayId(e.target.value)}
                style={{ padding: '6px 8px', borderRadius: '6px', fontSize: '12px' }}
              >
                {pathways.map((pw) => (
                  <option key={pw.pathway_id} value={pw.pathway_id}>
                    {pw.name} ({pw.code})
                  </option>
                ))}
              </select>
            </div>

            <button onClick={handleEnrollPathway} className="btn btn-sm btn-primary">
              Enroll Active Patient
            </button>
          </div>

          {patientEnrollments.length === 0 ? (
            <div className="card" style={{ padding: '32px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
              Patient is not currently enrolled in any regional clinical pathways.
            </div>
          ) : (
            patientEnrollments.map((enr) => {
              const pathwayDef = pathways.find((p) => p.pathway_id === enr.pathway_id) || enr.pathway;
              const stages = pathwayDef ? pathwayDef.stages : [];

              return (
                <div key={enr.enrollment_id} className="card" style={{ padding: '0', overflow: 'hidden' }}>
                  <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 'bold' }}>
                          {pathwayDef?.name || 'Regional Clinical Protocol'}
                        </h3>
                        <span className={`badge ${enr.status === 'completed' ? 'badge-success' : 'badge-primary'}`}>
                          {enr.status.toUpperCase()}
                        </span>
                      </div>
                      <span style={{ fontSize: '11px', color: '#94a3b8', fontFamily: 'monospace' }}>
                        Enrollment ID: {enr.enrollment_id}
                      </span>
                    </div>

                    {enr.status === 'active' && (
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        <input
                          type="text"
                          placeholder="Optional variance reason..."
                          value={varianceReason}
                          onChange={(e) => setVarianceReason(e.target.value)}
                          style={{ fontSize: '11px', padding: '4px 8px', borderRadius: '4px', width: '160px' }}
                        />
                        <button
                          onClick={() => handleAdvanceStage(enr.enrollment_id)}
                          className="btn btn-sm btn-primary"
                          style={{ fontSize: '11px', padding: '4px 10px' }}
                        >
                          Advance Stage ➔
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Stages */}
                  <div style={{ padding: '16px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
                    {stages.map((stg) => {
                      const isCurrent = stg.stage_id === enr.current_stage_id;
                      return (
                        <div
                          key={stg.stage_id}
                          style={{
                            padding: '12px',
                            borderRadius: '8px',
                            background: isCurrent ? 'rgba(16, 185, 129, 0.1)' : 'rgba(255,255,255,0.02)',
                            border: isCurrent ? '1px solid #10b981' : '1px solid rgba(255,255,255,0.08)',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#94a3b8', marginBottom: '4px' }}>
                            <span>Stage {stg.sequence_order}</span>
                            <span className="badge" style={{ fontSize: '9px' }}>{stg.assigned_facility_id || 'FAC-METRO-MAIN'}</span>
                          </div>
                          <div style={{ fontWeight: 'bold', fontSize: '13px', marginBottom: '8px' }}>{stg.name}</div>

                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '6px' }}>
                            {stg.milestones.map((ms) => {
                              const isDone = (enr.completed_milestones || []).includes(ms.milestone_id);
                              return (
                                <div
                                  key={ms.milestone_id}
                                  onClick={() => enr.status === 'active' && handleToggleMilestone(enr.enrollment_id, ms.milestone_id)}
                                  style={{
                                    fontSize: '11px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '6px',
                                    cursor: 'pointer',
                                    color: isDone ? '#34d399' : '#94a3b8',
                                  }}
                                >
                                  <span>{isDone ? '☑' : '☐'}</span>
                                  <span>{ms.name}</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* Merge Modal */}
      {isMergeModalOpen && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 100, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
          <div className="card" style={{ maxWidth: '420px', width: '100%', padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>🔀 Merge Duplicate Records</h3>
            <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8' }}>
              Unify multiple patient identities under surviving master ID.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
              <div>
                <label style={{ fontWeight: 'bold' }}>Target Surviving Record:</label>
                <select
                  value={mergeTargetPatientId}
                  onChange={(e) => setMergeTargetPatientId(e.target.value)}
                  style={{ width: '100%', marginTop: '4px', padding: '6px', borderRadius: '6px' }}
                >
                  {patients.map((p) => (
                    <option key={p.patient_id} value={p.patient_id}>
                      {p.first_name} {p.last_name} ({p.patient_id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontWeight: 'bold' }}>Source Duplicate Record:</label>
                <select
                  value={mergeSourcePatientId}
                  onChange={(e) => setMergeSourcePatientId(e.target.value)}
                  style={{ width: '100%', marginTop: '4px', padding: '6px', borderRadius: '6px' }}
                >
                  <option value="">Select source duplicate...</option>
                  {patients
                    .filter((p) => p.patient_id !== mergeTargetPatientId)
                    .map((p) => (
                      <option key={p.patient_id} value={p.patient_id}>
                        {p.first_name} {p.last_name} ({p.patient_id})
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label style={{ fontWeight: 'bold' }}>Merge Clinical Justification:</label>
                <input
                  type="text"
                  value={mergeReason}
                  onChange={(e) => setMergeReason(e.target.value)}
                  style={{ width: '100%', marginTop: '4px', padding: '6px', borderRadius: '6px' }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
              <button onClick={() => setIsMergeModalOpen(false)} className="btn btn-sm btn-secondary">
                Cancel
              </button>
              <button
                onClick={handleExecuteMerge}
                disabled={!mergeSourcePatientId || mergeSourcePatientId === mergeTargetPatientId}
                className="btn btn-sm btn-primary"
              >
                Execute Merge
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
