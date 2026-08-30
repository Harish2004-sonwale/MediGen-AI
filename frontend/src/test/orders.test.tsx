import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { OrdersWorkspace } from '../components/orders/OrdersWorkspace';
import { ordersApi, patientsApi } from '../api/client';

vi.mock('../api/client', () => ({
  patientsApi: {
    list: vi.fn().mockResolvedValue([
      {
        id: 1,
        patient_id: 'PAT-ORD-001',
        first_name: 'Arthur',
        last_name: 'Pendleton',
        gender: 'male',
        date_of_birth: '1965-05-20',
        is_active: true,
      },
    ]),
  },

  ordersApi: {
    listOrders: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          order_id: 'ORD-20260829-001',
          patient_id: 1,
          order_category: 'laboratory',
          order_type: 'complete_blood_count',
          priority: 'routine',
          status: 'placed',
          clinical_indication: 'Baseline inpatient evaluation',
          specimen_source: 'Venous blood',
          ai_safety_flags_json: [],
          is_ai_suggested: false,
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    listResults: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          result_id: 'RES-20260829-001',
          order_id: 1,
          patient_id: 1,
          test_name: 'Serum Potassium',
          test_code_loinc: '2823-3',
          status: 'final',
          abnormal_flag: 'panic_critical',
          findings_summary: 'Severe hyperkalemia detected on automated analyzer.',
          numeric_value: 6.8,
          unit_of_measure: 'mEq/L',
          reference_range_low: 3.5,
          reference_range_high: 5.0,
          resulted_at: '2026-08-29T10:30:00Z',
          created_at: '2026-08-29T10:30:00Z',
          updated_at: '2026-08-29T10:30:00Z',
        },
      ],
    }),
    placeOrder: vi.fn().mockResolvedValue({
      id: 2,
      order_id: 'ORD-20260829-002',
      patient_id: 1,
      order_category: 'laboratory',
      order_type: 'serum_potassium',
      priority: 'stat',
      status: 'placed',
      clinical_indication: 'Serial electrolyte check',
      specimen_source: 'Venous blood',
      ai_safety_flags_json: [],
      is_ai_suggested: false,
      created_at: '2026-08-29T10:15:00Z',
      updated_at: '2026-08-29T10:15:00Z',
    }),
    suggestBundle: vi.fn().mockResolvedValue({
      protocol_name: 'Chest Pain / Acute Coronary Syndrome Bundle',
      clinical_rationale: 'Targeted cardiovascular workup for suspected myocardial ischemia.',
      suggested_orders: [
        {
          order_category: 'laboratory',
          order_type: 'troponin_i_high_sensitivity',
          priority: 'stat',
          clinical_indication: 'Rule out acute myocardial infarction',
          specimen_source: 'Venous blood',
        },
      ],
      pre_order_safety_warnings: [],
    }),
    reviewResult: vi.fn().mockResolvedValue({
      id: 1,
      result_id: 'RES-20260829-001',
      reviewed_by_user_id: 1,
      reviewed_at: '2026-08-29T11:00:00Z',
    }),
  },
}));

describe('OrdersWorkspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders CPOE orders and displays active patient summary', async () => {
    render(<OrdersWorkspace />);

    await waitFor(() => {
      expect(screen.getAllByText(/Arthur/i).length).toBeGreaterThan(0);
      expect(screen.getByText('COMPLETE BLOOD COUNT')).toBeInTheDocument();
    });
  });



  it('navigates to Diagnostic Results tab and renders panic critical lab values', async () => {
    render(<OrdersWorkspace />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Diagnostic Results/i })).toBeInTheDocument();
    });

    const resultsTabBtn = screen.getByRole('button', { name: /Diagnostic Results/i });
    fireEvent.click(resultsTabBtn);

    await waitFor(() => {
      expect(screen.getByText('Serum Potassium')).toBeInTheDocument();
      expect(screen.getByText('Severe hyperkalemia detected on automated analyzer.')).toBeInTheDocument();
      expect(screen.getByText('Sign Off / Review')).toBeInTheDocument();
    });
  });

  it('opens AI Order Bundle modal and requests protocol recommendations', async () => {
    render(<OrdersWorkspace />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /AI Order Bundle/i })).toBeInTheDocument();
    });

    const aiBundleBtn = screen.getByRole('button', { name: /AI Order Bundle/i });
    fireEvent.click(aiBundleBtn);

    await waitFor(() => {
      expect(screen.getByText(/AI Order Set Protocol Bundle/i)).toBeInTheDocument();
      expect(screen.getByText(/Standard Clinical Protocol/i)).toBeInTheDocument();
    });
  });
});
