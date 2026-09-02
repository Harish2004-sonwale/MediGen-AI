import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DICOMPACSViewerWorkspace } from '../components/pacs/DICOMPACSViewerWorkspace';
import * as apiClient from '../api/client';

const mockStudies = {
  total: 1,
  studies: [
    {
      id: 1,
      study_instance_uid: '1.2.840.113619.2.55.3.1001',
      study_id: 'STU-2026-001',
      patient_id: 1,
      patient_identifier: 'PAT-001',
      facility_id: 'FAC-METRO-MAIN',
      accession_number: 'ACC-2026-001',
      study_description: 'High-Resolution Chest CT with Contrast',
      modality: 'CT',
      body_site: 'CHEST',
      study_datetime: '2026-09-02T10:00:00Z',
      referring_physician: 'Dr. Gregory House, MD',
      performing_institution: 'MetroHealth Diagnostic Imaging',
      number_of_series: 1,
      number_of_instances: 1,
      series_list: [
        {
          id: 1,
          series_instance_uid: '1.2.840.113619.2.55.3.1001.1',
          study_id: 1,
          series_number: 1,
          series_description: 'CT Chest Axial Reformat',
          modality: 'CT',
          body_part_examined: 'CHEST',
          patient_position: 'HFS',
          slice_thickness_mm: 1.25,
          pixel_spacing_row_mm: 0.68,
          pixel_spacing_col_mm: 0.68,
          window_center_default: 40,
          window_width_default: 400,
          rescale_intercept: 0,
          rescale_slope: 1,
          number_of_instances: 1,
          instances: [
            {
              id: 1,
              sop_instance_uid: '1.2.840.113619.2.55.3.1001.1.1',
              series_id: 1,
              sop_class_uid: '1.2.840.10008.5.1.4.1.1.2',
              instance_number: 1,
              rows: 512,
              columns: 512,
              bits_allocated: 16,
              bits_stored: 12,
              high_bit: 11,
              pixel_representation: 0,
              photometric_interpretation: 'MONOCHROME2',
              storage_path: '/pacs/storage/test.dcm',
              ai_findings: [
                {
                  id: 1,
                  finding_id: 'FND-2026-001',
                  instance_id: 1,
                  lesion_type: 'PNEUMONIA_CONSOLIDATION',
                  anatomical_location: 'Right Lower Lobe',
                  confidence_score: 0.94,
                  severity: 'MODERATE',
                  geometry_type: 'BOUNDING_BOX',
                  coordinates_json: { x: 160, y: 210, w: 85, h: 75 },
                  model_name: 'MediGen-VisionTransformer-v2.1',
                  model_version: '2.1.0',
                  clinician_review_status: 'pending_review',
                  created_at: '2026-09-02T10:00:00Z',
                },
              ],
              created_at: '2026-09-02T10:00:00Z',
            },
          ],
          created_at: '2026-09-02T10:00:00Z',
        },
      ],
      created_at: '2026-09-02T10:00:00Z',
      updated_at: '2026-09-02T10:00:00Z',
    },
  ],
};

const mockEcgSessions = {
  total: 1,
  sessions: [
    {
      id: 1,
      session_id: 'WAV-2026-001',
      patient_id: 1,
      patient_identifier: 'PAT-001',
      facility_id: 'FAC-METRO-MAIN',
      device_id: 'ICU-BED-04',
      lead_configuration: '12_LEAD',
      sample_rate_hz: 250,
      amplitude_unit: 'mV',
      start_time: '2026-09-02T10:00:00Z',
      duration_seconds: 10,
      current_rhythm_state: 'stemi_elevation',
      heart_rate_bpm: 95,
      multi_lead_samples_json: {
        I: [0.1, 0.2, 0.3],
        II: [0.1, 0.2, 0.3],
        III: [0.1, 0.2, 0.3],
        aVR: [-0.1, -0.2, -0.3],
        aVL: [0.1, 0.2, 0.3],
        aVF: [0.1, 0.2, 0.3],
        V1: [0.1, 0.2, 0.3],
        V2: [0.2, 0.4, 0.6],
        V3: [0.3, 0.6, 0.9],
        V4: [0.2, 0.4, 0.6],
        V5: [0.1, 0.2, 0.3],
        V6: [0.1, 0.2, 0.3],
      },
      is_active_streaming: true,
      alerts: [
        {
          id: 1,
          alert_id: 'ALT-2026-001',
          session_id: 1,
          patient_id: 1,
          event_type: 'stemi_elevation',
          severity: 'critical',
          lead_involved: 'V3',
          heart_rate_bpm: 95,
          st_elevation_mm: 3.8,
          alert_description: 'Critical STEMI ST-Elevation detected on Lead V3',
          status: 'active',
          triggered_at: '2026-09-02T10:00:00Z',
          cooldown_until: '2026-09-02T10:05:00Z',
        },
      ],
      created_at: '2026-09-02T10:00:00Z',
    },
  ],
};

