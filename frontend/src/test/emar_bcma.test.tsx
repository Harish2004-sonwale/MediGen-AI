import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { EMARClosedLoopWorkspace } from '../components/emar/EMARClosedLoopWorkspace';
import * as apiClient from '../api/client';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof apiClient>('../api/client');
  return {
    ...actual,
    emarApi: {
      getSchedule: vi.fn().mockResolvedValue({
        total: 2,
        records: [
          {
            id: 1,
            mar_id: 'MAR-2026-0001',
            patient_id: 1,
            facility_id: 'FAC-METRO-MAIN',
            medication_name: 'Insulin Regular (Humulin R) 100 units/mL',
            medication_code: 'RXNORM-5856',
            prescribed_dose: '10 units',
            prescribed_route: 'subcutaneous',
            prescribed_frequency: 'TID',
            scheduled_time: '2026-09-02T12:00:00Z',
            status: 'scheduled',
            is_high_alert: true,
            requires_dual_witness: true,
            verification_passed: false,
            created_at: '2026-09-02T08:00:00Z',
            updated_at: '2026-09-02T08:00:00Z',
          },
          {
            id: 2,
            mar_id: 'MAR-2026-0002',
            patient_id: 1,
            facility_id: 'FAC-METRO-MAIN',
            medication_name: 'Amlodipine Besylate 5mg',
            medication_code: 'RXNORM-17767',
            prescribed_dose: '5mg',
            prescribed_route: 'oral',
            prescribed_frequency: 'daily',
            scheduled_time: '2026-09-02T09:00:00Z',
            actual_admin_time: '2026-09-02T09:05:00Z',
            status: 'administered',
            administered_dose: '5mg',
            administered_route: 'oral',
            site_of_administration: 'Oral Swallowed with Water',
            is_high_alert: false,
            requires_dual_witness: false,
            verification_passed: true,
            created_at: '2026-09-02T08:00:00Z',
            updated_at: '2026-09-02T09:05:00Z',
          },
        ],
      }),
      verify5Rights: vi.fn().mockResolvedValue({
        verification_status: 'pass',
        overall_passed: true,
        patient_verification: {
          passed: true,
          expected: 'PAT-00101',
          scanned: 'PAT-00101',
        },
        medication_verification: {
          passed: true,
          expected: 'Insulin Regular (Humulin R) 100 units/mL',
          scanned: 'Insulin Regular (Humulin R) 100 units/mL',
        },
        dose_verification: {
          passed: true,
          expected: '10 units',
          scanned: '10 units',
        },
        route_verification: {
          passed: true,
          expected: 'subcutaneous',
          scanned: 'subcutaneous',
        },
        time_verification: {
          passed: true,
          expected: '2026-09-02T12:00:00Z',
          scanned: '2026-09-02T12:02:00Z',
        },
        is_high_alert: true,
        requires_dual_signoff: true,
        discrepancy_warnings: [],
        verification_token: 'BCMA-LOG-2026-998811',
        timestamp: '2026-09-02T12:02:00Z',
      }),
      administerDose: vi.fn().mockResolvedValue({
        id: 1,
        mar_id: 'MAR-2026-0001',
        patient_id: 1,
        facility_id: 'FAC-METRO-MAIN',
        medication_name: 'Insulin Regular (Humulin R) 100 units/mL',
        medication_code: 'RXNORM-5856',
        prescribed_dose: '10 units',
        prescribed_route: 'subcutaneous',
        prescribed_frequency: 'TID',
        scheduled_time: '2026-09-02T12:00:00Z',
        actual_admin_time: '2026-09-02T12:05:00Z',
        status: 'administered',
        administered_dose: '10 units',
        administered_route: 'subcutaneous',
        is_high_alert: true,
        requires_dual_witness: true,
        dual_witness_user_id: 2,
        verification_passed: true,
        created_at: '2026-09-02T08:00:00Z',
        updated_at: '2026-09-02T12:05:00Z',
      }),
      holdOrRefuseDose: vi.fn().mockResolvedValue({
        id: 1,
        mar_id: 'MAR-2026-0001',
        patient_id: 1,
        facility_id: 'FAC-METRO-MAIN',
        medication_name: 'Insulin Regular (Humulin R) 100 units/mL',
        medication_code: 'RXNORM-5856',
        prescribed_dose: '10 units',
        prescribed_route: 'subcutaneous',
        prescribed_frequency: 'TID',
        scheduled_time: '2026-09-02T12:00:00Z',
        status: 'held',
        variance_reason: 'Held for blood glucose 68 mg/dL',
        is_high_alert: true,
        requires_dual_witness: true,
        verification_passed: false,
        created_at: '2026-09-02T08:00:00Z',
        updated_at: '2026-09-02T12:00:00Z',
      }),
      dualSignoff: vi.fn().mockResolvedValue({
        id: 1,
        mar_id: 'MAR-2026-0001',
        patient_id: 1,
        facility_id: 'FAC-METRO-MAIN',
        medication_name: 'Insulin Regular (Humulin R) 100 units/mL',
        medication_code: 'RXNORM-5856',
        prescribed_dose: '10 units',
        prescribed_route: 'subcutaneous',
        prescribed_frequency: 'TID',
        scheduled_time: '2026-09-02T12:00:00Z',
        status: 'scheduled',
        is_high_alert: true,
        requires_dual_witness: true,
        dual_witness_user_id: 2,
        dual_witness_timestamp: '2026-09-02T12:01:00Z',
        verification_passed: false,
        created_at: '2026-09-02T08:00:00Z',
        updated_at: '2026-09-02T12:01:00Z',
      }),
      listBarcodes: vi.fn().mockResolvedValue({
        total: 2,
        items: [
          {
            id: 1,
            barcode: 'NDC-00002-8215-01',
            medication_name: 'Insulin Regular (Humulin R) 100 units/mL',
            rxnorm_code: 'RXNORM-5856',
            standard_dose: '10 units',
            dosage_form: 'injection',
            route: 'subcutaneous',
            is_high_alert: true,
            high_alert_category: 'insulin',
            is_active: true,
            created_at: '2026-09-02T00:00:00Z',
          },
          {
            id: 2,
            barcode: 'NDC-00069-0266-01',
            medication_name: 'Amlodipine Besylate 5mg',
            rxnorm_code: 'RXNORM-17767',
            standard_dose: '5mg',
            dosage_form: 'tablet',
            route: 'oral',
            is_high_alert: false,
            is_active: true,
            created_at: '2026-09-02T00:00:00Z',
          },
        ],
      }),
      scheduleDoses: vi.fn().mockResolvedValue([]),
    },
  };
});

