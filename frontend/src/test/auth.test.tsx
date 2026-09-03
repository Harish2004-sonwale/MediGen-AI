import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { AuthProvider } from '../context/AuthContext';
import { LoginPage } from '../pages/LoginPage';
import { authApi } from '../api/client';

// Mock API client
vi.mock('../api/client', () => ({
  authApi: {
    login: vi.fn().mockResolvedValue({
      access_token: 'fake-jwt-token-12345',
      token_type: 'bearer',
      user: {
        id: 1,
        name: 'Dr. Gregory House',
        email: 'doctor@hospital.org',
        role: 'doctor',
        is_active: true,
        created_at: '2026-08-29T00:00:00Z',
        updated_at: '2026-08-29T00:00:00Z',
      },
    }),
    register: vi.fn().mockResolvedValue({
      id: 2,
      name: 'Dr. James Wilson',
      email: 'wilson@hospital.org',
      role: 'doctor',
      is_active: true,
    }),
    deleteAccount: vi.fn().mockResolvedValue({ message: 'Your account has been deleted successfully.' }),
    getMe: vi.fn().mockRejectedValue(new Error('No session')),
  },
  tenantApi: {
    listFacilities: vi.fn().mockResolvedValue([]),
    listOrganizations: vi.fn().mockResolvedValue([]),
  },
  getStoredToken: vi.fn().mockReturnValue(null),
  setStoredToken: vi.fn(),
  clearStoredToken: vi.fn(),
  getActiveFacilityId: vi.fn().mockReturnValue(null),
  setActiveFacilityId: vi.fn(),
}));

describe('Authentication & Secure Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login form with clean empty inputs and security controls', () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    expect(screen.getByText(/MediGen/i)).toBeInTheDocument();
    const emailInput = screen.getByTestId('login-email-input') as HTMLInputElement;
    const passwordInput = screen.getByTestId('login-password-input') as HTMLInputElement;
    expect(emailInput.value).toBe('');
    expect(passwordInput.value).toBe('');
    expect(screen.getByTestId('login-submit-btn')).toHaveTextContent('Sign In');
    // Ensure no quick demo login buttons exist
    expect(screen.queryByText(/Quick Demo Login/i)).not.toBeInTheDocument();
  });

  it('toggles password visibility when show/hide button is clicked', () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    const passwordInput = screen.getByTestId('login-password-input') as HTMLInputElement;
    const toggleBtn = screen.getByTestId('toggle-password-visibility');
    expect(passwordInput.type).toBe('password');
    expect(toggleBtn).toHaveTextContent('Show Password');

    fireEvent.click(toggleBtn);
    expect(passwordInput.type).toBe('text');
    expect(toggleBtn).toHaveTextContent('Hide Password');

    fireEvent.click(toggleBtn);
    expect(passwordInput.type).toBe('password');
  });

  it('submits login and invokes authentication API with entered credentials', async () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    const emailInput = screen.getByTestId('login-email-input');
    const passwordInput = screen.getByTestId('login-password-input');
    const submitBtn = screen.getByTestId('login-submit-btn');

    fireEvent.change(emailInput, { target: { value: 'doctor@hospital.org' } });
    fireEvent.change(passwordInput, { target: { value: 'ValidPassword123!' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalledWith('doctor@hospital.org', 'ValidPassword123!');
    });
  });

  it('displays error notification when authentication fails', async () => {
    vi.mocked(authApi.login).mockRejectedValueOnce(
      new Error('User not found or invalid email/password.')
    );

    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    const emailInput = screen.getByTestId('login-email-input');
    const passwordInput = screen.getByTestId('login-password-input');
    const submitBtn = screen.getByTestId('login-submit-btn');

    fireEvent.change(emailInput, { target: { value: 'wrong@hospital.org' } });
    fireEvent.change(passwordInput, { target: { value: 'BadPassword123!' } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByTestId('login-error-alert')).toBeInTheDocument();
      expect(screen.getByText(/User not found or invalid email\/password\./i)).toBeInTheDocument();
    });
  });
});