describe('DICOMPACSViewerWorkspace Component', () => {
  beforeEach(() => {
    vi.spyOn(apiClient.pacsApi, 'queryStudies').mockResolvedValue(mockStudies as any);
    vi.spyOn(apiClient.pacsApi, 'reviewFinding').mockResolvedValue({
      ...mockStudies.studies[0].series_list[0].instances[0].ai_findings[0],
      clinician_review_status: 'confirmed',
    } as any);
    vi.spyOn(apiClient.waveformsApi, 'getPatientSessions').mockResolvedValue(mockEcgSessions as any);
    vi.spyOn(apiClient.waveformsApi, 'listActiveAlerts').mockResolvedValue(mockEcgSessions.sessions[0].alerts as any);
    vi.spyOn(apiClient.waveformsApi, 'acknowledgeAlert').mockResolvedValue({
      ...mockEcgSessions.sessions[0].alerts[0],
      status: 'acknowledged',
      clinician_action_taken: 'Cath lab activated.',
    } as any);
  });

  it('renders DICOM PACS Viewer and displays study details with AI findings', async () => {
    render(<DICOMPACSViewerWorkspace patientId="PAT-001" />);

    await waitFor(() => {
      expect(screen.getByText(/DICOM PACS Medical Vision & Real-Time Waveform Telemetry/i)).toBeInTheDocument();
      expect(screen.getByText(/High-Resolution Chest CT with Contrast/i)).toBeInTheDocument();
      expect(screen.getByText(/PNEUMONIA_CONSOLIDATION/i)).toBeInTheDocument();
    });
  });

  it('allows clinician to confirm AI lesion finding', async () => {
    render(<DICOMPACSViewerWorkspace patientId="PAT-001" />);

    await waitFor(() => {
      expect(screen.getByText('✓ Confirm Finding')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('✓ Confirm Finding'));

    await waitFor(() => {
      expect(apiClient.pacsApi.reviewFinding).toHaveBeenCalledWith('FND-2026-001', {
        status: 'confirmed',
        review_notes: 'Clinician confirmed this finding during interactive review.',
      });
    });
  });

  it('switches to 12-Lead ECG Monitor tab and acknowledges arrhythmia alert', async () => {
    render(<DICOMPACSViewerWorkspace patientId="PAT-001" />);

    await waitFor(() => {
      expect(screen.getByText('📈 12-Lead ECG Monitor')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('📈 12-Lead ECG Monitor'));

    await waitFor(() => {
      expect(screen.getByText(/Critical Arrhythmia Alert Triggered: stemi elevation/i)).toBeInTheDocument();
      expect(screen.getByText('Acknowledge Alarm')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Acknowledge Alarm'));

    await waitFor(() => {
      expect(screen.getByText('Acknowledge ICU Arrhythmia Alert')).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/Bedside physician notified/i);
    fireEvent.change(textarea, { target: { value: 'Cath lab activated. Patient prepared for emergent PCI.' } });

    fireEvent.click(screen.getByText('Confirm Acknowledgment'));

    await waitFor(() => {
      expect(apiClient.waveformsApi.acknowledgeAlert).toHaveBeenCalledWith('ALT-2026-001', {
        clinician_action_taken: 'Cath lab activated. Patient prepared for emergent PCI.',
        status: 'acknowledged',
      });
    });
  });
});
