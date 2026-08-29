import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { ClinicalNoteWorkspace } from '../components/notes/ClinicalNoteWorkspace';
import { notesApi } from '../api/client';

vi.mock('../api/client', () => ({
  notesApi: {
    list: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          note_id: 'NOT-20260829-A1B2C3D4',
          patient_id: 1,
          author_user_id: 1,
          title: 'SOAP Note — Jane Doe',
          note_type: 'soap',
          status: 'draft',
          content_json: {
            subjective: 'Patient reports mild chest discomfort.',
            objective: 'Vitals stable. Lungs clear.',
            assessment: 'Atypical chest pain.',
            plan: 'Follow up in 2 weeks.',
          },
          raw_text: 'SOAP CLINICAL NOTE\n\nSUBJECTIVE:\nPatient reports mild chest discomfort.\n\nOBJECTIVE:\nVitals stable.\n\nASSESSMENT:\nAtypical chest pain.\n\nPLAN:\nFollow up in 2 weeks.',
          is_ai_generated: true,
          requires_clinician_review: true,
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    create: vi.fn().mockResolvedValue({
      id: 2,
      note_id: 'NOT-20260829-NEW00001',
      patient_id: 1,
      title: 'CONSULTATION Clinical Note',
      note_type: 'consultation',
      status: 'draft',
      raw_text: 'CLINICAL NOTE (CONSULTATION)',
      is_ai_generated: false,
      requires_clinician_review: true,
      created_at: '2026-08-29T10:05:00Z',
      updated_at: '2026-08-29T10:05:00Z',
    }),
    update: vi.fn().mockResolvedValue({
      id: 1,
      note_id: 'NOT-20260829-A1B2C3D4',
      patient_id: 1,
      title: 'SOAP Note — Jane Doe (Edited)',
      note_type: 'soap',
      status: 'draft',
      raw_text: 'SOAP CLINICAL NOTE (Updated draft)',
      is_ai_generated: true,
      requires_clinician_review: true,
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:10:00Z',
    }),
    signoff: vi.fn().mockResolvedValue({
      id: 1,
      note_id: 'NOT-20260829-A1B2C3D4',
      patient_id: 1,
      title: 'SOAP Note — Jane Doe',
      note_type: 'soap',
      status: 'finalized',
      raw_text: 'SOAP CLINICAL NOTE\n\n[PHYSICIAN SIGNOFF REMARKS]',
      is_ai_generated: true,
      requires_clinician_review: false,
      signed_by_user_id: 1,
      signed_at: '2026-08-29T10:15:00Z',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:15:00Z',
    }),
    enqueueSynthesis: vi.fn().mockResolvedValue({ task_id: 'TASK-NOT-1' }),
  },
}));

describe('Clinical Note Workspace & AI Scribe', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders clinical note list and detail editor', async () => {
    render(<ClinicalNoteWorkspace patientId="PAT-001" onTriggerSynthesis={vi.fn()} />);

    const titles = await screen.findAllByText(/SOAP Note — Jane Doe/i);
    expect(titles.length).toBeGreaterThan(0);

    const soapElements = await screen.findAllByText('SOAP');
    expect(soapElements.length).toBeGreaterThan(0);

    const disclaimer = await screen.findByText(/AI Clinical Scribe Draft/i);
    expect(disclaimer).toBeInTheDocument();

  });

  it('submits physician review signoff to finalize clinical note', async () => {
    render(<ClinicalNoteWorkspace patientId="PAT-001" onTriggerSynthesis={vi.fn()} />);

    await screen.findAllByText(/SOAP Note — Jane Doe/i);

    const signoffBtn = screen.getByText('✍️ Sign Off & Finalize Note');
    fireEvent.click(signoffBtn);

    const successAlert = await screen.findByText(/Clinical note finalized and signed/i);
    expect(successAlert).toBeInTheDocument();
  });
});
