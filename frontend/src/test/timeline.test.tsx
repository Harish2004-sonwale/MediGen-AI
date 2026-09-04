import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { TimelineView } from '../components/timeline/TimelineView';
import { timelineApi } from '../api/client';

vi.mock('../api/client', () => ({
  timelineApi: {
    getTimeline: vi.fn(),
    getSummary: vi.fn(),
  },
}));

describe('TimelineView Regression & Contract Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders correctly when backend returns TimelineListResponse envelope { total, patient_id, events } without events.map crash', async () => {
    const mockEnvelope = {
      total: 2,
      patient_id: 'PAT-20260903-E4EB',
      events: [
        {
          event_id: 'EVT-001',
          patient_id: 'PAT-20260903-E4EB',
          event_date: '2026-09-01T10:00:00Z',
          event_type: 'encounter',
          title: 'Initial Cardiology Consultation',
          description: 'Patient presented with mild chest tightness and stage 1 hypertension.',
        },
        {
          event_id: 'EVT-002',
          patient_id: 'PAT-20260903-E4EB',
          event_date: '2026-09-02T14:30:00Z',
          event_type: 'document',
          title: 'Echocardiogram Diagnostic Report',
          description: 'Normal ejection fraction 62%, no regional wall motion abnormalities.',
        },
      ],
    };

    (timelineApi.getTimeline as any).mockResolvedValue(mockEnvelope);
    (timelineApi.getSummary as any).mockResolvedValue({
      summary: 'Patient has a stable cardiovascular profile with documented normal echocardiogram.',
      citations: [],
      total_events_analyzed: 2,
    });

    render(<TimelineView patientId="PAT-20260903-E4EB" />);

    await waitFor(() => {
      expect(screen.getByText(/Initial Cardiology Consultation/i)).toBeInTheDocument();
      expect(screen.getByText(/Echocardiogram Diagnostic Report/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Patient presented with mild chest tightness/i)).toBeInTheDocument();
    expect(screen.getByText(/Normal ejection fraction 62%/i)).toBeInTheDocument();
  });

  it('renders clean empty state when patient has zero events', async () => {
    (timelineApi.getTimeline as any).mockResolvedValue({
      total: 0,
      patient_id: 'PAT-EMPTY-001',
      events: [],
    });
    (timelineApi.getSummary as any).mockResolvedValue(null);

    render(<TimelineView patientId="PAT-EMPTY-001" />);

    await waitFor(() => {
      expect(screen.getByText(/No clinical events recorded for this patient/i)).toBeInTheDocument();
    });
  });

  it('gracefully handles raw array responses for backwards compatibility', async () => {
    const mockArray = [
      {
        event_id: 'EVT-003',
        patient_id: 'PAT-ARRAY-001',
        event_date: '2026-09-03T09:00:00Z',
        event_type: 'appointment',
        title: 'Follow-up Follow-up Visit',
        description: 'Routine follow-up in Internal Medicine.',
      },
    ];

    (timelineApi.getTimeline as any).mockResolvedValue(mockArray);
    (timelineApi.getSummary as any).mockResolvedValue(null);

    render(<TimelineView patientId="PAT-ARRAY-001" />);

    await waitFor(() => {
      expect(screen.getByText(/Follow-up Follow-up Visit/i)).toBeInTheDocument();
    });
  });
});
