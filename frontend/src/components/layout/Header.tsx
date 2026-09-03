// ==============================================================================
// MediGen AI - Header Component with Active Facility Context Selector
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
  const { user, logout, activeFacilityId, activeFacility, availableFacilities, setActiveFacility } = useAuth();
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

  const currentFacilityName = activeFacility?.name || activeFacilityId || 'Primary Facility';
  const currentFacilityCode = activeFacility?.facility_code || activeFacilityId || 'FAC-001';

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

        {/* Active Facility Context Ribbon & Selector */}
        {user && (
          <div
            data-testid="header-facility-ribbon"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'linear-gradient(90deg, rgba(2, 132, 199, 0.12) 0%, rgba(15, 23, 42, 0.5) 100%)',
              border: '1px solid rgba(2, 132, 199, 0.3)',
              borderRadius: '6px',
              padding: '3px 10px',
              marginLeft: '8px',
            }}
          >
            <span style={{ fontSize: '0.9rem' }}>🏥</span>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.625rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--brand-primary)', fontWeight: 600 }}>
                Active Facility
              </span>
              {availableFacilities.length > 1 ? (
                <select
                  data-testid="header-facility-selector"
                  value={activeFacilityId || ''}
                  onChange={(e) => setActiveFacility(e.target.value)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-primary)',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    outline: 'none',
                    cursor: 'pointer',
                    padding: '0 4px 0 0',
                  }}
                  title="Switch Active Clinical Facility Context"
                >
                  {availableFacilities.map((fac) => (
                    <option key={fac.facility_id} value={fac.facility_id} style={{ background: '#0f172a', color: '#f8fafc' }}>
                      {fac.name} ({fac.facility_code})
                    </option>
                  ))}
                </select>
              ) : (
                <span
                  data-testid="active-facility-badge"
                  style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)' }}
                  title={`Facility Code: ${currentFacilityCode}`}
                >
                  {currentFacilityName} <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>({currentFacilityCode})</span>
                </span>
              )}
            </div>
          </div>
        )}
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
              <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                {user.name || (user.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : '') || 'Clinician'}
              </div>
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
