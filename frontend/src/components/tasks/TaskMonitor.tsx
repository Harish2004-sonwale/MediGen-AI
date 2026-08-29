// ==============================================================================
// MediGen AI - Background Task Queue Monitor Modal
// ==============================================================================

import React from 'react';
import { BackgroundTask } from '../../types';

interface TaskMonitorProps {
  tasks: BackgroundTask[];
  isOpen: boolean;
  onClose: () => void;
  onRetry: (taskId: string) => Promise<void>;
  onCancel: (taskId: string) => Promise<void>;
  onRefresh: () => Promise<void>;
}

export const TaskMonitor: React.FC<TaskMonitorProps> = ({
  tasks,
  isOpen,
  onClose,
  onRetry,
  onCancel,
  onRefresh,
}) => {
  if (!isOpen) return null;

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-success">Completed</span>;
      case 'running':
        return <span className="badge badge-info">Running...</span>;
      case 'queued':
        return <span className="badge badge-warning">Queued</span>;
      case 'failed':
        return <span className="badge badge-danger">Failed</span>;
      case 'cancelled':
        return <span className="badge">Cancelled</span>;
      default:
        return <span className="badge">{status}</span>;
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
        padding: '20px',
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '740px',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          padding: '24px',
          boxShadow: 'var(--shadow-lg)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: 'var(--brand-primary)' }}>⚙️</span>
              Background Asynchronous Task Monitor ({tasks.length})
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Real-time progress tracking, retries & cancellation for async OCR and summarization jobs
            </span>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn btn-secondary btn-sm" onClick={onRefresh}>
              ↻ Refresh
            </button>
            <button className="btn btn-secondary btn-sm" onClick={onClose}>
              ✕
            </button>
          </div>
        </div>

        <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {tasks.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '36px 0', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              No background tasks currently recorded in the queue.
            </div>
          ) : (
            tasks.map((task) => {
              const progressPct = Math.round(task.progress * 100);
              return (
                <div
                  key={task.task_id}
                  style={{
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-sm)',
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>
                        {task.task_type.replace('_', ' ').toUpperCase()}
                      </span>
                      <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>
                        {task.task_id}
                      </span>
                    </div>
                    <div>{getStatusBadge(task.status)}</div>
                  </div>

                  {/* Progress Bar */}
                  <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '3px', overflow: 'hidden', margin: '8px 0' }}>
                    <div
                      style={{
                        width: `${progressPct}%`,
                        height: '100%',
                        background: task.status === 'failed' ? '#ef4444' : 'var(--brand-primary)',
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span>
                      Progress: <strong>{progressPct}%</strong> • Created: {new Date(task.created_at).toLocaleTimeString()}
                    </span>

                    <div style={{ display: 'flex', gap: '6px' }}>
                      {task.status === 'failed' && (
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                          onClick={() => onRetry(task.task_id)}
                        >
                          🔄 Retry
                        </button>
                      )}
                      {(task.status === 'queued' || task.status === 'running') && (
                        <button
                          className="btn btn-danger btn-sm"
                          style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                          onClick={() => onCancel(task.task_id)}
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </div>

                  {task.error_message && (
                    <div style={{ marginTop: '6px', fontSize: '0.75rem', color: '#f87171', background: 'rgba(239,68,68,0.1)', padding: '4px 8px', borderRadius: '4px' }}>
                      Error: {task.error_message}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
