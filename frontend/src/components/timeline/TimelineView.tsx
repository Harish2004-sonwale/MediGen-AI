// ==============================================================================
// MediGen AI - Longitudinal Timeline & AI Summary Component
// ==============================================================================

import React, { useEffect, useState, useCallback } from 'react';
import { timelineApi } from '../../api/client';
import { TimelineEvent, TimelineSummary } from '../../types';

interface TimelineViewProps {
  patientId?: string;
}

export const TimelineView: React.FC<TimelineViewProps> = ({ patientId }) => {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [summary, setSummary] = useState<TimelineSummary | null>(null);
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSummaryLoading, setIsSummaryLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadTimeline = useCallback(async () => {
    if (!patientId) {
      setEvents([]);
      setSummary(null);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const data = await timelineApi.getTimeline(patientId, eventTypeFilter || undefined);
      setEvents(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load timeline events.');
    } finally {
      setIsLoading(false);
    }
  }, [patientId, eventTypeFilter]);

  const loadSummary = useCallback(async () => {
    if (!patientId) return;
    setIsSummaryLoading(true);
    try {
      const sum = await timelineApi.getSummary(patientId);
      setSummary(sum);
    } catch {
      // Non-blocking summary load
    } finally {
      setIsSummaryLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    loadTimeline();
    loadSummary();
  }, [loadTimeline, loadSummary]);

  const getEventBadge = (type: string) => {
    switch (type) {
      case 'encounter':
        return <span className="badge badge-info">Clinical Encounter</span>;
      case 'document':
        return <span className="badge badge-success">Medical Document</span>;
      case 'appointment':
        return <span className="badge badge-warning">Appointment</span>;
      default:
        return <span className="badge">{type}</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
      {/* AI Longitudinal Summary Card */}
      <div
        className="glass-panel"
        style={{
          padding: '16px',
          borderLeft: '4px solid var(--brand-primary)',
          background: 'linear-gradient(135deg, rgba(2, 132, 199, 0.08) 0%, rgba(17, 24, 39, 0.9) 100%)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--brand-primary)' }}>✨</span>
            AI Longitudinal Narrative Summary
          </h4>
          <button
            className="btn btn-secondary btn-sm"
            onClick={loadSummary}
            disabled={isSummaryLoading || !patientId}
            style={{ fontSize: '0.7rem' }}
          >
            {isSummaryLoading ? 'Synthesizing...' : 'Regenerate'}
          </button>
        </div>

        {isSummaryLoading ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8125rem', fontStyle: 'italic' }}>
            Compiling grounded longitudinal clinical history...
          </div>
        ) : summary ? (
          <div>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '10px' }}>
              {summary.summary}
            </p>
            {summary.citations && summary.citations.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>Citations:</span>
                {summary.citations.map((cit, idx) => (
                  <span
                    key={idx}
                    className="badge badge-info"
                    style={{ fontSize: '0.65rem', textTransform: 'none' }}
                    title={`Source: ${cit.title} (p. ${cit.page_number || 1})`}
                  >
                    📄 {cit.title} {cit.page_number ? `(p. ${cit.page_number})` : ''}
                  </span>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>
            No summary generated yet. Click regenerate to synthesize longitudinal history.
          </div>
        )}
      </div>

      {/* Timeline Event Feed */}
      <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 14 14" />
            </svg>
            Chronological Care Timeline ({events.length})
          </h3>

          <div style={{ display: 'flex', gap: '8px' }}>
            <select
              className="form-select"
              style={{ width: 'auto', padding: '4px 8px', fontSize: '0.75rem' }}
              value={eventTypeFilter}
              onChange={(e) => setEventTypeFilter(e.target.value)}
            >
              <option value="">All Events</option>
              <option value="encounter">Encounters</option>
              <option value="document">Documents</option>
              <option value="appointment">Appointments</option>
            </select>
            <button className="btn btn-secondary btn-sm" onClick={loadTimeline} disabled={isLoading}>
              ↻
            </button>
          </div>
        </div>

        {error && (
          <div style={{ color: '#f87171', fontSize: '0.75rem', padding: '8px', background: 'rgba(239,68,68,0.1)', borderRadius: '4px', marginBottom: '8px' }}>
            {error}
          </div>
        )}

        <div style={{ overflowY: 'auto', flex: 1, paddingRight: '4px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {events.length === 0 ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem', padding: '32px 0' }}>
              {isLoading ? 'Loading timeline...' : 'No clinical events recorded for this patient.'}
            </div>
          ) : (
            events.map((evt) => (
              <div
                key={evt.event_id}
                style={{
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-sm)',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-color)',
                  borderLeft: '3px solid var(--border-focus)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                    {evt.title}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {getEventBadge(evt.event_type)}
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      {new Date(evt.event_date).toLocaleDateString()}
                    </span>
                  </div>
                </div>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                  {evt.summary}
                </p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
