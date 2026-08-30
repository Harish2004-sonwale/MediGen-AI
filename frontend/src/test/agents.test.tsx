import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { ClinicalAgentsWorkspace } from '../components/agents/ClinicalAgentsWorkspace';
import { agentsApi, patientsApi, fhirApi } from '../api/client';

vi.mock('../api/client', () => ({
  patientsApi: {
    list: vi.fn().mockResolvedValue({
      items: [
        {
          id: 1,
          patient_id: 'PAT-AGENT-001',
          first_name: 'Arthur',
          last_name: 'Pendelton',
          gender: 'male',
          date_of_birth: '1962-08-14',
          status: 'active',
        },
      ],
      total: 1,
    }),
  },
  agentsApi: {
    listDefinitions: vi.fn().mockResolvedValue({
      total: 2,
      items: [
        {
          id: 1,
          agent_id: 'risk_surveillance',
          agent_type: 'risk_surveillance',
          name: 'Risk Surveillance Agent',
          description: 'Monitors vital drift and acute CDS alerts.',
          is_active: true,
          version: '1.0.0',
          default_action_class: 'HIGH_RISK',
          created_at: '2026-08-30T10:00:00Z',
        },
        {
          id: 2,
          agent_id: 'medication_safety',
          agent_type: 'medication_safety',
          name: 'Medication Safety Agent',
          description: 'Evaluates polypharmacy and duplicate therapies.',
          is_active: true,
          version: '1.0.0',
          default_action_class: 'CLINICIAN_APPROVAL_REQUIRED',
          created_at: '2026-08-30T10:00:00Z',
        },
      ],
    }),

    getPatientCareCoordination: vi.fn().mockResolvedValue({
      patient_id: 'PAT-AGENT-001',
      overall_summary: 'Synthesized 2 multi-agent care recommendations.',
      recommendations_count: 2,
      urgent_recommendations_count: 1,
      recommendations: [
        {
          id: 101,
          recommendation_id: 'REC-001',
          run_id: 1,
          category: 'risk_escalation',
          title: 'Critical Vital Deterioration: Hypertensive Crisis',
          description: 'Systolic BP 185 mmHg detected. Urgent clinician review advised.',
          rationale: 'Prevent acute cardiovascular event.',
          priority: 'urgent',
          action_class: 'HIGH_RISK',
          suggested_action_type: 'acknowledge_alert',
          approval_status: 'pending_review',
          confidence_score: 0.98,
          provenance_hash: 'a1b2c3d4e5f6',
          created_at: '2026-08-30T10:00:00Z',
        },
        {
          id: 102,
          recommendation_id: 'REC-002',
          run_id: 1,
          category: 'quality_outreach',
          title: 'HEDIS Care Gap Remediation Outreach',
          description: 'Colorectal screening overdue.',
          rationale: 'Fulfill preventative quality measure.',
          priority: 'medium',
          action_class: 'RECOMMENDATION',
          suggested_action_type: 'dispatch_care_task',
          approval_status: 'pending_review',
          confidence_score: 0.9,
          provenance_hash: 'b2c3d4e5f6a1',
          created_at: '2026-08-30T10:00:00Z',
        },
      ],
      provenance_hash: 'c3d4e5f6a1b2',
      evaluated_at: '2026-08-30T10:00:00Z',
    }),
    listRuns: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          run_id: 'RUN-20260830-A1B2',
          patient_id: 'PAT-AGENT-001',
          agent_code: 'master_orchestrator',
          agent_name: 'Autonomous Care Coordinator',
          status: 'completed',
          overall_summary: 'Synthesized 2 multi-agent care recommendations.',
          recommendations_count: 2,
          urgent_count: 1,
          approval_required_count: 1,
          provenance_hash: 'c3d4e5f6a1b2',
          created_at: '2026-08-30T10:00:00Z',
        },
      ],
    }),
    synthesizePatientCareCoordination: vi.fn().mockResolvedValue({
      patient_id: 'PAT-AGENT-001',
      overall_summary: 'Synthesized fresh multi-agent care recommendations.',
      recommendations_count: 2,
      urgent_recommendations_count: 1,
      recommendations: [],
      provenance_hash: 'd4e5f6a1b2c3',
      evaluated_at: '2026-08-30T10:05:00Z',
    }),
    approveRecommendation: vi.fn().mockResolvedValue({
      id: 101,
      recommendation_id: 'REC-001',
      approval_status: 'approved',
      review_notes: 'Concur with clinical recommendation.',
    }),
    rejectRecommendation: vi.fn().mockResolvedValue({
      id: 102,
      recommendation_id: 'REC-002',
      approval_status: 'rejected',
      review_notes: 'Patient completed outside facility.',
    }),
    executeRecommendationAction: vi.fn().mockResolvedValue({
      status: 'executed',
      task_id: 'TASK-101',
    }),
    enqueueCareCoordinationTask: vi.fn().mockResolvedValue({
      task_id: 'TASK-ASYNC-001',
      task_type: 'CARE_COORDINATION_SYNTHESIS',
      status: 'queued',
    }),
  },
  fhirApi: {
    exportAgentTask: vi.fn().mockResolvedValue({
      resourceType: 'Task',
      id: 'task-REC-001',
      status: 'requested',
    }),
    exportAgentProvenance: vi.fn().mockResolvedValue({
      resourceType: 'Provenance',
      id: 'prov-1',
    }),
  },
}));

