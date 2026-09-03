// ==============================================================================
// MediGen AI - Enterprise Hospital Topbar Header
// Breadcrumbs, facility switcher, task alerts, safety modals, user profile & logout
// ==============================================================================

import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { MFAManagementModal } from '../security/MFAManagementModal';

interface TopbarProps {
  activeSectionTitle: string;
  onOpenSafetyModal?: () => void;
  onOpenTasksModal?: () => void;
  activeTaskCount?: number;
}

export const Topbar: React.FC<TopbarProps> = ({
  activeSectionTitle,
  onOpenSafetyModal,
  onOpenTasksModal,
  activeTaskCount = 0,
}) => {
  const { user, logout, activeFacilityId, activeFacility, availableFacilities, setActiveFacility } = useAuth();
  const [showMFAModal, setShowMFAModal] = useState(false);

  const getRoleBadge = (role?: string) => {
    switch (role) {
      case 'doctor':
        return { label: 'Specialist Physician', bg: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', border: 'rgba(56, 189, 248, 0.3)' };
      case 'admin':
        return { label: 'Hospital Administrator', bg: 'rgba(239, 68, 68, 0.15)', color: '#f87171', border: 'rgba(239, 68, 68, 0.3)' };
      case 'healthcare_staff':
        return { label: 'Clinical Staff', bg: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: 'rgba(245, 158, 11, 0.3)' };
      default:
        return { label: 'Patient Portal', bg: 'rgba(52, 211, 153, 0.15)', color: '#34d399', border: 'rgba(52, 211, 153, 0.3)' };
    }
  };

  const roleInfo = getRoleBadge(user?.role);
  const currentFacilityName = activeFacility?.name || activeFacilityId || 'Metro General Hospital (Main Campus)';

  return (
    <header className="hospital-topbar" data-testid="hospital-topbar">
      {/* Left: Breadcrumbs & Section Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
          <span>Hospital Portal</span>
          <span>/</span>
          <span style={{ color: '#ffffff', fontWeight: 600 }}>{activeSectionTitle}</span>
        </div>

        {/* Active Facility Switcher */}
        {user && (
          <div
            data-testid="header-facility-ribbon"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(2, 132, 199, 0.1)',
              border: '1px solid rgba(2, 132, 199, 0.25)',
              borderRadius: '6px',
              padding: '2px 8px',
              marginLeft: '12px',
            }}
          >
            <span style={{ fontSize: '0.85rem' }}>🏥</span>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {availableFacilities.length > 1 ? (
                <select
                  data-testid="header-facility-selector"
                  value={activeFacilityId || ''}
                  onChange={(e) => setActiveFacility(e.target.value)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#f8fafc',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    outline: 'none',
                    cursor: 'pointer',
                    padding: 0,
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
                  style={{ fontSize: '0.75rem', fontWeight: 600, color: '#f8fafc' }}
                >
                  {currentFacilityName}
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Right: Quick Action Controls & User Info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* Safety Engine Trigger (Doctors & Staff) */}
        {user?.role !== 'patient' && onOpenSafetyModal && (
          <button
            onClick={onOpenSafetyModal}
            className="btn btn-secondary btn-sm"
            style={{
              fontSize: '0.75rem',
              padding: '4px 10px',
              borderColor: 'rgba(245, 158, 11, 0.3)',
              background: 'rgba(245, 158, 11, 0.08)',
              color: '#fbbf24',
            }}
            title="Open Clinical Safety & Drug Interaction Verifier"
          >
            🛡️ Safety Engine
          </button>
        )}

        {/* Active Async Tasks Trigger */}
        {onOpenTasksModal && (
          <button
            onClick={onOpenTasksModal}
            className="btn btn-secondary btn-sm"
            style={{
              fontSize: '0.75rem',
              padding: '4px 10px',
              position: 'relative',
            }}
            title="View Background Processing Tasks & Async Queue"
          >
            ⚡ Tasks {activeTaskCount > 0 && <span style={{ marginLeft: '4px', background: '#0284c7', color: '#fff', padding: '1px 5px', borderRadius: '10px', fontSize: '0.65rem' }}>{activeTaskCount}</span>}
          </button>
        )}

        {/* MFA Security Status */}
        {user && (
          <button
            onClick={() => setShowMFAModal(true)}
            className="btn btn-secondary btn-sm"
            style={{ fontSize: '0.75rem', padding: '4px 10px' }}
            title="Manage Multi-Factor Authentication & Cryptographic Keys"
          >
            🔒 MFA
          </button>
        )}

        {/* User Profile Name & Role Tag */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '3px 8px', background: 'rgba(255,255,255,0.04)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#ffffff' }}>
              {user.name || (user.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : '') || 'Dr. Amit Kulkarni'}
            </span>
            <span
              data-testid="header-role-badge"
              style={{
                fontSize: '0.6875rem',
                fontWeight: 700,
                padding: '2px 6px',
                borderRadius: '4px',
                background: roleInfo.bg,
                color: roleInfo.color,
                border: `1px solid ${roleInfo.border}`,
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}
            >
              {user.role?.toUpperCase() || roleInfo.label}
            </span>
          </div>
        )}

        {/* Logout Button */}
        <button
          onClick={logout}
          className="btn btn-danger btn-sm"
          style={{ fontSize: '0.75rem', padding: '4px 10px' }}
          title="Sign out of MediGen AI"
        >
          Logout
        </button>
      </div>

      {/* MFA Security Management Modal */}
      <MFAManagementModal
        isOpen={showMFAModal}
        onClose={() => setShowMFAModal(false)}
      />
    </header>
  );
};
