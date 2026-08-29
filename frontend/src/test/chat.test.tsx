import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { ClinicalChat } from '../components/chat/ClinicalChat';
import { chatApi } from '../api/client';

vi.mock('../api/client', () => ({
  chatApi: {
    createSession: vi.fn().mockResolvedValue({
      session_id: 'SES-TEST-001',
      patient_id: 'PAT-001',
      title: 'Clinical Consultation',
      is_active: true,
      message_count: 0,
      created_at: '2026-08-29T00:00:00Z',
      updated_at: '2026-08-29T00:00:00Z',
    }),
    streamMessage: vi.fn().mockImplementation(async (sessionId, message, handlers) => {
      handlers.onStart?.({ session_id: sessionId, message_id: 'asst-1' });
      handlers.onDelta?.('Patient has no known ');
      handlers.onDelta?.('drug interactions.');
      handlers.onCitation?.({
        document_id: 'DOC-1',
        title: 'Discharge Summary',
        page_number: 1,
      });
      handlers.onDone?.({
        message_id: 'asst-1',
        completed: true,
        insufficient_information: false,
        retrieved_chunks: 1,
      });
    }),
  },
  getStoredToken: vi.fn().mockReturnValue('mock-token'),
  setStoredToken: vi.fn(),
  clearStoredToken: vi.fn(),
}));

describe('Clinical AI Copilot (SSE Streaming Chat)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders chat copilot with starter clinical prompts', () => {
    render(<ClinicalChat patientId="PAT-001" />);

    expect(screen.getByText(/Clinical AI Copilot/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Ask a clinical question/i)).toBeInTheDocument();
    expect(screen.getByText(/Summarize active medications/i)).toBeInTheDocument();
  });

  it('sends message turn and accumulates SSE streaming tokens and citation badges', async () => {
    render(<ClinicalChat patientId="PAT-001" />);

    const input = screen.getByPlaceholderText(/Ask a clinical question/i);
    fireEvent.change(input, { target: { value: 'Are there any interactions?' } });

    const sendBtn = screen.getByText('Send');
    fireEvent.click(sendBtn);

    const userMessage = await screen.findByText('Are there any interactions?');
    expect(userMessage).toBeInTheDocument();

    const assistantAnswer = await screen.findByText('Patient has no known drug interactions.');
    expect(assistantAnswer).toBeInTheDocument();

    const citationBadge = await screen.findByText(/Discharge Summary/i);
    expect(citationBadge).toBeInTheDocument();
  });
});
