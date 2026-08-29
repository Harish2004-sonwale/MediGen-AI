// ==============================================================================
// MediGen AI - Clinical Notes & AI Scribe Workspace
// ==============================================================================

import React, { useEffect, useState, useCallback } from 'react';
import { notesApi } from '../../api/client';
import { ClinicalNote, NoteType } from '../../types';

interface ClinicalNoteWorkspaceProps {
  patientId?: string;
  onTriggerSynthesis: (noteType: NoteType) => Promise<any>;
}

export const ClinicalNoteWorkspace: React.FC<ClinicalNoteWorkspaceProps> = ({
  patientId,
  onTriggerSynthesis,
}) => {
  const [notes, setNotes] = useState<ClinicalNote[]>([]);
  const [selectedNote, setSelectedNote] = useState<ClinicalNote | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isSigningOff, setIsSigningOff] = useState<boolean>(false);
  const [selectedNoteType, setSelectedNoteType] = useState<NoteType>('soap');
  const [editedTitle, setEditedTitle] = useState<string>('');
  const [editedRawText, setEditedRawText] = useState<string>('');
  const [signoffNotes, setSignoffNotes] = useState<string>('');
  const [confirmSignoff, setConfirmSignoff] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadNotes = useCallback(async () => {
    if (!patientId) {
      setNotes([]);
      setSelectedNote(null);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await notesApi.list(patientId);
      setNotes(res.items);
      if (res.items.length > 0 && !selectedNote) {
        selectNote(res.items[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load clinical notes.');
    } finally {
      setIsLoading(false);
    }
  }, [patientId, selectedNote]);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  const selectNote = (note: ClinicalNote) => {
    setSelectedNote(note);
    setEditedTitle(note.title);
    setEditedRawText(note.raw_text);
    setError(null);
    setSuccessMsg(null);
  };

  const handleSynthesize = async () => {
    if (!patientId) return;
    setIsLoading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await onTriggerSynthesis(selectedNoteType);
      setSuccessMsg(`AI Scribe synthesis enqueued for ${selectedNoteType.toUpperCase()} note.`);
      await loadNotes();
    } catch (err: any) {
      setError(err.message || 'Failed to enqueue AI scribe synthesis.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleManualCreate = async () => {
    if (!patientId) return;
    setIsLoading(true);
    setError(null);
    try {
      const defaultTitle = `${selectedNoteType.toUpperCase()} Clinical Note`;
      const defaultText = `CLINICAL NOTE (${selectedNoteType.toUpperCase()})\n\nPatient presented for clinical consultation.\nAssessment & Plan documented.`;
      const created = await notesApi.create(
        patientId,
        defaultTitle,
        selectedNoteType,
        defaultText
      );
      await loadNotes();
      selectNote(created);
      setSuccessMsg('Manual draft note created.');
    } catch (err: any) {
      setError(err.message || 'Failed to create manual note draft.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!selectedNote) return;
    setIsSaving(true);
    setError(null);
    try {
      const updated = await notesApi.update(selectedNote.note_id, {
        title: editedTitle.trim() || undefined,
        raw_text: editedRawText.trim() || undefined,
      });
      selectNote(updated);
      await loadNotes();
      setSuccessMsg('Draft changes saved successfully.');
    } catch (err: any) {
      setError(err.message || 'Failed to update draft note.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleSignoff = async () => {
    if (!selectedNote) return;
    setIsSigningOff(true);
    setError(null);
    try {
      const signed = await notesApi.signoff(
        selectedNote.note_id,
        confirmSignoff,
        signoffNotes.trim() || undefined
      );
      selectNote(signed);
      await loadNotes();
      setSuccessMsg('Clinical note finalized and signed by attending physician.');
    } catch (err: any) {
      setError(err.message || 'Failed to sign off clinical note.');
    } finally {
      setIsSigningOff(false);
    }
  };

  const isFinalized = selectedNote?.status === 'finalized';

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '16px', height: '100%' }}>
      {/* Left: Notes List & Generation Actions */}
      <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>📝</span>
            Clinical Notes ({notes.length})
          </h3>
          <button className="btn btn-secondary btn-sm" onClick={loadNotes} disabled={isLoading || !patientId}>
            ↻
          </button>
        </div>

        {/* Action Controls: Synthesis & Manual Draft */}
        {patientId && (
          <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', padding: '12px', marginBottom: '14px' }}>
            <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px', display: 'block' }}>
              Note Template Type
            </label>
            <select
              className="form-select"
              value={selectedNoteType}
              onChange={(e) => setSelectedNoteType(e.target.value as NoteType)}
              style={{ width: '100%', marginBottom: '10px', fontSize: '0.8125rem' }}
            >
              <option value="soap">SOAP Note</option>
              <option value="consultation">Consultation Summary</option>
              <option value="discharge_summary">Discharge Summary</option>
              <option value="procedure_note">Procedure Note</option>
              <option value="referral_letter">Referral Letter</option>
            </select>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleSynthesize}
                disabled={isLoading}
                title="Synthesize note from patient timeline, encounters, chat, and diagnostics"
              >
                ⚡ AI Scribe
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleManualCreate}
                disabled={isLoading}
              >
                ➕ New Draft
              </button>
            </div>
          </div>
        )}

        {/* Note List */}
        <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {notes.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem', padding: '24px 0' }}>
              {isLoading ? 'Loading clinical notes...' : 'No clinical notes recorded.'}
            </div>
          ) : (
            notes.map((note) => {
              const isSelected = selectedNote?.note_id === note.note_id;
              return (
                <div
                  key={note.note_id}
                  onClick={() => selectNote(note)}
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
                      {note.title}
                    </span>
                    <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>
                      {note.note_type.toUpperCase()}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                    <span>{new Date(note.created_at).toLocaleDateString()}</span>
                    {note.status === 'finalized' ? (
                      <span className="badge badge-success">Finalized</span>
                    ) : (
                      <span className="badge badge-warning">Draft</span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right: Note Detail & Editor Workspace */}
      <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
        {selectedNote ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
              <div style={{ flex: 1, marginRight: '16px' }}>
                {isFinalized ? (
                  <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {selectedNote.title}
                  </h3>
                ) : (
                  <input
                    type="text"
                    className="form-input"
                    value={editedTitle}
                    onChange={(e) => setEditedTitle(e.target.value)}
                    style={{ fontSize: '1rem', fontWeight: 700 }}
                  />
                )}
                <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>
                  <span>Note ID: <strong style={{ color: 'var(--text-secondary)' }}>{selectedNote.note_id}</strong></span>
                  <span>Type: <strong style={{ color: 'var(--text-secondary)' }}>{selectedNote.note_type.toUpperCase()}</strong></span>
                  <span>Created: <strong style={{ color: 'var(--text-secondary)' }}>{new Date(selectedNote.created_at).toLocaleDateString()}</strong></span>
                  {selectedNote.is_ai_generated && <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>AI Assisted</span>}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                {isFinalized ? (
                  <span className="badge badge-success" style={{ padding: '6px 12px', fontSize: '0.8125rem' }}>
                    ✅ Signed & Finalized
                  </span>
                ) : (
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleSaveDraft}
                    disabled={isSaving}
                  >
                    {isSaving ? 'Saving...' : '💾 Save Draft'}
                  </button>
                )}
              </div>
            </div>

            {/* Mandatory AI Scribe Disclaimer */}
            {selectedNote.is_ai_generated && !isFinalized && (
              <div style={{ padding: '10px 14px', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: 'var(--radius-sm)', color: '#fbbf24', fontSize: '0.75rem', lineHeight: '1.4' }}>
                ⚠️ <strong>AI Clinical Scribe Draft:</strong> Generated as clinical decision support. Must be reviewed, amended, and signed off by the attending physician before clinical reliance.
              </div>
            )}

            {/* Note Narrative Editor / Viewer */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Clinical Note Content
              </label>
              {isFinalized ? (
                <div style={{ padding: '14px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)', whiteSpace: 'pre-wrap', fontSize: '0.875rem', lineHeight: '1.6', color: 'var(--text-primary)' }}>
                  {selectedNote.raw_text}
                </div>
              ) : (
                <textarea
                  className="form-textarea"
                  rows={14}
                  value={editedRawText}
                  onChange={(e) => setEditedRawText(e.target.value)}
                  style={{ fontFamily: 'monospace', fontSize: '0.8125rem', lineHeight: '1.5' }}
                />
              )}
            </div>

            {/* Physician Verification & Signoff Card */}
            <div style={{ padding: '16px', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', borderRadius: 'var(--radius-sm)' }}>
              <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>👨‍⚕️</span>
                Attending Physician Review & Signoff
              </h4>

              {isFinalized ? (
                <div style={{ padding: '10px 12px', background: 'var(--success-bg)', border: '1px solid var(--success-border)', borderRadius: '4px', color: '#34d399', fontSize: '0.8125rem' }}>
                  ✅ <strong>Legally Finalized & Signed</strong> {selectedNote.signed_at && `on ${new Date(selectedNote.signed_at).toLocaleDateString()}`}
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: 'var(--text-primary)', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={confirmSignoff}
                      onChange={(e) => setConfirmSignoff(e.target.checked)}
                    />
                    I confirm that I have reviewed this clinical note for accuracy and approve finalization into the patient record.
                  </label>

                  <textarea
                    className="form-textarea"
                    placeholder="Add optional physician signoff remarks, addenda, or clinical directives..."
                    rows={2}
                    value={signoffNotes}
                    onChange={(e) => setSignoffNotes(e.target.value)}
                    style={{ fontSize: '0.8125rem' }}
                  />

                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={handleSignoff}
                      disabled={isSigningOff || !confirmSignoff}
                    >
                      {isSigningOff ? 'Finalizing...' : '✍️ Sign Off & Finalize Note'}
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
            <div style={{ fontSize: '2.5rem', marginBottom: '8px' }}>📝</div>
            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
              No Clinical Note Selected
            </div>
            <p style={{ fontSize: '0.8125rem', maxWidth: '360px', margin: '6px auto 0' }}>
              Select a clinical note from the left panel or click <strong>⚡ AI Scribe</strong> to synthesize documentation from patient history.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
