// ==============================================================================
// MediGen AI - Phase 9.0.24 Frontend Governance & Facility Context Tests
// ==============================================================================

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Header } from '../components/layout/Header';
import { AuthProvider, useAuth } from '../context/AuthContext';
import * as client from '../api/client';
import { ClinicalFacility, User } from '../types';

const mockFacilities: ClinicalFacility[] = [
  {
    id: 1,
    facility_id: 'FAC-001',
    org_id: 'ORG-001',
    name: 'General Medical Center',
    facility_code: 'GMC-MAIN',
    address_json: { city: 'Metropolis' },
    is_active: true,
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
  },
  {
    id: 2,
    facility_id: 'FAC-002',
    org_id: 'ORG-001',
    name: 'St. Jude Specialty Hospital',
    facility_code: 'SJSH-EAST',
    address_json: { city: 'Gotham' },
    is_active: true,
    created_at: '2026-01-01',
    updated_at: '2026-01-01',
  },
];

const mockUser: User = {
  id: 101,
  name: 'Dr. Sarah Connor',
  email: 'sarah.connor@medigen.ai',
  role: 'doctor',
  is_active: true,
  default_facility_id: 'FAC-001',
  created_at: '2026-01-01',
  updated_at: '2026-01-01',
};

const FacilityTestHarness: React.FC = () => {
  const { activeFacilityId, activeFacility, setActiveFacility } = useAuth();
  return (
    <div>
      <Header onOpenSafetyModal={() => {}} onOpenTasksModal={() => {}} activeTaskCount={0} />
      <div data-testid="current-active-fac-id">{activeFacilityId}</div>
      <div data-testid="current-active-fac-name">{activeFacility?.name}</div>
      <button
        data-testid="switch-to-fac-2-btn"
        onClick={() => setActiveFacility('FAC-002')}
      >
        Switch to FAC-002
      </button>
    </div>
  );
};

describe('Phase 9.0.24 — Active Facility Context Ribbon & Header Selector (P2-3)', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('1. Header renders active facility context with multiple facilities', async () => {
    client.setStoredToken('mock-jwt-token');
    vi.spyOn(client.authApi, 'getMe').mockResolvedValue(mockUser);
    vi.spyOn(client.tenantApi, 'listFacilities').mockResolvedValue(mockFacilities);

    render(
      <AuthProvider>
        <FacilityTestHarness />
      </AuthProvider>
    );

    // Wait for session and facilities to load
    await waitFor(() => {
      expect(screen.getByText(/Active Facility/i)).toBeDefined();
      expect(screen.getByTestId('header-facility-selector')).toBeDefined();
    });

    const selector = screen.getByTestId('header-facility-selector') as HTMLSelectElement;
    expect(selector.value).toBe('FAC-001');
    expect(screen.getByText(/General Medical Center \(GMC-MAIN\)/i)).toBeDefined();
    expect(screen.getByText(/St. Jude Specialty Hospital \(SJSH-EAST\)/i)).toBeDefined();
  });

  it('2. Changing active facility updates context in UI and localStorage', async () => {
    client.setStoredToken('mock-jwt-token');
    vi.spyOn(client.authApi, 'getMe').mockResolvedValue(mockUser);
    vi.spyOn(client.tenantApi, 'listFacilities').mockResolvedValue(mockFacilities);

    render(
      <AuthProvider>
        <FacilityTestHarness />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('header-facility-selector')).toBeDefined();
    });

    const selector = screen.getByTestId('header-facility-selector') as HTMLSelectElement;
    fireEvent.change(selector, { target: { value: 'FAC-002' } });

    await waitFor(() => {
      expect(screen.getByTestId('current-active-fac-id').textContent).toBe('FAC-002');
      expect(screen.getByTestId('current-active-fac-name').textContent).toBe('St. Jude Specialty Hospital');
      expect(client.getActiveFacilityId()).toBe('FAC-002');
    });
  });

  it('3. Header handles facility API failure gracefully without crashing', async () => {
    client.setStoredToken('mock-jwt-token');
    vi.spyOn(client.authApi, 'getMe').mockResolvedValue(mockUser);
    vi.spyOn(client.tenantApi, 'listFacilities').mockRejectedValue(new Error('Network error loading facilities'));

    render(
      <AuthProvider>
        <FacilityTestHarness />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Dr. Sarah Connor/i)).toBeDefined();
      expect(screen.getByText(/Active Facility/i)).toBeDefined();
    });

    // When API fails, renders single badge fallback
    expect(screen.getByTestId('active-facility-badge')).toBeDefined();
  });

  it('4. Single-facility user renders fixed context badge instead of dropdown', async () => {
    const singleFacility = [mockFacilities[0]];
    client.setStoredToken('mock-jwt-token');
    vi.spyOn(client.authApi, 'getMe').mockResolvedValue(mockUser);
    vi.spyOn(client.tenantApi, 'listFacilities').mockResolvedValue(singleFacility);

    render(
      <AuthProvider>
        <FacilityTestHarness />
      </AuthProvider>
    );

    await waitFor(() => {
      const badge = screen.getByTestId('active-facility-badge');
      expect(badge).toBeDefined();
      expect(badge.textContent).toContain('General Medical Center');
      expect(badge.textContent).toContain('GMC-MAIN');
      expect(screen.queryByTestId('header-facility-selector')).toBeNull();
    });
  });

  it('5. API request includes X-Facility-ID header from active context', async () => {
    client.setStoredToken('mock-token-abc');
    client.setActiveFacilityId('FAC-001');

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'success' }),
    });
    global.fetch = mockFetch;

    await client.apiRequest('/patients');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const callArgs = mockFetch.mock.calls[0];
    const headers = callArgs[1].headers as Headers;
    expect(headers.get('X-Facility-ID')).toBe('FAC-001');
    expect(headers.get('Authorization')).toBe('Bearer mock-token-abc');
  });

  it('6. Switching facility changes subsequent API request header', async () => {
    client.setStoredToken('mock-token-abc');
    client.setActiveFacilityId('FAC-001');

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'ok' }),
    });
    global.fetch = mockFetch;

    // Request 1 with FAC-001
    await client.apiRequest('/care-plans');
    let callHeaders = mockFetch.mock.calls[0][1].headers as Headers;
    expect(callHeaders.get('X-Facility-ID')).toBe('FAC-001');

    // Switch to FAC-002
    client.setActiveFacilityId('FAC-002');

    // Request 2 with FAC-002
    await client.apiRequest('/care-plans');
    callHeaders = mockFetch.mock.calls[1][1].headers as Headers;
    expect(callHeaders.get('X-Facility-ID')).toBe('FAC-002');
  });
});
