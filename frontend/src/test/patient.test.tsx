import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { PatientDirectory } from '../components/patients/PatientDirectory';
import { PatientProvider } from '../context/PatientContext';
import { patientsApi } from '../api/client';
import { AuthProvider } from '../context/AuthContext';

vi.mock('../api/client', () => ({
  patientsApi: {
    list: vi.fn().mockResolvedValue([
      {
        id: 1,
        patient_id: 'PAT-001',
        first_name: 'John',
        last_name: 'Doe',
        date_of_birth: '1980-05-15',
        gender: 'Male',
        allergies: 'Penicillin',
        is_active: true,
        created_at: '2026-08-29T00:00:00Z',
      },
      {
        id: 2,
        patient_id: 'PAT-002',
        first_name: 'Jane',
        last_name: 'Smith',
        date_of_birth: '1992-11-20',
        gender: 'Female',
        allergies: 'Aspirin',
        is_active: true,
        created_at: '2026-08-29T00:00:00Z',
      },
    ]),
    get: vi.fn(),
  },
  authApi: {
    getMe: vi.fn().mockResolvedValue({
      id: 1,
      name: 'Dr. House',
      email: 'house@example.com',
      role: 'doctor',
      is_active: true,
    }),
  },
  getStoredToken: vi.fn().mockReturnValue('mock-token'),
  setStoredToken: vi.fn(),
  clearStoredToken: vi.fn(),
}));

describe('Patient Directory & Context', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders patient directory list', async () => {
    render(
      <AuthProvider>
        <PatientProvider>
          <PatientDirectory />
        </PatientProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/John Doe/i)).toBeInTheDocument();
      expect(screen.getByText(/Jane Smith/i)).toBeInTheDocument();
      expect(screen.getByText(/PAT-001/i)).toBeInTheDocument();
    });
  });

  it('filters patient directory on search query', async () => {
    render(
      <AuthProvider>
        <PatientProvider>
          <PatientDirectory />
        </PatientProvider>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/John Doe/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search by name or ID/i);
    fireEvent.change(searchInput, { target: { value: 'Jane' } });

    expect(screen.getByText(/Jane Smith/i)).toBeInTheDocument();
    expect(screen.queryByText(/John Doe/i)).not.toBeInTheDocument();
  });
});
