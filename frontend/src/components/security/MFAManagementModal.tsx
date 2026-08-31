import React, { useState, useEffect } from 'react';
import { mfaApi } from '../../api/client';
import { MFASetupResponse, MFAStatusResponse } from '../../types';

interface MFAManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MFAManagementModal: React.FC<MFAManagementModalProps> = ({ isOpen, onClose }) => {
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
    const text = `MediGen-AI Emergency Backup Recovery Codes\nGenerated: ${new Date().toISOString()}\n\n` +
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 max-w-xl w-full p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg font-bold"
        >
          ✕
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 bg-teal-50 dark:bg-teal-900/30 rounded-xl text-teal-600 dark:text-teal-400 font-bold text-xl">
            🛡️
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">Multi-Factor Authentication (MFA / TOTP)</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">RFC 6238 compliant authenticator security with offline backup recovery</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl text-sm text-red-600 dark:text-red-400 flex items-center gap-2">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mb-4 p-3 bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-800 rounded-xl text-sm text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
            <span>✅</span>
            <span>{successMsg}</span>
          </div>
        )}

        {/* Current MFA Status */}
        {status && !setupData && (
          <div className="space-y-6">
            <div className="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-xl border border-slate-200 dark:border-slate-700 flex items-center justify-between">
              <div>
                <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">Status</span>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`inline-block w-2.5 h-2.5 rounded-full ${status.is_enabled ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                  <span className="font-medium text-slate-900 dark:text-white">
                    {status.is_enabled ? 'Active & Enforced' : 'Not Configured'}
                  </span>
                </div>
              </div>
              {status.is_enabled && (
                <div className="text-right">
                  <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">Backup Codes</span>
                  <div className="font-semibold text-slate-900 dark:text-white mt-1">
                    {status.backup_codes_remaining} remaining
                  </div>
                </div>
              )}
            </div>

            {!status.is_enabled ? (
              <div className="text-center py-4">
                <p className="text-sm text-slate-600 dark:text-slate-300 mb-4">
                  Add an extra layer of security to your clinical account using Google Authenticator, Authy, or 1Password.
                </p>
                <button
                  onClick={handleStartSetup}
                  disabled={loading}
                  className="px-6 py-2.5 bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-xl shadow-sm transition inline-flex items-center gap-2"
                >
                  <span>🔑</span>
                  {loading ? 'Initializing...' : 'Set Up Two-Factor Authentication'}
                </button>
              </div>
            ) : (
              <form onSubmit={handleDisableMFA} className="p-4 border border-red-100 dark:border-red-900/40 bg-red-50/50 dark:bg-red-900/10 rounded-xl space-y-3">
                <h4 className="text-sm font-semibold text-red-900 dark:text-red-300">Disable Two-Factor Authentication</h4>
                <p className="text-xs text-red-700 dark:text-red-400">
                  Enter your current 6-digit authenticator code or emergency backup recovery code to disable MFA.
                </p>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="6-digit code or backup code"
                    value={disableCode}
                    onChange={(e) => setDisableCode(e.target.value)}
                    className="flex-1 px-3 py-2 text-sm bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 text-slate-900 dark:text-white"
                  />
                  <button
                    type="submit"
                    disabled={loading || !disableCode.trim()}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition"
                  >
                    Disable
                  </button>
                </div>
              </form>
            )}
          </div>
        )}

        {/* Setup Wizard */}
        {setupData && (
          <div className="space-y-6">
            <div className="space-y-2">
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">1. Authenticator Secret Key</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Enter the following base32 secret manually in your authenticator application:
              </p>
              <div className="flex items-center justify-between p-3 bg-slate-100 dark:bg-slate-900 rounded-lg font-mono text-sm tracking-wider text-slate-800 dark:text-slate-200">
                <span>{setupData.secret}</span>
                <button
                  type="button"
                  onClick={() => copyToClipboard(setupData.secret)}
                  className="p-1 text-slate-500 hover:text-teal-600 dark:hover:text-teal-400 text-xs font-semibold"
                  title="Copy secret"
                >
                  📋 Copy
                </button>
              </div>
              {copiedSecret && <span className="text-xs text-emerald-500">Secret copied to clipboard!</span>}
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-slate-900 dark:text-white">2. Emergency Backup Recovery Codes</h3>
                <button
                  type="button"
                  onClick={() => downloadBackupCodes(setupData.backup_codes)}
                  className="text-xs text-teal-600 dark:text-teal-400 hover:underline flex items-center gap-1"
                >
                  📥 Download All
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2 p-3 bg-slate-50 dark:bg-slate-900/60 rounded-lg border border-slate-200 dark:border-slate-700 font-mono text-xs text-slate-700 dark:text-slate-300">
                {setupData.backup_codes.map((code, idx) => (
                  <div key={idx} className="flex justify-between py-0.5 px-2 bg-white dark:bg-slate-800 rounded">
                    <span className="text-slate-400">#{idx + 1}</span>
                    <span className="font-bold">{code}</span>
                  </div>
                ))}
              </div>
            </div>

            <form onSubmit={handleEnableMFA} className="space-y-3 pt-2">
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">3. Confirm 6-Digit Code</h3>
              <div className="flex gap-2">
                <input
                  type="text"
                  maxLength={6}
                  placeholder="000000"
                  value={verifyCode}
                  onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, ''))}
                  className="flex-1 px-4 py-2.5 text-center font-mono text-lg tracking-widest bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900 dark:text-white"
                />
                <button
                  type="submit"
                  disabled={loading || verifyCode.length !== 6}
                  className="px-6 py-2.5 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-medium rounded-xl transition"
                >
                  Verify & Activate
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
