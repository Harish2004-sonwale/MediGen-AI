// ==============================================================================
// MediGen AI - Robust Clinical React Error Boundary
// ==============================================================================

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('MediGen AI React Error Boundary caught:', error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            padding: '32px 24px',
            minHeight: '280px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--card-bg, #0f172a)',
            border: '1px solid var(--border-color, rgba(255,255,255,0.1))',
            borderRadius: '12px',
            margin: '16px',
            textAlign: 'center',
            color: 'var(--text-primary, #f8fafc)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
          }}
        >
          <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>⚠️</div>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fca5a5', marginBottom: '8px' }}>
            {this.props.fallbackTitle || 'Workspace Display Error'}
          </h3>
          <p style={{ maxWidth: '520px', color: 'var(--text-secondary, #94a3b8)', fontSize: '0.875rem', marginBottom: '20px', lineHeight: 1.5 }}>
            An unexpected error occurred while rendering this clinical section. The application safeguarded clinical state and prevented an unrecoverable failure.
          </p>

          {this.state.error && (
            <div
              style={{
                maxWidth: '600px',
                width: '100%',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                borderRadius: '6px',
                padding: '10px 14px',
                fontSize: '0.75rem',
                fontFamily: 'monospace',
                color: '#fca5a5',
                textAlign: 'left',
                overflowX: 'auto',
                marginBottom: '20px',
              }}
            >
              {this.state.error.message || String(this.state.error)}
            </div>
          )}

          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', justifyContent: 'center' }}>
            <button
              className="btn btn-primary btn-sm"
              onClick={this.handleReset}
              style={{ padding: '8px 16px', fontWeight: 600 }}
            >
              🔄 Retry Workspace
            </button>
            <button
              className="btn btn-secondary btn-sm"
              onClick={this.handleReload}
              style={{ padding: '8px 16px' }}
            >
              🌐 Reload Application
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
