import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { RegionalInteroperabilityWorkspace } from '../components/interop/RegionalInteroperabilityWorkspace';
import { empiApi, ccdaApi, pathwaysApi, patientsApi } from '../api/client';

vi.mock('../api/client', () => ({
  patientsApi: {
    list: vi.fn().mockResolvedValue([
      {
        patient_id: 'PAT-00101',
        first_name: 'Alexander',
        last_name: 'Hamilton',
        date_of_birth: '1980-01-11',
        gender: 'male',
        facility_id: 'FAC-METRO-MAIN',
      },
    ]),
  },
  empiApi: {
    findCandidateMatches: vi.fn().mockResolvedValue({
      query_patient_id: 'PAT-00101',
      total_candidates: 1,
      candidates: [
        {
          patient_id: 'PAT-00104',
          first_name: 'Alexandr',
          last_name: 'Hamilton',
          date_of_birth: '1980-01-11',
          gender: 'male',
          facility_id: 'FAC-METRO-WEST',
          match_score: 0.92,
          grade: 'exact',
          feature_breakdown: {
            name_score: 0.95,
            dob_score: 1.0,
            phone_score: 0.9,
          },
        },
      ],
    }),
    listReviews: vi.fn().mockResolvedValue([]),
    linkPatient: vi.fn().mockResolvedValue({
      enterprise_id: 'EUID-001',
      patient_id: 'PAT-00104',
    }),
    unlinkPatient: vi.fn().mockResolvedValue({ success: true, message: 'Unlinked' }),
    mergeIdentities: vi.fn().mockResolvedValue({
      merge_id: 'MRG-001',
      message: 'Merged successfully',
    }),
    resolveReview: vi.fn().mockResolvedValue({ success: true, message: 'Resolved' }),
  },
  ccdaApi: {
    exportDocument: vi.fn().mockResolvedValue({
      document_id: 'CCDA-001',
      patient_id: 'PAT-00101',
      document_type: 'continuity_of_care_document',
      title: 'Continuity of Care Document',
      created_at: '2026-09-01T10:00:00Z',
      sha256_hash: 'abc123hash',
      xml_content: '<ClinicalDocument>Sample C-CDA XML Content</ClinicalDocument>',
      section_count: 6,
    }),
    downloadRawXmlUrl: vi.fn().mockReturnValue('/api/v1/ccda/export/PAT-00101/xml'),
    importDocument: vi.fn().mockResolvedValue({
      document_id: 'CCDA-IMP-001',
      patient_id: 'PAT-00101',
      title: 'Imported Summary',
      problems_count: 2,
      allergies_count: 1,
      medications_count: 3,
      vitals_count: 4,
      sections: [],
    }),
    listDocuments: vi.fn().mockResolvedValue({
      total: 1,
      documents: [
        {
          id: 1,
          document_id: 'CCDA-001',
          patient_id: 'PAT-00101',
          direction: 'export',
          title: 'Continuity of Care Document',
          sha256_hash: 'abc123hash89012345678',
          created_at: '2026-09-01T10:00:00Z',
        },
      ],
    }),
  },
  pathwaysApi: {
    listPathways: vi.fn().mockResolvedValue({
      total: 1,
      pathways: [
        {
          pathway_id: 'PATH-001',
          code: 'SEPSIS_BUNDLE',
          name: 'Regional Sepsis Resuscitation & Bundle Protocol',
          target_duration_hours: 24,
          stages: [
            {
              stage_id: 'STG-001',
              sequence_order: 1,
              name: 'Emergency Screening & Initial Resuscitation',
              assigned_facility_id: 'FAC-METRO-MAIN',
              milestones: [
                {
                  milestone_id: 'MS-001',
                  name: 'Serum Lactate Level',
                  is_critical: true,
                },
              ],
            },
          ],
        },
      ],
    }),
    getPatientEnrollments: vi.fn().mockResolvedValue([
      {
        id: 1,
        enrollment_id: 'ENR-001',
        patient_id: 'PAT-00101',
        pathway_id: 'PATH-001',
        current_stage_id: 'STG-001',
        status: 'active',
        enrolled_at: '2026-09-01T10:00:00Z',
        completed_milestones: ['MS-001'],
        has_variance: false,
        pathway: {
          pathway_id: 'PATH-001',
          name: 'Regional Sepsis Resuscitation & Bundle Protocol',
          stages: [
            {
              stage_id: 'STG-001',
              sequence_order: 1,
              name: 'Emergency Screening & Initial Resuscitation',
              assigned_facility_id: 'FAC-METRO-MAIN',
              milestones: [
                {
                  milestone_id: 'MS-001',
                  name: 'Serum Lactate Level',
                  is_critical: true,
                },
              ],
            },
          ],
        },
      },
    ]),
    enrollPatient: vi.fn(),
    advanceStage: vi.fn(),
    completeMilestone: vi.fn(),
  },
}));

describe('RegionalInteroperabilityWorkspace', () => {
  it('renders workspace tabs and loads patient candidate duplicate matches', async () => {
    render(<RegionalInteroperabilityWorkspace />);

    expect(screen.getByText(/Regional Interoperability & Care Orchestration/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Federated EMPI Identity Resolution/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Cross-Hospital C-CDA Exchange/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Regional Clinical Pathways/i).length).toBeGreaterThan(0);
  });

  it('navigates to C-CDA tab and triggers document generation', async () => {
    render(<RegionalInteroperabilityWorkspace />);

    const ccdaTab = screen.getByText(/Cross-Hospital C-CDA Exchange/i);
    fireEvent.click(ccdaTab);

    const exportHeading = await screen.findByText(/Export HL7 C-CDA/i);
    expect(exportHeading).toBeInTheDocument();

    const generateBtn = screen.getByRole('button', { name: /Generate XML/i });
    fireEvent.click(generateBtn);

    expect(ccdaApi.exportDocument).toHaveBeenCalled();
  });

  it('navigates to Pathways tab and renders multi-hospital stage timeline', async () => {
    render(<RegionalInteroperabilityWorkspace />);

    const pathwaysTab = screen.getByText(/Regional Clinical Pathways/i);
    fireEvent.click(pathwaysTab);

    const stageTitle = await screen.findByText('Emergency Screening & Initial Resuscitation');
    expect(stageTitle).toBeInTheDocument();

    const milestoneName = await screen.findByText('Serum Lactate Level');
    expect(milestoneName).toBeInTheDocument();

    const facilityBadge = await screen.findByText('FAC-METRO-MAIN');
    expect(facilityBadge).toBeInTheDocument();
  });
});
