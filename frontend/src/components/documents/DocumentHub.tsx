// ==============================================================================
// MediGen AI - Medical Document Hub Component
// ==============================================================================

import React, { useEffect, useState, useCallback } from 'react';
import { documentsApi } from '../../api/client';
import { MedicalDocument } from '../../types';

interface DocumentHubProps {
  patientId?: string;
  onTriggerOCR: (documentId: string) => Promise<any>;
}

export const DocumentHub: React.FC<DocumentHubProps> = ({ patientId, onTriggerOCR }) => {
  const [documents, setDocuments] = useState<MedicalDocument[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadTitle, setUploadTitle] = useState<string>('');
  const [documentType, setDocumentType] = useState<string>('lab_report');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    if (!patientId) {
      setDocuments([]);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const docs = await documentsApi.list(patientId);
      setDocuments(docs);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch medical documents.');
    } finally {
      setIsLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientId || !selectedFile || !uploadTitle.trim()) {
      setError('Please provide a document title and select a file.');
      return;
    }

    setIsUploading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const newDoc = await documentsApi.upload(
        patientId,
        selectedFile,
        uploadTitle.trim(),
        documentType
      );
      setSuccessMsg(`Document "${newDoc.title}" uploaded successfully!`);
      setUploadTitle('');
      setSelectedFile(null);
      await loadDocuments();
    } catch (err: any) {
      setError(err.message || 'Failed to upload document.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
          Medical Document Hub ({documents.length})
        </h3>
        <button className="btn btn-secondary btn-sm" onClick={loadDocuments} disabled={isLoading || !patientId}>
          ↻
        </button>
      </div>

      {/* Upload Dropzone Form */}
      {patientId && (
        <form onSubmit={handleUpload} style={{ background: 'rgba(255,255,255,0.02)', border: '1px dashed var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px', marginBottom: '14px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 140px', gap: '8px', marginBottom: '8px' }}>
            <input
              type="text"
              className="form-input"
              placeholder="Document Title..."
              value={uploadTitle}
              onChange={(e) => setUploadTitle(e.target.value)}
              style={{ padding: '6px 10px', fontSize: '0.8125rem' }}
            />
            <select
              className="form-select"
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              style={{ padding: '6px 10px', fontSize: '0.8125rem' }}
            >
              <option value="lab_report">Lab Report</option>
              <option value="discharge_summary">Discharge Summary</option>
              <option value="prescription">Prescription</option>
              <option value="radiology_report">Radiology</option>
              <option value="consultation_note">Consultation</option>
            </select>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}
            />
            <button
              type="submit"
              className="btn btn-primary btn-sm"
              disabled={isUploading || !selectedFile || !uploadTitle.trim()}
            >
              {isUploading ? 'Uploading...' : 'Upload & Index'}
            </button>
          </div>
        </form>
      )}

      {error && (
        <div style={{ color: '#f87171', fontSize: '0.75rem', padding: '6px 8px', background: 'rgba(239,68,68,0.1)', borderRadius: '4px', marginBottom: '8px' }}>
          {error}
        </div>
      )}

      {successMsg && (
        <div style={{ color: '#34d399', fontSize: '0.75rem', padding: '6px 8px', background: 'rgba(16,185,129,0.1)', borderRadius: '4px', marginBottom: '8px' }}>
          {successMsg}
        </div>
      )}

      {/* Document List */}
      <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {documents.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem', padding: '24px 0' }}>
            {isLoading ? 'Loading records...' : 'No medical documents uploaded yet.'}
          </div>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.document_id}
              style={{
                padding: '10px 12px',
                borderRadius: 'var(--radius-sm)',
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.8125rem', color: 'var(--text-primary)' }}>
                  {doc.title}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  {doc.document_type.replace('_', ' ').toUpperCase()} • {(doc.file_size_bytes / 1024).toFixed(1)} KB
                </div>
              </div>

              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '0.7rem', padding: '2px 6px' }}
                  onClick={() => onTriggerOCR(doc.document_id)}
                  title="Trigger background OCR & Vector Re-indexing"
                >
                  ⚡ OCR
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
