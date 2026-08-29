import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { SafetyPrescriberModal } from '../components/safety/SafetyPrescriberModal';
import { safetyApi } from '../api/client';

vi.mock('../api/client', () => ({
  safetyApi: {
    checkSafety: vi.fn(),
  },
}));

describe('Clinical Decision Support Safety Prescriber Modal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders safety prescriber modal when open', () => {
    render(
      <SafetyPrescriberModal
        patientId="PAT-2026-001"
        isOpen={true}
        onClose={() => {}}
      />
    );

    expect(screen.getByText(/Clinical Decision Support/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/e\.g\. Warfarin, Aspirin/i)).toBeInTheDocument();
  });

  it('submits safety check and renders critical conflict alert', async () => {
    vi.mocked(safetyApi.checkSafety).mockResolvedValueOnce({
      patient_id: 'PAT-2026-001',
      alerts: [
        {
          alert_id: 'ALT-101',
          patient_id: 'PAT-2026-001',
          alert_type: 'contraindication',
          severity: 'CRITICAL',
          title: 'Severe Bleeding Risk with Warfarin and Aspirin',
          explanation: 'Concurrent administration elevates major hemorrhage risk.',
          medications: ['Warfarin', 'Aspirin'],
          source_references: ['FDA Package Insert'],
          generated_at: '2026-08-29T10:00:00Z',
          provider: 'MockCDS',
          requires_clinician_review: true,
          citations: [],
        },
      ],
      checked_items: 2,
      safe_to_proceed: false,
      summary: '1 critical alert detected.',
      disclaimer: 'Decision-support alert only.',
      generated_at: '2026-08-29T10:00:00Z',
    });

    render(
      <SafetyPrescriberModal
        patientId="PAT-2026-001"
        isOpen={true}
        onClose={() => {}}
      />
    );

    const input = screen.getByPlaceholderText(/e\.g\. Warfarin, Aspirin/i);
    fireEvent.change(input, { target: { value: 'Warfarin, Aspirin' } });

    const submitBtn = screen.getByText(/Run Clinical Safety Check/i);
    fireEvent.click(submitBtn);

    const alertTitle = await screen.findByText('Severe Bleeding Risk with Warfarin and Aspirin');
    expect(alertTitle).toBeInTheDocument();

    const criticalBadge = await screen.findByText('CRITICAL');
    expect(criticalBadge).toBeInTheDocument();
  });
});
