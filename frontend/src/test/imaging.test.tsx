import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { ImagingRadiologyWorkspace } from '../components/imaging/ImagingRadiologyWorkspace';
import { imagingApi, patientsApi, fhirApi } from '../api/client';

vi.mock('../api/client', () => ({
  patientsApi: {
    list: vi.fn().mockResolvedValue([
      {
        id: 1,
        patient_id: 'PAT-IMG-001',
        first_name: 'Eleanor',
        last_name: 'Vance',
        gender: 'female',
        date_of_birth: '1975-04-12',
        is_active: true,
      },
    ]),
  },

  imagingApi: {
    listStudies: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          study_id: 'STU-IMG-999',
          patient_id: 1,
          patient_identifier: 'PAT-IMG-001',
          modality: 'CT',
          body_site: 'HEAD_BRAIN',
          study_description: 'Non-contrast Brain CT for sudden onset severe headache',
          accession_number: 'ACC-CT-1001',
          study_datetime: '2026-08-30T10:00:00Z',
          performing_department: 'Radiology & Diagnostic Imaging',
          referring_provider: 'Dr. John Watson',
          status: 'IN_PROGRESS',
          source: 'DIRECT_PACS',
          provenance_hash: 'abc123hash999',
          assets_count: 1,
          findings_count: 1,
          reports_count: 1,
          has_critical_findings: true,
          created_at: '2026-08-30T10:00:00Z',
          updated_at: '2026-08-30T10:00:00Z',
        },
      ],
    }),
    getStudy: vi.fn().mockResolvedValue({
      id: 1,
      study_id: 'STU-IMG-999',
      patient_id: 1,
      modality: 'CT',
      body_site: 'HEAD_BRAIN',
      study_description: 'Non-contrast Brain CT for sudden onset severe headache',
      accession_number: 'ACC-CT-1001',
      study_datetime: '2026-08-30T10:00:00Z',
      performing_department: 'Radiology & Diagnostic Imaging',
      status: 'IN_PROGRESS',
      provenance_hash: 'abc123hash999',
    }),
    listAssets: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          asset_id: 'AST-001',
          study_id: 1,
          series_description: 'Axial Brain 5mm',
          sop_instance_uid: '1.2.840.113619.2.55.3.1000',
          modality: 'CT',
          body_site: 'HEAD_BRAIN',
          mime_type: 'application/dicom',
          file_size_bytes: 524288,
          storage_path: 'imaging/assets/test.dcm',
          provenance_hash: 'ast-hash-1',
          created_at: '2026-08-30T10:00:00Z',
        },
      ],
    }),
    listFindings: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          finding_id: 'FND-IMG-001',
          study_id: 1,
          patient_id: 1,
          finding_type: 'POSSIBLE_HEMORRHAGE',
          anatomical_location: 'Right basal ganglia / temporal lobe',
          laterality: 'RIGHT',
          severity: 'CRITICAL',
          confidence_score: 0.94,
          is_critical: true,
          finding_nature: 'AI_GENERATED_FINDING',
          description: 'Hyperdense attenuation noted in right subarachnoid space suggestive of acute subarachnoid hemorrhage.',
          recommendation: 'Urgent neurosurgical consultation and non-contrast CT angiography.',
          bounding_box_json: { x: 120, y: 150, width: 80, height: 90 },
          clinician_review_status: 'pending_review',
          provenance_hash: 'fnd-hash-001',
          created_at: '2026-08-30T10:00:00Z',
        },
      ],
    }),
    createStudy: vi.fn().mockResolvedValue({
      id: 2,
      study_id: 'STU-IMG-1000',
      patient_id: 1,
      modality: 'XRAY',
      body_site: 'CHEST',
      study_description: 'CXR PA/Lateral for cough',
      accession_number: 'ACC-XRAY-2002',
      status: 'ORDERED',
      provenance_hash: 'hash-new-study',
      created_at: '2026-08-30T10:00:00Z',
      updated_at: '2026-08-30T10:00:00Z',
    }),
    analyzeStudy: vi.fn().mockResolvedValue({
      study_id: 'STU-IMG-999',
      status: 'COMPLETED',
      findings_count: 1,
      critical_findings_count: 1,
      findings: [
        {
          id: 1,
          finding_id: 'FND-IMG-001',
          study_id: 1,
          patient_id: 1,
          finding_type: 'POSSIBLE_HEMORRHAGE',
          anatomical_location: 'Right basal ganglia / temporal lobe',
          laterality: 'RIGHT',
          severity: 'CRITICAL',
          confidence_score: 0.94,
          is_critical: true,
          finding_nature: 'AI_GENERATED_FINDING',
          description: 'Hyperdense attenuation noted in right subarachnoid space suggestive of acute subarachnoid hemorrhage.',
          recommendation: 'Urgent neurosurgical consultation and non-contrast CT angiography.',
          bounding_box_json: { x: 120, y: 150, width: 80, height: 90 },
          clinician_review_status: 'pending_review',
          provenance_hash: 'fnd-hash-001',
          created_at: '2026-08-30T10:00:00Z',
        },
      ],
      draft_report: {
        id: 1,
        report_id: 'REP-IMG-001',
        study_id: 1,
        status: 'AI_ASSISTED',
        clinical_indication: 'Sudden onset severe headache',
        technique: 'Axial Non-Contrast Head CT',
        comparison_studies: 'No prior CT scans available.',
        findings: 'Acute hyperdensity noted in the right Sylvian fissure and basal cisterns.',
        impression: 'Findings consistent with acute subarachnoid hemorrhage.',
        recommendations: 'Immediate neurosurgery review and CTA.',
        is_critical: true,
        provenance_hash: 'rep-hash-001',
        created_at: '2026-08-30T10:00:00Z',
        updated_at: '2026-08-30T10:00:00Z',
      },
      multimodal_context: {
        patient_id: 'PAT-IMG-001',
        patient_name: 'Eleanor Vance',
        age_years: 49,
        gender: 'female',
        clinical_indication: 'Sudden severe headache',
        modality: 'CT',
        body_site: 'HEAD_BRAIN',
        active_diagnoses: ['Essential Hypertension'],
        active_medications: ['Amlodipine 5mg'],
        allergies: ['Penicillin'],
        recent_vitals: [{ heart_rate: 88, blood_pressure: '142/90' }],
        active_alerts: [],
        relevant_lab_results: [],
        previous_studies: [],
      },
      provenance_hash: 'analysis-hash-999',
      evaluated_at: '2026-08-30T10:00:00Z',
    }),
    reviewFinding: vi.fn().mockResolvedValue({
      id: 1,
      finding_id: 'FND-IMG-001',
      study_id: 1,
      patient_id: 1,
      finding_type: 'POSSIBLE_HEMORRHAGE',
      anatomical_location: 'Right basal ganglia / temporal lobe',
      laterality: 'RIGHT',
      severity: 'CRITICAL',
      confidence_score: 0.94,
      is_critical: true,
      finding_nature: 'CLINICIAN_CONFIRMED_FINDING',
      description: 'Hyperdense attenuation noted in right subarachnoid space suggestive of acute subarachnoid hemorrhage.',
      recommendation: 'Urgent neurosurgical consultation and non-contrast CT angiography.',
      clinician_review_status: 'confirmed',
      review_notes: 'Verified hyperdensity on slice 14.',
      provenance_hash: 'fnd-hash-001-confirmed',
      created_at: '2026-08-30T10:00:00Z',
    }),
    updateReport: vi.fn().mockResolvedValue({
      id: 1,
      report_id: 'REP-IMG-001',
      status: 'DRAFT',
      clinical_indication: 'Sudden onset severe headache',
      technique: 'Axial Non-Contrast Head CT',
      comparison_studies: 'None',
      findings: 'Findings updated by doctor',
      impression: 'Impression updated',
      recommendations: 'Neurosurgery consult',
      is_critical: true,
      provenance_hash: 'rep-hash-002',
      created_at: '2026-08-30T10:00:00Z',
      updated_at: '2026-08-30T10:00:00Z',
    }),
    submitReportReview: vi.fn().mockResolvedValue({
      id: 1,
      report_id: 'REP-IMG-001',
      status: 'RADIOLOGIST_REVIEW',
      clinical_indication: 'Sudden onset severe headache',
      technique: 'Axial Non-Contrast Head CT',
      comparison_studies: 'None',
      findings: 'Findings updated',
      impression: 'Impression updated',
      recommendations: 'Neurosurgery consult',
      is_critical: true,
      provenance_hash: 'rep-hash-003',
      created_at: '2026-08-30T10:00:00Z',
      updated_at: '2026-08-30T10:00:00Z',
    }),
    finalizeReport: vi.fn().mockResolvedValue({
      id: 1,
      report_id: 'REP-IMG-001',
      status: 'FINALIZED',
      clinical_indication: 'Sudden onset severe headache',
      technique: 'Axial Non-Contrast Head CT',
      comparison_studies: 'None',
      findings: 'Findings updated',
      impression: 'Impression confirmed',
      recommendations: 'Neurosurgery consult',
      is_critical: true,
      signed_at: '2026-08-30T10:05:00Z',
      provenance_hash: 'rep-hash-final',
      created_at: '2026-08-30T10:00:00Z',
      updated_at: '2026-08-30T10:05:00Z',
    }),
    amendReport: vi.fn().mockResolvedValue({
      id: 2,
      report_id: 'REP-IMG-001-A1',
      status: 'AMENDED',
      amendment_reason: 'Follow-up comparison clarified',
      clinical_indication: 'Sudden onset severe headache',
      technique: 'Axial Non-Contrast Head CT',
      comparison_studies: 'None',
      findings: 'Findings amended',
      impression: 'Impression amended',
      recommendations: 'Neurosurgery consult',
      is_critical: true,
      provenance_hash: 'rep-hash-amended',
      created_at: '2026-08-30T10:10:00Z',
      updated_at: '2026-08-30T10:10:00Z',
    }),
    getTimeline: vi.fn().mockResolvedValue({
      patient_id: 'PAT-IMG-001',
      total_studies: 1,
      items: [
        {
          event_id: 'EVT-001',
          study_id: 'STU-IMG-999',
          study_datetime: '2026-08-30T10:00:00Z',
          modality: 'CT',
          body_site: 'HEAD_BRAIN',
          description: 'Non-contrast Brain CT',
          status: 'COMPLETED',
          accession_number: 'ACC-CT-1001',
          findings_count: 1,
          has_critical: true,
          report_id: 'REP-IMG-001',
          report_status: 'FINALIZED',
        },
      ],
    }),
  },
  fhirApi: {
    exportImagingStudy: vi.fn().mockResolvedValue({
      resourceType: 'ImagingStudy',
      id: 'STU-IMG-999',
      status: 'available',
      modality: [{ system: 'http://dicom.nema.org/resources/ontology/DCM', code: 'CT' }],
    }),
  },
}));

describe('ImagingRadiologyWorkspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders workspace banner with assistive safety disclaimer', async () => {
    render(<ImagingRadiologyWorkspace selectedPatientId="PAT-IMG-001" />);

    expect(screen.getByText(/Medical Imaging AI & Multimodal Radiology/i)).toBeInTheDocument();
    expect(screen.getByText(/Assistive AI Support/i)).toBeInTheDocument();
    expect(
      screen.getByText(/All AI-generated observations and draft reports remain preliminary/i)
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(imagingApi.listStudies).toHaveBeenCalled();
    });
  });

  it('displays critical finding alert banner when critical anomalies are detected', async () => {
    render(<ImagingRadiologyWorkspace selectedPatientId="PAT-IMG-001" />);

    await waitFor(() => {
      expect(screen.getByTestId('critical-finding-banner')).toBeInTheDocument();
      expect(
        screen.getByText(/POTENTIALLY CRITICAL AI-ASSISTED FINDING — REQUIRES IMMEDIATE CLINICIAN REVIEW/i)
      ).toBeInTheDocument();
    });
  });

  it('triggers multimodal AI interpretation and switches to analysis view', async () => {
    render(<ImagingRadiologyWorkspace selectedPatientId="PAT-IMG-001" />);

    await waitFor(() => {
      expect(screen.getByTestId('run-analysis-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('run-analysis-btn'));

    await waitFor(() => {
      expect(imagingApi.analyzeStudy).toHaveBeenCalledWith('STU-IMG-999');
    });

    expect(await screen.findByText(/Diagnostic Image Canvas/i)).toBeInTheDocument();
    expect(screen.getByTestId('imaging-canvas')).toBeInTheDocument();
  });

  it('allows clinician to review and confirm structured findings', async () => {
    render(<ImagingRadiologyWorkspace selectedPatientId="PAT-IMG-001" />);

    // Switch to analysis tab
    fireEvent.click(screen.getByTestId('tab-analysis'));

    await waitFor(() => {
      expect(screen.getByTestId('finding-card-FND-IMG-001')).toBeInTheDocument();
    });

    const reviewBtn = screen.getByTestId('review-finding-btn-FND-IMG-001');
    fireEvent.click(reviewBtn);

    expect(screen.getByText(/Clinician Finding Review Sign-off/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /Record Review/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(imagingApi.reviewFinding).toHaveBeenCalledWith('FND-IMG-001', 'confirmed', '');
    });
  });

  it('allows doctor to review, sign, and finalize radiology report', async () => {
    render(<ImagingRadiologyWorkspace selectedPatientId="PAT-IMG-001" />);

    await waitFor(() => {
      expect(screen.getByTestId('run-analysis-btn')).toBeInTheDocument();
    });

    // Run analysis first to populate activeReport
    fireEvent.click(screen.getByTestId('run-analysis-btn'));

    await waitFor(() => {
      expect(imagingApi.analyzeStudy).toHaveBeenCalled();
    });

    // Switch to report tab
    fireEvent.click(screen.getByTestId('tab-report'));

    await waitFor(() => {
      expect(screen.getByText(/Diagnostic Radiology Report/i)).toBeInTheDocument();
    });

    // Click Finalize
    const finalizeBtn = screen.getByTestId('finalize-report-btn');
    fireEvent.click(finalizeBtn);

    expect(screen.getByText(/Attest & Electronically Sign Radiology Report/i)).toBeInTheDocument();

    const confirmFinalizeBtn = screen.getByTestId('confirm-finalize-btn');
    fireEvent.click(confirmFinalizeBtn);

    await waitFor(() => {
      expect(imagingApi.finalizeReport).toHaveBeenCalled();
    });
  });

});
