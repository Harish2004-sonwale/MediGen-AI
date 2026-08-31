import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LiveCollaborationWorkspace } from '../components/collaboration/LiveCollaborationWorkspace';
import * as apiClient from '../api/client';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof apiClient>('../api/client');
  return {
    ...actual,
    telehealthApi: {
      getIceServers: vi.fn(),
      getWebSocketStats: vi.fn(),
      broadcastTelemetry: vi.fn(),
    },
  };
});

describe('LiveCollaborationWorkspace', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(apiClient.telehealthApi.getIceServers).mockResolvedValue({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    });

    vi.mocked(apiClient.telehealthApi.getWebSocketStats).mockResolvedValue({
      active_telemetry_patients: 1,
      active_collaboration_rooms: 1,
      active_telehealth_sessions: 1,
      total_connected_clients: 2,
    });
  });

  it('renders live collaboration room with ECG telemetry and presence', async () => {
    render(<LiveCollaborationWorkspace selectedPatientId="PAT-001" />);
    expect(
      screen.getByText(/Real-Time Vital Telemetry & Multi-Clinician Collaboration Room/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Live ECG Telemetry \(Lead II\)/i)).toBeInTheDocument();
    expect(screen.getByText(/WebRTC Telehealth Room/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Dr. Harish Sonwale/i)).toBeInTheDocument();
      expect(screen.getByText(/WebSocket Connected \(WSS\)/i)).toBeInTheDocument();
    });
  });

  it('toggles microphone and camera mute states', async () => {
    render(<LiveCollaborationWorkspace selectedPatientId="PAT-001" />);

    const micBtn = screen.getByText(/Mic On/i);
    fireEvent.click(micBtn);
    expect(screen.getByText(/Mic Muted/i)).toBeInTheDocument();

    const camBtn = screen.getByText(/Cam On/i);
    fireEvent.click(camBtn);
    expect(screen.getByText(/Cam Off/i)).toBeInTheDocument();
  });
});
