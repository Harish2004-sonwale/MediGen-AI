// ==============================================================================
// MediGen AI - Real-Time AI Clinical Copilot (SSE Streaming & Citations)
// ==============================================================================

import React, { useState, useRef, useEffect } from 'react';
import { useChatStream } from '../../hooks/useChatStream';

interface ClinicalChatProps {
  patientId?: string;
}

export const ClinicalChat: React.FC<ClinicalChatProps> = ({ patientId }) => {
  const {
    messages,
    isStreaming,
    streamingText,
    streamingCitations,
    error,
    sendMessage,
    abortStreaming,
    startNewSession,
  } = useChatStream(patientId);

  const [inputQuery, setInputQuery] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || isStreaming) return;
    const q = inputQuery;
    setInputQuery('');
    sendMessage(q);
  };

  const handleSuggestedPrompt = (prompt: string) => {
    if (isStreaming) return;
    sendMessage(prompt);
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '16px' }}>
      {/* Copilot Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingBottom: '12px', borderBottom: '1px solid var(--border-color)' }}>
        <div>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--brand-primary)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            Clinical AI Copilot (Grounded RAG)
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Real-time multi-turn clinical intelligence with source citations
          </span>
        </div>

        {patientId && (
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => startNewSession(patientId)}
            disabled={isStreaming}
            title="Start new consultation"
          >
            + New Chat
          </button>
        )}
      </div>

      {/* Message Stream Feed */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 4px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {messages.length === 0 && !isStreaming ? (
          <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🩺</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
              How can MediGen AI assist with this patient?
            </div>
            <p style={{ fontSize: '0.8rem', maxWidth: '380px', margin: '0 auto 16px' }}>
              Ask clinical questions regarding diagnoses, history, medication regimens, or lab observations.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '380px', margin: '0 auto' }}>
              {[
                'Summarize active medications and recent lab findings.',
                'Are there any duplicate prescriptions or allergy conflicts?',
                'What was the primary diagnosis during the last encounter?',
              ].map((suggestion, idx) => (
                <button
                  key={idx}
                  className="btn btn-secondary btn-sm"
                  style={{ textAlign: 'left', justifyContent: 'flex-start', fontSize: '0.75rem' }}
                  onClick={() => handleSuggestedPrompt(suggestion)}
                >
                  💡 {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, index) => {
            const isUser = msg.sender_role === 'user';
            return (
              <div
                key={index}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: isUser ? 'flex-end' : 'flex-start',
                }}
              >
                <div
                  style={{
                    maxWidth: '85%',
                    padding: '12px 16px',
                    borderRadius: isUser ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
                    background: isUser ? 'var(--brand-primary)' : 'var(--bg-input)',
                    color: '#ffffff',
                    fontSize: '0.875rem',
                    lineHeight: '1.5',
                    border: isUser ? 'none' : '1px solid var(--border-color)',
                  }}
                >
                  {msg.content}

                  {/* Citations list */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                      <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.7)', fontWeight: 600, marginBottom: '4px' }}>
                        Sources Cited:
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {msg.citations.map((c, i) => (
                          <span
                            key={i}
                            className="badge badge-info"
                            style={{ fontSize: '0.65rem', textTransform: 'none', background: 'rgba(2, 132, 199, 0.4)' }}
                            title={`Document: ${c.title} (Page ${c.page_number || 1})`}
                          >
                            📄 {c.title} {c.page_number ? `p.${c.page_number}` : ''}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}

        {/* Live SSE Streaming Assistant Message */}
        {isStreaming && (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
            <div
              style={{
                maxWidth: '85%',
                padding: '12px 16px',
                borderRadius: '14px 14px 14px 2px',
                background: 'var(--bg-input)',
                color: '#ffffff',
                fontSize: '0.875rem',
                lineHeight: '1.5',
                border: '1px solid var(--brand-primary)',
              }}
            >
              {streamingText || <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Analyzing records & grounding response...</span>}
              <span className="stream-cursor" />

              {/* Streaming Citations */}
              {streamingCitations.length > 0 && (
                <div style={{ marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.7)', fontWeight: 600, marginBottom: '4px' }}>
                    Grounded Sources:
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                    {streamingCitations.map((c, i) => (
                      <span key={i} className="badge badge-info" style={{ fontSize: '0.65rem', textTransform: 'none' }}>
                        📄 {c.title}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {error && (
          <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.15)', border: '1px solid var(--danger-border)', borderRadius: 'var(--radius-sm)', color: '#fca5a5', fontSize: '0.8125rem' }}>
            ⚠️ {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Query Input Box */}
      <form onSubmit={handleSend} style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
        <input
          type="text"
          className="form-input"
          placeholder="Ask a clinical question about this patient..."
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          disabled={isStreaming}
        />
        {isStreaming ? (
          <button type="button" className="btn btn-danger" onClick={abortStreaming}>
            Stop
          </button>
        ) : (
          <button type="submit" className="btn btn-primary" disabled={!inputQuery.trim()}>
            Send
          </button>
        )}
      </form>
    </div>
  );
};
