// ==============================================================================
// MediGen AI - Enterprise Hospital Topbar Header
// Breadcrumbs, facility switcher, task alerts, safety modals, user profile & logout
// ==============================================================================

import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { authApi } from '../../api/client';
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
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setDeleteError(null);
    if (deleteConfirmText.trim().toUpperCase() !== 'DELETE') {
      setDeleteError("Please type 'DELETE' to confirm.");
      return;
    }
    setIsDeleting(true);
    try {
      await authApi.deleteAccount(deletePassword, 'DELETE');
      setShowDeleteModal(false);
      logout();
    } catch (err: any) {
      setDeleteError(err.message || 'Failed to delete account. Please verify your password.');
    } finally {
      setIsDeleting(false);
    }
  };

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

        {/* Active Facility Context */}
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
              padding: '3px 10px',
              marginLeft: '12px',
            }}
          >
            <span style={{ fontSize: '0.85rem' }}>🏥</span>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span
                style={{
                  fontSize: '0.58rem',
                  color: 'var(--text-muted)',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                CURRENT FACILITY
              </span>
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

      {/* Right: Clean Header Controls & User Info */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* MFA Security Status */}
        {user && (
          <button
            onClick={() => setShowMFAModal(true)}
            className="btn btn-secondary btn-sm"
            style={{ fontSize: '0.75rem', padding: '4px 10px' }}
            title="Manage Multi-Factor Authentication & Cryptographic Keys"
            data-testid="topbar-mfa-btn"
          >
            🔒 MFA
          </button>
        )}


        {/* User Profile Name & Role Tag */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '3px 8px', background: 'rgba(255,255,255,0.04)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#ffffff' }}>
              {user.name || (user.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : '') || user.email || 'User'}
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

        {/* Account Deletion Settings for Clinician / Admin */}
        {user && (
          <button
            onClick={() => {
              setDeletePassword('');
              setDeleteConfirmText('');
              setDeleteError(null);
              setShowDeleteModal(true);
            }}
            className="btn btn-secondary btn-sm"
            style={{ fontSize: '0.75rem', padding: '4px 8px', color: '#fca5a5', borderColor: 'rgba(239, 68, 68, 0.3)' }}
            title="Account Security & Deletion Settings"
            data-testid="topbar-account-settings-btn"
          >
            ⚙️ Account
          </button>
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

      {/* Account Deletion Confirmation Modal */}
      {showDeleteModal && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.8)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 99999,
            padding: '20px',
          }}
        >
          <div className="glass-panel" style={{ width: '100%', maxWidth: '440px', padding: '24px', background: '#0f172a', border: '1px solid rgba(239, 68, 68, 0.4)' }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ef4444', marginBottom: '8px' }}>
              ⚠️ Account Deletion & Deactivation
            </h3>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.5 }}>
              This action will deactivate your user account ({user?.email}) and revoke active sessions. System administrator protection ensures the last active admin cannot be removed.
            </p>

            {deleteError && (
              <div style={{ padding: '8px 12px', background: 'rgba(239,68,68,0.15)', border: '1px solid var(--danger-border)', borderRadius: '6px', color: '#fca5a5', fontSize: '0.8rem', marginBottom: '14px' }}>
                ⚠️ {deleteError}
              </div>
            )}

            <form onSubmit={handleDeleteAccount}>
              <div className="form-group" style={{ marginBottom: '12px' }}>
                <label className="form-label" style={{ fontSize: '0.8rem' }}>Enter Your Password</label>
                <input
                  type="password"
                  className="form-input"
                  data-testid="topbar-delete-password-input"
                  placeholder="Verify your password"
                  value={deletePassword}
                  onChange={(e) => setDeletePassword(e.target.value)}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '16px' }}>
                <label className="form-label" style={{ fontSize: '0.8rem' }}>Type &quot;DELETE&quot; to confirm</label>
                <input
                  type="text"
                  className="form-input"
                  data-testid="topbar-delete-confirm-input"
                  placeholder="DELETE"
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => setShowDeleteModal(false)}
                  className="btn btn-secondary btn-sm"
                  disabled={isDeleting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-danger btn-sm"
                  data-testid="topbar-delete-submit-btn"
                  disabled={isDeleting || deleteConfirmText.trim().toUpperCase() !== 'DELETE' || !deletePassword}
                >
                  {isDeleting ? 'Deleting...' : 'Permanently Delete Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </header>
  );
};
