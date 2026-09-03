import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../App';
import * as apiClient from '../api/client';

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof apiClient>('../api/client');
  return {
    ...actual,
    authApi: {
      login: vi.fn().mockResolvedValue({
        access_token: 'mock-jwt-token-doctor',
        token_type: 'bearer',
        user: {
          id: 1,
          email: 'doctor@example.com',
          name: 'Dr. John Doe',
          first_name: 'John',
          last_name: 'Doe',
          role: 'doctor',
          is_active: true,
          facility_id: 'FAC-METRO-MAIN',
        },
      }),
      getMe: vi.fn().mockResolvedValue({
        id: 1,
        email: 'doctor@example.com',
        name: 'Dr. John Doe',
        first_name: 'John',
        last_name: 'Doe',
        role: 'doctor',
        is_active: true,
        facility_id: 'FAC-METRO-MAIN',
      }),
      register: vi.fn(),
    },
    patientsApi: {
      list: vi.fn().mockResolvedValue([
        {
          id: 1,
          patient_id: 'PAT-00101',
          first_name: 'Alexander',
          last_name: 'Hamilton',
          date_of_birth: '1980-01-11',
          gender: 'male',
          facility_id: 'FAC-METRO-MAIN',
          is_active: true,
          created_at: '2026-08-30T00:00:00Z',
        },
        {
          id: 2,
          patient_id: 'PAT-00102',
          first_name: 'Eleanor',
          last_name: 'Vance',
          date_of_birth: '1975-06-15',
          gender: 'female',
          facility_id: 'FAC-METRO-MAIN',
          is_active: true,
          created_at: '2026-08-30T00:00:00Z',
        },
      ]),
      get: vi.fn().mockResolvedValue({
        id: 1,
        patient_id: 'PAT-00101',
        first_name: 'Alexander',
        last_name: 'Hamilton',
        date_of_birth: '1980-01-11',
        gender: 'male',
        facility_id: 'FAC-METRO-MAIN',
        is_active: true,
        created_at: '2026-08-30T00:00:00Z',
      }),
    },
    tenantApi: {
      listFacilities: vi.fn().mockResolvedValue([
        {
          id: 1,
          facility_id: 'FAC-METRO-MAIN',
          org_id: 'ORG-001',
          name: 'Metropolitan General Hospital - Main Campus',
          facility_code: 'MGH-MAIN',
          is_active: true,
        },
        {
          id: 2,
          facility_id: 'FAC-METRO-WEST',
          org_id: 'ORG-001',
          name: 'Metropolitan Community Hospital - West Campus',
          facility_code: 'MCH-WEST',
          is_active: true,
        },
      ]),
      listOrganizations: vi.fn().mockResolvedValue([
        {
          id: 1,
          org_id: 'ORG-001',
          name: 'Metropolitan Regional Health Network',
          is_active: true,
        },
      ]),
      listDepartments: vi.fn().mockResolvedValue([]),
      getEHRConfig: vi.fn().mockResolvedValue({
        ehr_vendor: 'EPIC',
        fhir_base_url: 'https://epic.mgh.org/api/FHIR/R4',
        is_enabled: true,
      }),
    },
    empiApi: {
      findCandidateMatches: vi.fn().mockResolvedValue({
        query_patient_id: 'PAT-00101',
        total_candidates: 2,
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
          {
            patient_id: 'PAT-00105',
            first_name: 'Eleanore',
            last_name: 'Vance',
            date_of_birth: '1975-06-15',
            gender: 'female',
            facility_id: 'FAC-METRO-WEST',
            match_score: 0.88,
            grade: 'exact',
            feature_breakdown: {
              name_score: 0.92,
              dob_score: 1.0,
              phone_score: 0.85,
            },
          },
        ],
      }),
      listReviews: vi.fn().mockResolvedValue([]),
      linkPatient: vi.fn().mockResolvedValue({ enterprise_id: 'EUID-001' }),
      unlinkPatient: vi.fn().mockResolvedValue({ success: true }),
      mergeIdentities: vi.fn().mockResolvedValue({ message: 'Merged successfully' }),
      resolveReview: vi.fn().mockResolvedValue({ success: true }),
    },
    ccdaApi: {
      exportDocument: vi.fn().mockResolvedValue({
        document_id: 'CCDA-001',
        patient_id: 'PAT-00101',
        document_type: 'continuity_of_care_document',
        title: 'Continuity of Care Document',
        created_at: '2026-09-01T10:00:00Z',
        sha256_hash: 'abc123hash999888777',
        xml_content: '<?xml version="1.0"?><ClinicalDocument>Sample HL7 C-CDA XML</ClinicalDocument>',
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
      listDocuments: vi.fn().mockResolvedValue({ total: 0, documents: [] }),
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
                  { milestone_id: 'MS-001', name: 'Serum Lactate Level', is_critical: true },
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
          completed_milestones: ['MS-001'],
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
                  { milestone_id: 'MS-001', name: 'Serum Lactate Level', is_critical: true },
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
  };
});

