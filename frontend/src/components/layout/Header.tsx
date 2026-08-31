// ==============================================================================
// MediGen AI - Header Component
// ==============================================================================

import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { MFAManagementModal } from '../security/MFAManagementModal';

interface HeaderProps {
  onOpenSafetyModal: () => void;
  onOpenTasksModal: () => void;
  activeTaskCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenSafetyModal,
  onOpenTasksModal,
  activeTaskCount,
}) => {
  const { user, logout } = useAuth();
  const [showMFAModal, setShowMFAModal] = useState(false);

  const getRoleBadgeClass = (role?: string) => {
    switch (role) {
      case 'doctor':
        return 'badge-info';
      case 'admin':
        return 'badge-danger';
      case 'healthcare_staff':
        return 'badge-warning';
      default:
        return 'badge-success';
    }
  };

  return (
    <header className="app-header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <a href="/" className="brand-logo">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
            <path d="M12 5v14" />
            <path d="M5 12h14" />
          </svg>
          <span>MediGen <span style={{ color: 'var(--brand-primary)' }}>AI</span></span>
        </a>
        <span style={{ fontSize: '0.75rem', background: 'rgba(255,255,255,0.06)', padding: '2px 8px', borderRadius: '4px', color: 'var(--text-muted)' }}>
          Clinical Intelligence Platform
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Safety CDS Trigger */}
        <button
          className="btn btn-secondary btn-sm"
          onClick={onOpenSafetyModal}
          title="Open Clinical Decision Support Safety Prescriber"
          style={{ borderColor: 'var(--warning-border)', color: '#fbbf24' }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          Safety CDS Check
        </button>

        {/* Task Monitor Trigger */}
        <button
          className="btn btn-secondary btn-sm"
          onClick={onOpenTasksModal}
          title="View Background Asynchronous Task Queue"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          Tasks {activeTaskCount > 0 && <span className="badge badge-info" style={{ marginLeft: '4px' }}>{activeTaskCount}</span>}
        </button>

        {/* User Info & Logout */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', borderLeft: '1px solid var(--border-color)', paddingLeft: '14px' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)' }}>{user.name}</div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '2px' }}>
                <span className={`badge ${getRoleBadgeClass(user.role)}`} style={{ fontSize: '0.65rem' }}>
                  {user.role.replace('_', ' ')}
                </span>
              </div>
            </div>
            <button
              id="btn-header-mfa"
              className="btn btn-secondary btn-sm"
              onClick={() => setShowMFAModal(true)}
              title="Configure Multi-Factor Authentication"
              style={{ color: '#a78bfa', borderColor: 'rgba(167, 139, 250, 0.3)' }}
            >
              🔐 MFA
            </button>
            <button className="btn btn-secondary btn-sm" onClick={logout} title="Sign Out">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              Logout
            </button>
          </div>
        )}
      </div>

      {showMFAModal && (
        <MFAManagementModal onClose={() => setShowMFAModal(false)} />
      )}
    </header>
  );
};
