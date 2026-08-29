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
        email: 'doctor@example.com',
        role: 'doctor',
        is_active: true,
        created_at: '2026-08-29T00:00:00Z',
        updated_at: '2026-08-29T00:00:00Z',
      },
    }),
    register: vi.fn().mockResolvedValue({
      id: 2,
      name: 'Dr. James Wilson',
      email: 'wilson@example.com',
      role: 'doctor',
      is_active: true,
    }),
    getMe: vi.fn().mockRejectedValue(new Error('No session')),
  },
  getStoredToken: vi.fn().mockReturnValue(null),
  setStoredToken: vi.fn(),
  clearStoredToken: vi.fn(),
}));

describe('Authentication & Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login form with clinical branding', () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    expect(screen.getByText(/MediGen/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/user@hospital.org/i)).toBeInTheDocument();
    expect(screen.getByText(/Sign In to Clinical Workspace/i)).toBeInTheDocument();
  });

  it('switches demo credentials on quick role click', () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    const adminBtn = screen.getByText(/🛡️ Admin/i);
    fireEvent.click(adminBtn);

    const emailInput = screen.getByPlaceholderText(/user@hospital.org/i) as HTMLInputElement;
    expect(emailInput.value).toBe('admin@example.com');
  });

  it('submits login and invokes login API', async () => {
    render(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    const submitBtn = screen.getByText(/Sign In to Clinical Workspace/i);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalledWith('doctor@example.com', 'DoctorPassword123!');
    });
  });
});
