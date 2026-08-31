import React, { useState, useEffect } from 'react';
import { outboxApi } from '../../api/client';
import { OutboxEvent, OutboxMetrics } from '../../types';

export const OutboxDLQMonitor: React.FC = () => {
  const [events, setEvents] = useState<OutboxEvent[]>([]);
  const [metrics, setMetrics] = useState<OutboxMetrics | null>(null);
  const [loading, setLoading] = useState(false);
  const [replaying, setReplaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [eventsRes, metricsRes] = await Promise.all([
        outboxApi.listEvents(statusFilter || undefined),
        outboxApi.getMetrics(),
      ]);
      setEvents(eventsRes);
      setMetrics(metricsRes);
    } catch (err: any) {
      setError(err.message || 'Failed to load transactional outbox events');
    } finally {
      setLoading(false);
    }
  };

  const handleReplayDLQ = async () => {
    try {
      setReplaying(true);
      setError(null);
      await outboxApi.replayDeadLetters();
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to replay dead letter events');
    } finally {
      setReplaying(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-amber-50 dark:bg-amber-900/30 rounded-xl text-amber-600 dark:text-amber-400 font-bold text-xl">
            📤
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Transactional Outbox & Dead-Letter Queue (DLQ)</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Reliable at-least-once message dispatch with exponential backoff & replay</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition text-sm"
            title="Refresh"
          >
            🔄
          </button>
          {metrics && metrics.dead_letter > 0 && (
            <button
              onClick={handleReplayDLQ}
              disabled={replaying}
              className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold rounded-xl transition flex items-center gap-2"
            >
              <span>🔁</span>
              Replay {metrics.dead_letter} Dead Letters
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl text-xs text-red-600 dark:text-red-400 flex items-center gap-2">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Metrics Cards */}
      {metrics && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-700">
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Total Events</span>
            <div className="text-xl font-bold text-slate-900 dark:text-white mt-1">{metrics.total}</div>
          </div>
          <div className="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-700">
            <span className="text-[11px] font-bold text-amber-500 uppercase tracking-wider">Pending Backlog</span>
            <div className="text-xl font-bold text-amber-600 dark:text-amber-400 mt-1">{metrics.pending}</div>
          </div>
          <div className="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-700">
            <span className="text-[11px] font-bold text-emerald-500 uppercase tracking-wider">Dispatched</span>
            <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400 mt-1">{metrics.published}</div>
          </div>
          <div className="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-700">
            <span className="text-[11px] font-bold text-red-500 uppercase tracking-wider">Dead-Letter Queue</span>
            <div className="text-xl font-bold text-red-600 dark:text-red-400 mt-1">{metrics.dead_letter}</div>
          </div>
        </div>
      )}

      {/* Outbox Events Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 dark:bg-slate-900/50 text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="py-3 px-4">Event ID</th>
              <th className="py-3 px-4">Type</th>
              <th className="py-3 px-4">Aggregate</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Attempts</th>
              <th className="py-3 px-4">Error / Details</th>
              <th className="py-3 px-4">Created At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60 font-sans">
            {events.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-400">
                  No outbox events matching query.
                </td>
              </tr>
            ) : (
              events.map((evt) => (
                <tr key={evt.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-700/30 transition">
                  <td className="py-3 px-4 font-mono font-medium text-slate-900 dark:text-white">
                    {evt.event_id}
                  </td>
                  <td className="py-3 px-4 font-semibold text-slate-800 dark:text-slate-200">
                    {evt.event_type}
                  </td>
                  <td className="py-3 px-4 text-slate-500">
                    {evt.aggregate_type}:{evt.aggregate_id}
                  </td>
                  <td className="py-3 px-4">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[11px] font-semibold ${
                        evt.status === 'PUBLISHED'
                          ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400'
                          : evt.status === 'DEAD_LETTER'
                          ? 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                          : evt.status === 'FAILED'
                          ? 'bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'
                          : 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                      }`}
                    >
                      {evt.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-600 dark:text-slate-300">
                    {evt.attempts} / {evt.max_attempts}
                  </td>
                  <td className="py-3 px-4 max-w-xs truncate text-[11px] text-red-500 font-mono">
                    {evt.error_message || '—'}
                  </td>
                  <td className="py-3 px-4 text-slate-400 text-[11px]">
                    {new Date(evt.created_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