describe('Full Real-World Application & UI Flow Verification', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('verifies clean initial loading without hang and renders login form', async () => {
    render(<App />);

    // Must NOT be stuck at "Initializing Clinical Workspace..."
    await waitFor(() => {
      expect(screen.queryByText(/Initializing Clinical Workspace/i)).not.toBeInTheDocument();
    });

    // Login form should be visible
    expect(screen.getByText(/MediGen/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/user@hospital.org/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/••••••••••••/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Sign In$/i })).toBeInTheDocument();
  });

  it('performs real login, mounts clinical dashboard, navigates tabs, and executes Phase 9.0.25 workflows', async () => {
    render(<App />);

    // 1. Enter credentials and submit
    const emailInput = screen.getByPlaceholderText(/user@hospital.org/i);
    const passwordInput = screen.getByPlaceholderText(/••••••••••••/i);
    fireEvent.change(emailInput, { target: { value: 'doctor@hospital.org' } });
    fireEvent.change(passwordInput, { target: { value: 'ValidPassword123!' } });

    const submitBtn = screen.getByRole('button', { name: /^Sign In$/i });
    fireEvent.click(submitBtn);

    // 2. Verify dashboard loads with authenticated doctor
    const doctorHeading = await screen.findByText(/John Doe/i);
    expect(doctorHeading).toBeInTheDocument();
    expect(screen.getByText(/DOCTOR/i)).toBeInTheDocument();

    // 3. Verify Patient Directory & Active Patient selection
    const patientItems = await screen.findAllByText(/Alexander Hamilton/i);
    expect(patientItems.length).toBeGreaterThan(0);

    // 4. Verify Facility Selector & Switching
    expect(screen.getAllByText(/Metropolitan General Hospital - Main Campus/i).length).toBeGreaterThan(0);

    // 5. Navigate to Regional Interoperability & EMPI Workspace
    const interopTabBtn = screen.getByTestId('tab-btn-regional-interop');
    fireEvent.click(interopTabBtn);

    // Verify EMPI Candidate Matching
    expect(await screen.findByText(/Probabilistic Identity Resolution Candidates/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Exact Match/i).length).toBeGreaterThan(0);

    // Verify C-CDA Sub-tab
    const ccdaSubTab = screen.getByText(/Cross-Hospital C-CDA Exchange/i);
    fireEvent.click(ccdaSubTab);
    expect(await screen.findByText(/Export HL7 C-CDA/i)).toBeInTheDocument();

    // Trigger C-CDA Generation
    const generateBtn = screen.getByRole('button', { name: /Generate XML/i });
    fireEvent.click(generateBtn);
    expect(apiClient.ccdaApi.exportDocument).toHaveBeenCalled();

    // Verify Regional Pathways Sub-tab
    const pathwaysSubTab = screen.getByText(/Regional Clinical Pathways/i);
    fireEvent.click(pathwaysSubTab);
    const pathwayItems = await screen.findAllByText(/Regional Sepsis Resuscitation/i);
    expect(pathwayItems.length).toBeGreaterThan(0);
    expect(screen.getByText(/Emergency Screening & Initial Resuscitation/i)).toBeInTheDocument();

    // 6. Test Logout Workflow
    const logoutBtn = screen.getByRole('button', { name: /Logout/i });
    fireEvent.click(logoutBtn);

    // Verify returning cleanly to login screen
    expect(await screen.findByPlaceholderText(/user@hospital.org/i)).toBeInTheDocument();
    expect(screen.queryByText(/John Doe/i)).not.toBeInTheDocument();
  });
});
