// ==============================================================================
// MediGen AI - Multi-Modal Medical Diagnostics & Imaging Workspace
// ==============================================================================

import React, { useEffect, useState, useCallback } from 'react';
import { mediaApi } from '../../api/client';
import { DiagnosticMedia, MediaBodySite, MediaModality } from '../../types';

interface MediaDiagnosticsHubProps {
  patientId?: string;
  onTriggerAnalysis: (mediaId: string) => Promise<any>;
}

export const MediaDiagnosticsHub: React.FC<MediaDiagnosticsHubProps> = ({
  patientId,
  onTriggerAnalysis,
}) => {
  const [mediaList, setMediaList] = useState<DiagnosticMedia[]>([]);
  const [selectedMedia, setSelectedMedia] = useState<DiagnosticMedia | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadTitle, setUploadTitle] = useState<string>('');
  const [modality, setModality] = useState<MediaModality>('xray_chest');
  const [bodySite, setBodySite] = useState<MediaBodySite>('chest');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Review state
  const [clinicianConfirmed, setClinicianConfirmed] = useState<boolean>(true);
  const [clinicianNotes, setClinicianNotes] = useState<string>('');
  const [isSigningOff, setIsSigningOff] = useState<boolean>(false);

  const loadMediaList = useCallback(async () => {
    if (!patientId) {
      setMediaList([]);
      setSelectedMedia(null);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await mediaApi.list(patientId);
      setMediaList(res.items);
      if (res.items.length > 0 && !selectedMedia) {
        setSelectedMedia(res.items[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load diagnostic media records.');
    } finally {
      setIsLoading(false);
    }
  }, [patientId, selectedMedia]);

  useEffect(() => {
    loadMediaList();
  }, [loadMediaList]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientId || !selectedFile || !uploadTitle.trim()) {
      setError('Please provide an image title and select a diagnostic media file.');
      return;
    }

    setIsUploading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const newMedia = await mediaApi.upload(
        patientId,
        selectedFile,
        uploadTitle.trim(),
        modality,
        bodySite
      );
      setSuccessMsg(`Diagnostic study "${newMedia.title}" registered successfully.`);
      setUploadTitle('');
      setSelectedFile(null);
      await loadMediaList();
      setSelectedMedia(newMedia);
      // Auto trigger background analysis
      await onTriggerAnalysis(newMedia.media_id);
    } catch (err: any) {
      setError(err.message || 'Failed to upload diagnostic media.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleReviewSignoff = async () => {
    if (!selectedMedia) return;
    setIsSigningOff(true);
    setError(null);
    try {
      const updated = await mediaApi.review(
        selectedMedia.media_id,
        clinicianConfirmed,
        clinicianNotes.trim() || undefined
      );
      setSelectedMedia(updated);
      await loadMediaList();
      setSuccessMsg('Clinician review and verification successfully saved.');
    } catch (err: any) {
      setError(err.message || 'Failed to record clinician review signoff.');
    } finally {
      setIsSigningOff(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'reviewed':
        return <span className="badge badge-success">Physician Verified</span>;
      case 'analyzed':
        return <span className="badge badge-warning">AI Analyzed (Review Pending)</span>;
      case 'analyzing':
        return <span className="badge badge-info">AI Analyzing...</span>;
      case 'uploaded':
        return <span className="badge">Uploaded</span>;
      case 'failed':
        return <span className="badge badge-danger">Analysis Failed</span>;
      default:
        return <span className="badge">{status}</span>;
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '16px', height: '100%' }}>
      {/* Left: Upload Form & Studies List */}
      <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>🖼️</span>
            Imaging Studies ({mediaList.length})
          </h3>
          <button className="btn btn-secondary btn-sm" onClick={loadMediaList} disabled={isLoading || !patientId}>
            ↻
          </button>
        </div>

        {/* Media Upload Dropzone */}
        {patientId && (
          <form onSubmit={handleUpload} style={{ background: 'rgba(255,255,255,0.02)', border: '1px dashed var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px', marginBottom: '14px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginBottom: '8px' }}>
              <input
                type="text"
                className="form-input"
                placeholder="Study Title (e.g. Chest X-Ray PA)"
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                style={{ padding: '6px 10px', fontSize: '0.8125rem' }}
              />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                <select
                  className="form-select"
                  value={modality}
                  onChange={(e) => setModality(e.target.value as MediaModality)}
                  style={{ padding: '4px 6px', fontSize: '0.75rem' }}
                >
                  <option value="xray_chest">Chest X-Ray</option>
                  <option value="ct_scan">CT Scan</option>
                  <option value="mri">MRI</option>
                  <option value="ultrasound">Ultrasound</option>
                  <option value="dermatology">Dermatology</option>
                  <option value="pathology">Pathology</option>
                  <option value="other">Other</option>
                </select>
                <select
                  className="form-select"
                  value={bodySite}
                  onChange={(e) => setBodySite(e.target.value as MediaBodySite)}
                  style={{ padding: '4px 6px', fontSize: '0.75rem' }}
                >
                  <option value="chest">Chest</option>
                  <option value="brain">Brain</option>
                  <option value="abdomen">Abdomen</option>
                  <option value="pelvis">Pelvis</option>
                  <option value="extremity">Extremity</option>
                  <option value="skin">Skin</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.webp,.tiff,.tif,.dcm,.dicom,.pdf"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}
              />
              <button
                type="submit"
                className="btn btn-primary btn-sm"
                disabled={isUploading || !selectedFile || !uploadTitle.trim()}
              >
                {isUploading ? 'Uploading...' : 'Upload & Analyze'}
              </button>
            </div>
          </form>
        )}

        {/* Media Records List */}
        <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {mediaList.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem', padding: '24px 0' }}>
              {isLoading ? 'Loading imaging records...' : 'No clinical imaging studies recorded.'}
            </div>
          ) : (
            mediaList.map((media) => {
              const isSelected = selectedMedia?.media_id === media.media_id;
              return (
                <div
                  key={media.media_id}
                  onClick={() => setSelectedMedia(media)}
                  style={{
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-sm)',
                    background: isSelected ? 'rgba(2, 132, 199, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                    border: isSelected ? '1px solid var(--brand-primary)' : '1px solid var(--border-color)',
                    cursor: 'pointer',
                    transition: 'all var(--transition-fast)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.8125rem', color: isSelected ? '#ffffff' : 'var(--text-primary)' }}>
                      {media.title}
                    </span>
                    <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>
                      {media.modality.toUpperCase()}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    <span>{new Date(media.created_at).toLocaleDateString()}</span>
                    {getStatusBadge(media.status)}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right: Study Diagnostic Viewer & Findings Panel */}
      <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        {selectedMedia ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Header & Meta */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
              <div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  {selectedMedia.title}
                </h3>
                <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  <span>Study ID: <strong style={{ color: 'var(--text-secondary)' }}>{selectedMedia.media_id}</strong></span>
                  <span>Modality: <strong style={{ color: 'var(--text-secondary)' }}>{(selectedMedia.modality || 'other').toUpperCase()}</strong></span>
                  {selectedMedia.body_site && <span>Body Site: <strong style={{ color: 'var(--text-secondary)' }}>{selectedMedia.body_site.toUpperCase()}</strong></span>}
                  <span>Size: <strong style={{ color: 'var(--text-secondary)' }}>{((selectedMedia.file_size_bytes || 0) / 1024).toFixed(1)} KB</strong></span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => onTriggerAnalysis(selectedMedia.media_id)}
                  title="Re-run AI Multi-Modal Imaging Analysis"
                >
                  ⚡ Re-Analyze
                </button>
              </div>
            </div>

            {/* Status & Confidence Gauge */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 180px', gap: '12px' }}>
              <div style={{ padding: '12px 14px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '4px' }}>
                  Diagnostic Status
                </div>
                <div>{getStatusBadge(selectedMedia.status)}</div>
              </div>

              <div style={{ padding: '12px 14px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '2px' }}>
                  AI Confidence
                </div>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--brand-primary)' }}>
                  {selectedMedia.confidence_score ? `${Math.round(selectedMedia.confidence_score * 100)}%` : 'N/A'}
                </div>
              </div>
            </div>

            {/* AI Structured Findings Card */}
            <div style={{ padding: '16px', background: 'rgba(2,132,199,0.06)', border: '1px solid rgba(2,132,199,0.3)', borderRadius: 'var(--radius-sm)' }}>
              <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <span>🧠</span>
                AI Multi-Modal Observations & Findings
              </h4>

              {selectedMedia.findings_summary ? (
                <div>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '12px' }}>
                    {selectedMedia.findings_summary}
                  </p>

                  {selectedMedia.structured_findings?.findings && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                        Anatomical Detail:
                      </span>
                      {selectedMedia.structured_findings.findings.map((f: any, idx: number) => (
                        <div key={idx} style={{ fontSize: '0.8125rem', padding: '6px 10px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', display: 'flex', justifyContent: 'space-between' }}>
                          <span>• <strong>{f.anatomical_region}:</strong> {f.observation}</span>
                          <span style={{ color: 'var(--brand-primary)', fontWeight: 600 }}>{Math.round(f.confidence * 100)}%</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {selectedMedia.structured_findings?.differential_notes && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <strong>Differential Notes:</strong> {selectedMedia.structured_findings.differential_notes.join(' • ')}
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', fontStyle: 'italic' }}>
                  No AI findings generated yet. Click Re-Analyze to execute multi-modal evaluation.
                </div>
              )}

              {/* Mandatory Clinical Safety Disclaimer */}
              <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.08)', fontSize: '0.7rem', color: '#fbbf24', fontStyle: 'italic' }}>
                ⚠️ AI decision support observation only. Must be validated by a certified radiologist/clinician. Does not constitute a confirmed diagnosis.
              </div>
            </div>

            {/* Clinician Review & Verification Form */}
            <div style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}>
              <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>👨‍⚕️</span>
                Physician Verification & Signoff
              </h4>

              {selectedMedia.clinician_confirmed ? (
                <div style={{ padding: '10px 12px', background: 'var(--success-bg)', border: '1px solid var(--success-border)', borderRadius: '4px', color: '#34d399', fontSize: '0.8125rem' }}>
                  ✅ <strong>Verified by Attending Physician</strong> {selectedMedia.reviewed_at && `on ${new Date(selectedMedia.reviewed_at).toLocaleDateString()}`}
                  {selectedMedia.clinician_notes && (
                    <div style={{ marginTop: '4px', color: 'var(--text-secondary)' }}>
                      Notes: {selectedMedia.clinician_notes}
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: 'var(--text-primary)', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={clinicianConfirmed}
                      onChange={(e) => setClinicianConfirmed(e.target.checked)}
                    />
                    I have reviewed the diagnostic study and confirm the clinical interpretation.
                  </label>

                  <textarea
                    className="form-textarea"
                    placeholder="Add clinician review notes, differential remarks, or clinical signoff..."
                    rows={2}
                    value={clinicianNotes}
                    onChange={(e) => setClinicianNotes(e.target.value)}
                    style={{ fontSize: '0.8125rem' }}
                  />

                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={handleReviewSignoff}
                      disabled={isSigningOff}
                    >
                      {isSigningOff ? 'Saving Review...' : 'Sign Off & Confirm Study'}
                    </button>
                  </div>
                </div>
              )}
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
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: '64px 0', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>🖼️</div>
            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              No Diagnostic Study Selected
            </div>
            <p style={{ fontSize: '0.8125rem', maxWidth: '360px', margin: '6px auto 0' }}>
              Upload or select a medical imaging study from the list to view multi-modal AI analysis and record physician signoff.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
