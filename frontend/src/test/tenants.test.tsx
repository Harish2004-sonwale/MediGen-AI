import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { HealthSystemTenantWorkspace } from '../components/tenants/HealthSystemTenantWorkspace';
import * as apiClient from '../api/client';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof apiClient>('../api/client');
  return {
    ...actual,
    tenantApi: {
      listOrganizations: vi.fn().mockResolvedValue([
        {
          id: 1,
          org_id: 'ORG-001',
          name: 'Metropolitan Regional Health System',
          org_type: 'HOSPITAL_NETWORK',
          is_active: true,
          created_at: '2026-08-30T00:00:00Z',
          updated_at: '2026-08-30T00:00:00Z',
        },
      ]),
      createOrganization: vi.fn(),
      listFacilities: vi.fn().mockResolvedValue([
        {
          id: 1,
          facility_id: 'FAC-001',
          org_id: 'ORG-001',
          name: 'Metropolitan General Hospital',
          facility_code: 'MGH-MAIN-01',
          address_json: { city: 'Boston', state: 'MA' },
          is_active: true,
          created_at: '2026-08-30T00:00:00Z',
          updated_at: '2026-08-30T00:00:00Z',
        },
      ]),
      createFacility: vi.fn(),
      listDepartments: vi.fn().mockResolvedValue([
        {
          id: 1,
          department_id: 'DEP-001',
          facility_id: 'FAC-001',
          name: 'Cardiology Intensive Care Unit',
          dept_code: 'CICU-01',
          is_active: true,
          created_at: '2026-08-30T00:00:00Z',
          updated_at: '2026-08-30T00:00:00Z',
        },
      ]),
      createDepartment: vi.fn(),
      getEHRConfig: vi.fn().mockResolvedValue({
        id: 1,
        config_id: 'EHR-001',
        facility_id: 'FAC-001',
        ehr_vendor: 'EPIC',
        fhir_base_url: 'https://epic.mgh.org/api/FHIR/R4',
        client_id: 'mgh-epic-client-001',
        is_enabled: true,
        created_at: '2026-08-30T00:00:00Z',
        updated_at: '2026-08-30T00:00:00Z',
      }),
      configureEHR: vi.fn(),
    },
  };
});

describe('HealthSystemTenantWorkspace', () => {
  it('renders health system organization and facilities', async () => {
    render(<HealthSystemTenantWorkspace />);
    expect(
      screen.getByText(/Multi-Tenant Health Systems, Facilities & EHR Integrations/i)
    ).toBeInTheDocument();

    await waitFor(() => {
      const facTitles = screen.getAllByText(/Metropolitan General Hospital/i);
      expect(facTitles.length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Cardiology Intensive Care Unit/i)).toBeInTheDocument();
      expect(screen.getByTestId('ehr-vendor')).toHaveTextContent('EPIC');
    });
  });
});
