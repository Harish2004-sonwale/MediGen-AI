import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { CarePlanWorkspace } from '../components/care/CarePlanWorkspace';
import { carePlansApi } from '../api/client';

vi.mock('../api/client', () => ({
  carePlansApi: {
    list: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          plan_id: 'CP-20260829-001',
          patient_id: 1,
          title: 'Comprehensive Chronic Disease Management Plan',
          category: 'chronic_disease_management',
          status: 'draft',
          intent: 'plan',
          description: 'Longitudinal plan targeting hypertension and metabolic control.',
          goals_json: [
            {
              goal_id: 'G-01',
              title: 'Blood Pressure Stabilization',
              target_metric: 'Systolic BP < 130 mmHg',
              status: 'in_progress',
            },
          ],
          interventions_json: [
            {
              intervention_id: 'INT-01',
              description: 'Home blood pressure monitoring twice daily.',
              category: 'monitoring',
              responsible_party: 'patient',
              status: 'active',
            },
          ],
          is_ai_generated: true,
          start_date: '2026-08-29T10:00:00Z',
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    listTasks: vi.fn().mockResolvedValue({
      total: 1,
      items: [
        {
          id: 1,
          task_id: 'CTSK-20260829-001',
          patient_id: 1,
          care_plan_id: 1,
          title: 'Comprehensive Metabolic Panel',
          task_type: 'lab_test_order',
          priority: 'ROUTINE',
          status: 'pending',
          instructions: 'Fasting metabolic and renal function check.',
          due_date: '2026-09-12T10:00:00Z',
          is_overdue: false,
          created_at: '2026-08-29T10:00:00Z',
        },
      ],
    }),
    review: vi.fn().mockResolvedValue({
      id: 1,
      plan_id: 'CP-20260829-001',
      title: 'Comprehensive Chronic Disease Management Plan',
      category: 'chronic_disease_management',
      status: 'active',
      reviewed_at: '2026-08-29T10:05:00Z',
    }),
    completeTask: vi.fn().mockResolvedValue({
      id: 1,
      task_id: 'CTSK-20260829-001',
      status: 'completed',
      completed_at: '2026-08-29T10:10:00Z',
    }),
    enqueueSynthesis: vi.fn().mockResolvedValue({
      task_id: 'TASK-20260829-001',
      task_type: 'care_plan_generation',
      status: 'queued',
    }),
  },
}));

describe('Clinical Care Plan & Workflow Workspace', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders care plan details, health goals, and follow-up tasks', async () => {
    render(<CarePlanWorkspace patientId="PAT-001" />);

    const planTitle = await screen.findByText(/Comprehensive Chronic Disease Management Plan/i);
    expect(planTitle).toBeInTheDocument();

    const goalTitle = await screen.findByText('Blood Pressure Stabilization');
    expect(goalTitle).toBeInTheDocument();

    const taskTitle = await screen.findByText('Comprehensive Metabolic Panel');
    expect(taskTitle).toBeInTheDocument();

    const aiBadge = await screen.findByText('🤖 AI-Generated');
    expect(aiBadge).toBeInTheDocument();
  });

  it('allows physician to review and activate draft care plan', async () => {
    render(<CarePlanWorkspace patientId="PAT-001" />);

    const reviewBtn = await screen.findByText('✓ Review & Activate Plan');
    fireEvent.click(reviewBtn);

    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);

    const signBtn = screen.getByText('Sign & Activate Plan');
    fireEvent.click(signBtn);

    expect(carePlansApi.review).toHaveBeenCalledWith('CP-20260829-001', true, '', true);
  });

  it('completes a clinical follow-up task', async () => {
    render(<CarePlanWorkspace patientId="PAT-001" />);

    const completeBtn = await screen.findByText('✓ Complete');
    fireEvent.click(completeBtn);

    const confirmBtn = screen.getByText('Confirm Completion');
    fireEvent.click(confirmBtn);

    expect(carePlansApi.completeTask).toHaveBeenCalledWith('CTSK-20260829-001', undefined);
  });
});
