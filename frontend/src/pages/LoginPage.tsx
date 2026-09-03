// ==============================================================================
// MediGen AI - Secure Login & Authentication Portal
// ==============================================================================

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';
import { PatientRegistrationModal } from '../components/auth/PatientRegistrationModal';

export const LoginPage: React.FC = () => {
  const { login, register, isLoading } = useAuth();
  const [isRegisterMode, setIsRegisterMode] = useState<boolean>(false);
  const [isPatientModalOpen, setIsPatientModalOpen] = useState<boolean>(false);
  const [name, setName] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const [role, setRole] = useState<UserRole>('doctor');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (isRegisterMode) {
        if (!name.trim()) {
          setError('Please provide your full name.');
          return;
        }
        await register(name.trim(), email.trim(), password, role);
      } else {
        await login(email.trim(), password);
      }
    } catch (err: any) {
      setError(err.message || 'User not found or invalid email/password.');
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'radial-gradient(circle at 50% 30%, rgba(2, 132, 199, 0.15) 0%, #0b0f19 80%)',
        padding: '24px',
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '460px',
          padding: '32px',
          boxShadow: 'var(--shadow-lg)',
          borderRadius: '12px',
        }}
      >
        {/* Brand Banner */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="var(--brand-primary)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
              <path d="M12 5v14" />
              <path d="M5 12h14" />
            </svg>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 800, color: '#ffffff', margin: 0 }}>
              MediGen <span style={{ color: 'var(--brand-primary)' }}>AI</span>
            </h1>
          </div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: 0 }}>
            Hospital Management & Clinical AI Platform
          </p>
        </div>

        {/* Status Error Alert */}
        {error && (
          <div
            data-testid="login-error-alert"
            style={{
              padding: '12px 14px',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid var(--danger-border)',
              borderRadius: 'var(--radius-sm)',
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

        <form onSubmit={handleSubmit} data-testid="login-form">
          {isRegisterMode && (
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input
                type="text"
                className="form-input"
                placeholder="Dr. Neha Patil"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              type="email"
              className="form-input"
              data-testid="login-email-input"
              placeholder="user@hospital.org"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label className="form-label" style={{ margin: 0 }}>Password</label>
              <button
                type="button"
                data-testid="toggle-password-visibility"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  padding: 0,
                  textDecoration: 'underline',
                }}
              >
                {showPassword ? 'Hide Password' : 'Show Password'}
              </button>
            </div>
            <input
              type={showPassword ? 'text' : 'password'}
              className="form-input"
              data-testid="login-password-input"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {isRegisterMode && (
            <div className="form-group">
              <label className="form-label">Account Role</label>
              <select
                className="form-input"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
              >
                <option value="doctor">Doctor / Clinician</option>
                <option value="admin">Hospital Administrator</option>
                <option value="healthcare_staff">Healthcare Staff</option>
                <option value="patient">Patient</option>
              </select>
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            data-testid="login-submit-btn"
            style={{ width: '100%', marginTop: '16px', padding: '10px' }}
            disabled={isLoading}
          >
            {isLoading ? 'Signing In...' : isRegisterMode ? 'Create Clinician / Admin Account' : 'Sign In'}
          </button>
        </form>

        {/* Patient Registration Trigger */}
        <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid rgba(255,255,255,0.08)', textAlign: 'center' }}>
          <p style={{ fontSize: '0.8125rem', color: '#94a3b8', margin: '0 0 8px' }}>
            Are you a new patient visiting our hospital?
          </p>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            style={{ width: '100%', color: '#38bdf8', borderColor: 'rgba(56,189,248,0.3)', padding: '8px' }}
            onClick={() => setIsPatientModalOpen(true)}
          >
            ➕ Register as New Patient
          </button>
        </div>

        {/* Staff Switch */}
        <div style={{ marginTop: '12px', textAlign: 'center' }}>
          <button
            type="button"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-secondary)',
              fontSize: '0.75rem',
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
            onClick={() => {
              setIsRegisterMode(!isRegisterMode);
              setError(null);
            }}
          >
            {isRegisterMode
              ? 'Already have an account? Sign In'
              : 'Register clinical staff / doctor account'}
          </button>
        </div>
      </div>

      {/* Patient Registration Onboarding Modal */}
      <PatientRegistrationModal
        isOpen={isPatientModalOpen}
        onClose={() => setIsPatientModalOpen(false)}
      />
    </div>
  );
};