vi.mock('../context/PatientContext', () => ({
  usePatient: () => ({
    selectedPatient: {
      id: 1,
      patient_id: 'PAT-00101',
      first_name: 'Victor',
      last_name: 'Stone',
      date_of_birth: '1985-04-12',
      gender: 'Male',
      is_active: true,
      created_at: '2026-08-30T00:00:00Z',
    },
    patients: [],
    selectPatient: vi.fn(),
    selectPatientById: vi.fn(),
    refreshPatients: vi.fn(),
    isLoading: false,
    error: null,
  }),
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      name: 'Nurse Jackie, RN',
      email: 'nurse@hospital.org',
      role: 'healthcare_staff',
      is_active: true,
      created_at: '2026-08-30T00:00:00Z',
      updated_at: '2026-08-30T00:00:00Z',
    },
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    token: 'mock-token',
  }),
}));

describe('EMARClosedLoopWorkspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders eMAR timeline with high-alert insulin and scheduled doses', async () => {
    render(<EMARClosedLoopWorkspace />);

    expect(
      screen.getByText(/Closed-Loop eMAR & Barcode Medication Administration/i)
    ).toBeInTheDocument();

    await waitFor(() => {
      const insulinItems = screen.getAllByText(/Insulin Regular/i);
      expect(insulinItems.length).toBeGreaterThanOrEqual(1);
      const highAlertBadges = screen.getAllByText(/HIGH-ALERT/i);
      expect(highAlertBadges.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('executes BCMA 5-Rights Bedside Verification successfully', async () => {
    render(<EMARClosedLoopWorkspace />);

    const bcmaTab = screen.getByRole('button', { name: /Bedside BCMA 5-Rights Scanner/i });
    fireEvent.click(bcmaTab);

    await waitFor(() => {
      expect(screen.getByText(/Optical BCMA Scanner/i)).toBeInTheDocument();
    });

    const insulinPreset = screen.getByRole('button', { name: /Humulin R Insulin/i });
    fireEvent.click(insulinPreset);

    const verifyBtn = screen.getByRole('button', { name: /Verify 5-Rights Bedside/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(screen.getByText(/RIGHT PATIENT/i)).toBeInTheDocument();
      expect(screen.getByText(/RIGHT MEDICATION/i)).toBeInTheDocument();
      expect(screen.getByText(/RIGHT DOSE/i)).toBeInTheDocument();
      expect(screen.getByText(/RIGHT ROUTE/i)).toBeInTheDocument();
      expect(screen.getByText(/RIGHT TIME/i)).toBeInTheDocument();
    });
  });

  it('switches to Pharmacy Barcode Catalog and inspects barcodes', async () => {
    render(<EMARClosedLoopWorkspace />);

    const catalogTab = screen.getByRole('button', { name: /Pharmacy Barcode Catalog/i });
    fireEvent.click(catalogTab);

    await waitFor(() => {
      expect(screen.getByText(/NDC-00002-8215-01/i)).toBeInTheDocument();
      expect(screen.getByText(/NDC-00069-0266-01/i)).toBeInTheDocument();
    });
  });
});