describe('ClinicalAgentsWorkspace Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Clinician Supervision Safety Banner and Agent Registry', async () => {
    render(<ClinicalAgentsWorkspace />);

    expect(screen.getByText(/Autonomous Care Coordination & Multi-Agent Engine/i)).toBeInTheDocument();
    expect(screen.getByText(/Clinician Supervision Required/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Risk Surveillance Agent/i)).toBeInTheDocument();
      expect(screen.getByText(/Medication Safety Agent/i)).toBeInTheDocument();
    });
  });

  it('renders Prioritized Recommendations and Clinician Approval Controls', async () => {
    render(<ClinicalAgentsWorkspace />);

    await waitFor(() => {
      expect(screen.getByText(/Critical Vital Deterioration: Hypertensive Crisis/i)).toBeInTheDocument();
      expect(screen.getByText(/HEDIS Care Gap Remediation Outreach/i)).toBeInTheDocument();
    });

    const approveButtons = screen.getAllByRole('button', { name: /Approve Action/i });
    expect(approveButtons.length).toBeGreaterThan(0);
    fireEvent.click(approveButtons[0]);

    await waitFor(() => {
      expect(agentsApi.approveRecommendation).toHaveBeenCalled();
    });
  });

  it('triggers on-demand Care Coordination Synthesis', async () => {
    render(<ClinicalAgentsWorkspace />);

    await waitFor(() => {
      expect(screen.getByText(/Synthesize Care Coordination/i)).toBeInTheDocument();
    });

    const synthBtn = screen.getByRole('button', { name: /Synthesize Care Coordination/i });
    fireEvent.click(synthBtn);

    await waitFor(() => {
      expect(agentsApi.synthesizePatientCareCoordination).toHaveBeenCalledWith('PAT-AGENT-001');
    });
  });

  it('opens and displays FHIR R4 Task export modal', async () => {
    render(<ClinicalAgentsWorkspace />);

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /FHIR Task/i }).length).toBeGreaterThan(0);
    });

    const fhirButtons = screen.getAllByRole('button', { name: /FHIR Task/i });
    fireEvent.click(fhirButtons[0]);

    await waitFor(() => {
      expect(fhirApi.exportAgentTask).toHaveBeenCalledWith('REC-001');
      expect(screen.getByText(/FHIR R4 Task/i)).toBeInTheDocument();
    });
  });
});
