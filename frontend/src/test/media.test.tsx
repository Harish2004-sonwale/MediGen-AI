import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { MediaDiagnosticsHub } from '../components/media/MediaDiagnosticsHub';
import { mediaApi } from '../api/client';

vi.mock('../api/client', () => ({
  mediaApi: {
    list: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          media_id: 'MED-20260829-A1B2C3D4',
          patient_id: 1,
          title: 'Chest X-Ray PA View',
          modality: 'xray_chest',
          body_site: 'chest',
          original_filename: 'xray_pa.jpg',
          file_size_bytes: 204800,
          mime_type: 'image/jpeg',
          status: 'analyzed',
          confidence_score: 0.94,
          findings_summary: 'Clear lung fields bilaterally without consolidation.',
          structured_findings: {
            modality: 'xray_chest',
            confidence_score: 0.94,
            primary_observation: 'Clear lung fields bilaterally without consolidation.',
            findings: [
              {
                observation: 'Normal cardiac silhouette.',
                anatomical_region: 'Heart',
                confidence: 0.96,
                is_abnormal: false,
              },
            ],
            differential_notes: ['Correlate with clinical examination.'],
            disclaimer: 'AI decision support observation only.',
          },
          requires_clinician_review: true,
          clinician_confirmed: false,
          created_at: '2026-08-29T10:00:00Z',
          analyzed_at: '2026-08-29T10:02:00Z',
        },
      ],
    }),
    upload: vi.fn(),
    enqueueAnalysis: vi.fn().mockResolvedValue({ task_id: 'TASK-MED-1' }),
    review: vi.fn().mockResolvedValue({
      id: 1,
      media_id: 'MED-20260829-A1B2C3D4',
      patient_id: 1,
      title: 'Chest X-Ray PA View',
      modality: 'xray_chest',
      body_site: 'chest',
      original_filename: 'xray_pa.jpg',
      file_size_bytes: 204800,
      mime_type: 'image/jpeg',
      status: 'reviewed',
      confidence_score: 0.94,
      findings_summary: 'Clear lung fields bilaterally without consolidation.',
      requires_clinician_review: true,
      clinician_confirmed: true,
      clinician_notes: 'Confirmed clear lungs.',
      reviewed_at: '2026-08-29T10:15:00Z',
    }),
    getFileUrl: vi.fn().mockReturnValue('/api/v1/media/MED-20260829-A1B2C3D4/file'),
  },
}));

describe('Multi-Modal Medical Diagnostics Hub', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders diagnostic imaging study list and AI findings', async () => {
    render(<MediaDiagnosticsHub patientId="PAT-001" onTriggerAnalysis={vi.fn()} />);

    const titles = await screen.findAllByText('Chest X-Ray PA View');
    expect(titles.length).toBeGreaterThan(0);

    const confidenceScore = await screen.findByText('94%');
    expect(confidenceScore).toBeInTheDocument();

    const observation = await screen.findByText(/Clear lung fields bilaterally/i);
    expect(observation).toBeInTheDocument();

    const disclaimer = await screen.findByText(/AI decision support observation only/i);
    expect(disclaimer).toBeInTheDocument();
  });

  it('submits physician review signoff', async () => {
    render(<MediaDiagnosticsHub patientId="PAT-001" onTriggerAnalysis={vi.fn()} />);

    const titles = await screen.findAllByText('Chest X-Ray PA View');
    expect(titles.length).toBeGreaterThan(0);

    const signoffBtn = screen.getByText('Sign Off & Confirm Study');
    fireEvent.click(signoffBtn);

    const successAlert = await screen.findByText(/Clinician review and verification successfully saved/i);
    expect(successAlert).toBeInTheDocument();
  });

});
