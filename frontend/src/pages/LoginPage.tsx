// ==============================================================================
// MediGen AI - Login & Role Switching Page
// ==============================================================================

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types';

export const LoginPage: React.FC = () => {
  const { login, register, isLoading } = useAuth();
  const [isRegisterMode, setIsRegisterMode] = useState<boolean>(false);
  const [name, setName] = useState<string>('');
  const [email, setEmail] = useState<string>('doctor@example.com');
  const [password, setPassword] = useState<string>('DoctorPassword123!');
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
      setError(err.message || 'Authentication failed. Please verify credentials.');
    }
  };

  const handleQuickRole = (r: UserRole, defaultEmail: string, defaultPass: string) => {
    setEmail(defaultEmail);
    setPassword(defaultPass);
    setRole(r);
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
          maxWidth: '440px',
          padding: '32px',
          boxShadow: 'var(--shadow-lg)',
        }}
      >
        {/* Brand Banner */}
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--brand-primary)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
              <path d="M12 5v14" />
              <path d="M5 12h14" />
            </svg>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff' }}>
              MediGen <span style={{ color: 'var(--brand-primary)' }}>AI</span>
            </h1>
          </div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)' }}>
            Clinical Decision Support & Intelligence Platform
          </p>
        </div>

        {/* Quick Demo Role Selector */}
        {!isRegisterMode && (
          <div style={{ marginBottom: '20px', padding: '10px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
              Quick Demo Login:
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px' }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.7rem' }}
                onClick={() => handleQuickRole('doctor', 'doctor@example.com', 'DoctorPassword123!')}
              >
                🩺 Doctor
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.7rem' }}
                onClick={() => handleQuickRole('admin', 'admin@example.com', 'AdminPassword123!')}
              >
                🛡️ Admin
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.7rem' }}
                onClick={() => handleQuickRole('patient', 'patient@example.com', 'PatientPassword123!')}
              >
                👤 Patient
              </button>
            </div>
          </div>
        )}

        {error && (
          <div style={{ padding: '10px 14px', background: 'rgba(239,68,68,0.15)', border: '1px solid var(--danger-border)', borderRadius: 'var(--radius-sm)', color: '#fca5a5', fontSize: '0.8125rem', marginBottom: '16px' }}>
            ⚠️ {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {isRegisterMode && (
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input
                type="text"
                className="form-input"
                placeholder="Dr. Alice Smith"
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
              placeholder="user@hospital.org"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {isRegisterMode && (
            <div className="form-group">
              <label className="form-label">Assigned Role</label>
              <select
                className="form-select"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
              >
                <option value="doctor">Doctor / Clinician</option>
                <option value="healthcare_staff">Healthcare Staff</option>
                <option value="patient">Patient</option>
                <option value="admin">System Administrator</option>
              </select>
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '8px', padding: '12px' }}
            disabled={isLoading}
          >
            {isLoading
              ? 'Authenticating...'
              : isRegisterMode
              ? 'Create Healthcare Account'
              : 'Sign In to Clinical Workspace'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '16px' }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            style={{ border: 'none', background: 'none', color: 'var(--brand-primary)', textDecoration: 'underline' }}
            onClick={() => {
              setIsRegisterMode(!isRegisterMode);
              setError(null);
            }}
          >
            {isRegisterMode
              ? 'Already have an account? Sign in'
              : "Don't have an account? Register new clinician profile"}
          </button>
        </div>
      </div>
    </div>
  );
};
