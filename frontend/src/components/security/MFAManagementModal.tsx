import React, { useState, useEffect } from 'react';
import { mfaApi } from '../../api/client';
import { MFASetupResponse, MFAStatusResponse } from '../../types';

interface MFAManagementModalProps {
  isOpen?: boolean;
  onClose: () => void;
}

export const MFAManagementModal: React.FC<MFAManagementModalProps> = ({ isOpen = true, onClose }) => {
  const [status, setStatus] = useState<MFAStatusResponse | null>(null);
  const [setupData, setSetupData] = useState<MFASetupResponse | null>(null);
  const [verifyCode, setVerifyCode] = useState('');
  const [disableCode, setDisableCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [copiedSecret, setCopiedSecret] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadStatus();
    }
  }, [isOpen]);

  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await mfaApi.getStatus();
      setStatus(res);
    } catch (err: any) {
      setError(err.message || 'Failed to load MFA status');
    } finally {
      setLoading(false);
    }
  };

  const handleStartSetup = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await mfaApi.setup();
      setSetupData(res);
    } catch (err: any) {
      setError(err.message || 'Failed to initiate MFA setup');
    } finally {
      setLoading(false);
    }
  };

  const handleEnableMFA = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!verifyCode.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const res = await mfaApi.enable(verifyCode.trim());
      setSuccessMsg(res.message);
      setSetupData(null);
      setVerifyCode('');
      await loadStatus();
    } catch (err: any) {
      setError(err.message || 'Failed to verify TOTP code');
    } finally {
      setLoading(false);
    }
  };

  const handleDisableMFA = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!disableCode.trim()) return;
    try {
      setLoading(true);
      setError(null);
      const res = await mfaApi.disable(disableCode.trim());
      setSuccessMsg(res.message);
      setDisableCode('');
      await loadStatus();
    } catch (err: any) {
      setError(err.message || 'Failed to disable MFA');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSecret(true);
    setTimeout(() => setCopiedSecret(false), 2000);
  };

  const downloadBackupCodes = (codes: string[]) => {
    const text =
      `MediGen-AI Emergency Backup Recovery Codes\nGenerated: ${new Date().toISOString()}\n\n` +
      codes.map((c, i) => `${i + 1}. ${c}`).join('\n') +
      '\n\nKeep these single-use codes in a secure offline location.';
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'medigen-backup-recovery-codes.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        background: 'rgba(5, 10, 20, 0.85)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
      data-testid="mfa-modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '540px',
          padding: '28px',
          background: '#0d1527',
          borderRadius: '16px',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.7)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          position: 'relative',
          maxHeight: '90vh',
          overflowY: 'auto',
        }}
      >
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '20px',
            right: '20px',
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            fontSize: '1.2rem',
            cursor: 'pointer',
            padding: '4px',
            lineHeight: 1,
          }}
          aria-label="Close"
        >
          ✕
        </button>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '20px' }}>
          <div
            style={{
              width: '44px',
              height: '44px',
              borderRadius: '12px',
              background: 'rgba(2, 132, 199, 0.15)',
              border: '1px solid rgba(2, 132, 199, 0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1.4rem',
            }}
          >
            🛡️
          </div>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>
              Multi-Factor Authentication (MFA / 2FA)

            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '4px 0 0' }}>
              RFC 6238 compliant authenticator security with offline backup recovery
            </p>
          </div>
        </div>

        {error && (
          <div
            style={{
              padding: '10px 14px',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid #ef4444',
              borderRadius: '8px',
              color: '#fca5a5',
              fontSize: '0.8125rem',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div
            style={{
              padding: '10px 14px',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid #10b981',
              borderRadius: '8px',
              color: '#6ee7b7',
              fontSize: '0.8125rem',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <span>✅</span>
            <span>{successMsg}</span>
          </div>
        )}

        {/* Status Display */}
        {status && !setupData && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div
              style={{
                padding: '16px',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-color)',
                borderRadius: '10px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
                  Status
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                  <span
                    style={{
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      background: status.is_enabled ? '#10b981' : '#f59e0b',
                      display: 'inline-block',
                    }}
                  />
                  <strong style={{ fontSize: '0.95rem', color: status.is_enabled ? '#34d399' : '#fbbf24' }}>
                    {status.is_enabled ? 'Enabled' : 'Not configured'}
                  </strong>
                </div>
              </div>

              {status.is_enabled && (
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>
                    Authenticator
                  </span>
                  <div style={{ fontSize: '0.85rem', color: '#38bdf8', fontWeight: 600, marginTop: '4px' }}>
                    Configured ({status.backup_codes_remaining} backup codes)
                  </div>
                </div>
              )}
            </div>

            {!status.is_enabled ? (
              <div style={{ textAlign: 'center', padding: '12px 0' }}>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '18px', lineHeight: 1.5 }}>
                  Add an extra layer of security to your clinical account using an authenticator app (Google Authenticator, Authy, Microsoft Authenticator, or 1Password).
                </p>
                <button
                  onClick={handleStartSetup}
                  disabled={loading}
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '12px', fontSize: '0.9rem', fontWeight: 600 }}
                  data-testid="btn-start-mfa-setup"
                >
                  🔑 {loading ? 'Initializing...' : 'Set Up Two-Factor Authentication'}
                </button>
              </div>
            ) : (
              <div style={{ padding: '16px', background: 'rgba(239, 68, 68, 0.06)', border: '1px solid rgba(239, 68, 68, 0.25)', borderRadius: '10px' }}>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#f87171', margin: '0 0 6px' }}>
                  Disable Two-Factor Authentication
                </h4>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                  Enter your current 6-digit authenticator code or emergency backup recovery code to deactivate MFA.
                </p>
                <form onSubmit={handleDisableMFA} style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    placeholder="6-digit TOTP or backup code"
                    value={disableCode}
                    onChange={(e) => setDisableCode(e.target.value)}
                    className="form-input"
                    style={{ flex: 1, fontSize: '0.85rem' }}
                  />
                  <button
                    type="submit"
                    disabled={loading || !disableCode.trim()}
                    className="btn btn-danger"
                    style={{ fontSize: '0.85rem', padding: '8px 16px' }}
                  >
                    Disable MFA
                  </button>
                </form>
              </div>
            )}
          </div>
        )}

        {/* Setup Flow */}
        {setupData && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div style={{ padding: '14px', background: 'rgba(2, 132, 199, 0.08)', border: '1px solid rgba(2, 132, 199, 0.25)', borderRadius: '10px' }}>
              <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#38bdf8', marginBottom: '8px' }}>
                1. Add Account to Authenticator App
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                Scan or enter this manual secret key in your authenticator app:
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <code
                  style={{
                    flex: 1,
                    padding: '8px 12px',
                    background: '#090d16',
                    border: '1px solid var(--border-color)',
                    borderRadius: '6px',
                    color: '#34d399',
                    fontFamily: 'monospace',
                    fontSize: '0.85rem',
                    letterSpacing: '0.05em',
                  }}
                >
                  {setupData.secret}
                </code>
                <button
                  type="button"
                  onClick={() => copyToClipboard(setupData.secret)}
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '0.75rem', padding: '8px 12px' }}
                >
                  {copiedSecret ? 'Copied! ✓' : 'Copy'}
                </button>
              </div>
            </div>

            {setupData.backup_codes && setupData.backup_codes.length > 0 && (
              <div style={{ padding: '14px', background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.25)', borderRadius: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#fbbf24', margin: 0 }}>
                    2. Emergency Backup Recovery Codes
                  </h3>
                  <button
                    type="button"
                    onClick={() => downloadBackupCodes(setupData.backup_codes)}
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: '0.7rem', padding: '4px 8px' }}
                  >
                    💾 Download
                  </button>
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  Save these single-use codes offline in case you lose access to your authenticator device:
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', background: '#090d16', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                  {setupData.backup_codes.map((code, idx) => (
                    <code key={idx} style={{ fontSize: '0.75rem', color: '#f8fafc', fontFamily: 'monospace' }}>
                      {idx + 1}. {code}
                    </code>
                  ))}
                </div>
              </div>
            )}

            {/* Verification Form */}
            <form onSubmit={handleEnableMFA} style={{ padding: '14px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-color)', borderRadius: '10px' }}>
              <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: '#ffffff', marginBottom: '8px' }}>
                3. Verify Authenticator Code
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                Enter the 6-digit code currently generated by your authenticator app to confirm setup:
              </p>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  maxLength={6}
                  placeholder="e.g. 123456"
                  value={verifyCode}
                  onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, ''))}
                  className="form-input"
                  style={{ flex: 1, fontSize: '1rem', letterSpacing: '0.2em', textAlign: 'center', fontWeight: 700 }}
                  required
                />
                <button
                  type="submit"
                  disabled={loading || verifyCode.trim().length !== 6}
                  className="btn btn-primary"
                  style={{ padding: '8px 20px', fontWeight: 600 }}
                >
                  {loading ? 'Activating...' : 'Activate MFA'}
                </button>
              </div>
            </form>

            <div style={{ textAlign: 'right' }}>
              <button
                type="button"
                onClick={() => setSetupData(null)}
                className="btn btn-secondary btn-sm"
              >
                Cancel Setup
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
