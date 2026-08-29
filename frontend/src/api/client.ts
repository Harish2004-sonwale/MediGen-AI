// ==============================================================================
// MediGen AI - Centralized HTTP & SSE API Client
// Strict Zero-Secret Architecture, Typed Endpoints & Robust Error Handling
// ==============================================================================

/// <reference types="vite/client" />

import {
  BackgroundTask,

  CarePlan,
  CarePlanCategory,
  CarePlanListResponse,
  CareTask,
  CareTaskListResponse,
  CareTaskType,
  ChatSession,
  ChatSessionDetail,
  ClinicalAlert,
  ClinicalAlertListResponse,
  ClinicalNote,
  ClinicalNoteListResponse,
  ClinicalRiskAssessment,
  ClinicalSafetyReport,
  CohortAnalytics,
  CohortCriteria,
  CohortListResponse,
  CohortMembership,
  CohortType,
  DiagnosticMedia,

  DiagnosticMediaListResponse,
  MediaBodySite,
  MediaModality,
  MedicalDocument,
  NoteType,
  Patient,
  PatientCohort,
  RiskAssessmentListResponse,
  RiskType,
  TaskListResponse,

  TaskPriority,
  TimelineCitation,
  TimelineEvent,
  TimelineSummary,
  TokenResponse,
  User,
  UserRole,
  VitalSimulationProfile,
  VitalTelemetry,
  VitalTelemetryListResponse,
} from '../types';

const API_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_URL) || '/api/v1';

// Token Management
export const getStoredToken = (): string | null => {
  return localStorage.getItem('medigen_token') || sessionStorage.getItem('medigen_token');
};

export const setStoredToken = (token: string, remember = true): void => {
  if (remember) {
    localStorage.setItem('medigen_token', token);
  } else {
    sessionStorage.setItem('medigen_token', token);
  }
};

export const clearStoredToken = (): void => {
  localStorage.removeItem('medigen_token');
  sessionStorage.removeItem('medigen_token');
  localStorage.removeItem('medigen_user');
  sessionStorage.removeItem('medigen_user');
};

// Generic Fetch Wrapper
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // Token expired or invalid
    clearStoredToken();
    window.dispatchEvent(new Event('medigen:unauthorized'));
    throw new Error('Your session has expired. Please sign in again.');
  }

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errorData = await response.json();
      errorDetail = errorData.detail || errorData.message || errorDetail;
    } catch {
      // Non-JSON response
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<T>;
}

// 1. Authentication APIs
export const authApi = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    return apiRequest<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  register: async (
    name: string,
    email: string,
    password: string,
    role: UserRole
  ): Promise<User> => {
    return apiRequest<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password, role }),
    });
  },

  getMe: async (): Promise<User> => {
    return apiRequest<User>('/auth/me', {
      method: 'GET',
    });
  },
};

// 2. Patient Management APIs
export const patientsApi = {
  list: async (search?: string, status?: string): Promise<Patient[]> => {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (status) params.append('status', status);
    const query = params.toString() ? `?${params.toString()}` : '';
    return apiRequest<Patient[]>(`/patients${query}`, { method: 'GET' });
  },

  get: async (patientId: string): Promise<Patient> => {
    return apiRequest<Patient>(`/patients/${encodeURIComponent(patientId)}`, {
      method: 'GET',
    });
  },

  create: async (data: Partial<Patient>): Promise<Patient> => {
    return apiRequest<Patient>('/patients', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

// 3. Clinical Timeline APIs
export const timelineApi = {
  getTimeline: async (
    patientId: string,
    eventType?: string
  ): Promise<TimelineEvent[]> => {
    const params = new URLSearchParams();
    if (eventType) params.append('event_type', eventType);
    const query = params.toString() ? `?${params.toString()}` : '';
    return apiRequest<TimelineEvent[]>(
      `/patients/${encodeURIComponent(patientId)}/timeline${query}`,
      { method: 'GET' }
    );
  },

  getSummary: async (
    patientId: string,
    focus?: string
  ): Promise<TimelineSummary> => {
    const params = new URLSearchParams();
    if (focus) params.append('focus', focus);
    const query = params.toString() ? `?${params.toString()}` : '';
    return apiRequest<TimelineSummary>(
      `/patients/${encodeURIComponent(patientId)}/timeline/summary${query}`,
      { method: 'GET' }
    );
  },
};

// 4. Clinical Decision Support / Safety APIs
export const safetyApi = {
  checkSafety: async (
    patientId: string,
    candidateMedications?: string[],
    activeConditions?: string[]
  ): Promise<ClinicalSafetyReport> => {
    return apiRequest<ClinicalSafetyReport>(
      `/safety/check?patient_id=${encodeURIComponent(patientId)}`,
      {
        method: 'POST',
        body: JSON.stringify({
          candidate_medications: candidateMedications,
          active_conditions: activeConditions,
        }),
      }
    );
  },
};

// 5. Medical Documents APIs
export const documentsApi = {
  list: async (patientId: string): Promise<MedicalDocument[]> => {
    return apiRequest<MedicalDocument[]>(
      `/patients/${encodeURIComponent(patientId)}/documents`,
      { method: 'GET' }
    );
  },

  upload: async (
    patientId: string,
    file: File,
    title: string,
    documentType: string
  ): Promise<MedicalDocument> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    formData.append('document_type', documentType);

    return apiRequest<MedicalDocument>(
      `/patients/${encodeURIComponent(patientId)}/documents`,
      {
        method: 'POST',
        body: formData,
      }
    );
  },
};

// 6. Real-Time AI Clinical Chat & SSE Streaming
export interface StreamChatHandlers {
  onStart?: (data: { session_id: string; message_id: string }) => void;
  onDelta?: (text: string) => void;
  onCitation?: (citation: TimelineCitation) => void;
  onDone?: (data: {
    message_id: string;
    completed: boolean;
    insufficient_information: boolean;
    retrieved_chunks: number;
  }) => void;
  onError?: (error: string) => void;
}

export const chatApi = {
  listSessions: async (patientId?: string): Promise<{ total: number; sessions: ChatSession[] }> => {
    const params = new URLSearchParams();
    if (patientId) params.append('patient_id', patientId);
    const query = params.toString() ? `?${params.toString()}` : '';
    return apiRequest<{ total: number; sessions: ChatSession[] }>(`/chat/sessions${query}`, {
      method: 'GET',
    });
  },

  createSession: async (patientId: string, title?: string): Promise<ChatSession> => {
    return apiRequest<ChatSession>('/chat/sessions', {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId, title }),
    });
  },

  getSession: async (sessionId: string): Promise<ChatSessionDetail> => {
    return apiRequest<ChatSessionDetail>(`/chat/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'GET',
    });
  },

  closeSession: async (sessionId: string): Promise<ChatSession> => {
    return apiRequest<ChatSession>(`/chat/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'DELETE',
    });
  },

  streamMessage: async (
    sessionId: string,
    message: string,
    handlers: StreamChatHandlers,
    signal?: AbortSignal
  ): Promise<void> => {
    const token = getStoredToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(
      `${API_BASE_URL}/chat/sessions/${encodeURIComponent(sessionId)}/messages/stream`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify({ message }),
        signal,
      }
    );

    if (!response.ok) {
      let errorMsg = `Streaming failed (${response.status})`;
      try {
        const errJson = await response.json();
        errorMsg = errJson.detail || errorMsg;
      } catch {
        // fallback
      }
      if (handlers.onError) handlers.onError(errorMsg);
      throw new Error(errorMsg);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Unable to read streaming response body.');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const block of lines) {
          if (!block.trim()) continue;

          let eventType = 'message';
          let dataStr = '';

          const blockLines = block.split('\n');
          for (const line of blockLines) {
            if (line.startsWith('event:')) {
              eventType = line.replace('event:', '').trim();
            } else if (line.startsWith('data:')) {
              dataStr = line.replace('data:', '').trim();
            }
          }

          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);

            if (eventType === 'start' && handlers.onStart) {
              handlers.onStart(data);
            } else if (eventType === 'delta' && handlers.onDelta) {
              handlers.onDelta(data.text || '');
            } else if (eventType === 'citation' && handlers.onCitation) {
              handlers.onCitation(data);
            } else if (eventType === 'done' && handlers.onDone) {
              handlers.onDone(data);
            } else if (eventType === 'error' && handlers.onError) {
              handlers.onError(data.error || 'Unknown streaming error');
            }
          } catch {
            // Non-JSON SSE chunk fallback
            if (eventType === 'delta' && handlers.onDelta) {
              handlers.onDelta(dataStr);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },
};

// 7. Background Task Management APIs
export const tasksApi = {
  list: async (page = 1, size = 20, patientId?: string): Promise<TaskListResponse> => {
    const params = new URLSearchParams({ page: String(page), size: String(size) });
    if (patientId) params.append('patient_id', patientId);
    return apiRequest<TaskListResponse>(`/tasks?${params.toString()}`, {
      method: 'GET',
    });
  },

  get: async (taskId: string): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>(`/tasks/${encodeURIComponent(taskId)}`, {
      method: 'GET',
    });
  },

  retry: async (taskId: string): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>(`/tasks/${encodeURIComponent(taskId)}/retry`, {
      method: 'POST',
    });
  },

  cancel: async (taskId: string): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>(`/tasks/${encodeURIComponent(taskId)}/cancel`, {
      method: 'POST',
    });
  },

  triggerDocumentProcessing: async (documentId: string): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>(
      `/tasks/documents/${encodeURIComponent(documentId)}/process`,
      { method: 'POST' }
    );
  },

  triggerTimelineSummary: async (patientId: string, focus?: string): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>(
      `/tasks/timeline/${encodeURIComponent(patientId)}/summary`,
      {
        method: 'POST',
        body: JSON.stringify({ focus }),
      }
    );
  },
};

// 8. Multi-Modal Medical Diagnostics APIs
export const mediaApi = {
  list: async (patientId: string): Promise<DiagnosticMediaListResponse> => {
    return apiRequest<DiagnosticMediaListResponse>(
      `/patients/${encodeURIComponent(patientId)}/media`,
      { method: 'GET' }
    );
  },

  get: async (mediaId: string): Promise<DiagnosticMedia> => {
    return apiRequest<DiagnosticMedia>(
      `/media/${encodeURIComponent(mediaId)}`,
      { method: 'GET' }
    );
  },

  upload: async (
    patientId: string,
    file: File,
    title: string,
    modality: MediaModality,
    bodySite?: MediaBodySite
  ): Promise<DiagnosticMedia> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', title);
    formData.append('modality', modality);
    if (bodySite) formData.append('body_site', bodySite);

    return apiRequest<DiagnosticMedia>(
      `/patients/${encodeURIComponent(patientId)}/media`,
      {
        method: 'POST',
        body: formData,
      }
    );
  },

  enqueueAnalysis: async (mediaId: string): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>(
      `/tasks/media/${encodeURIComponent(mediaId)}/analyze`,
      { method: 'POST' }
    );
  },

  review: async (
    mediaId: string,
    clinicianConfirmed: boolean,
    clinicianNotes?: string
  ): Promise<DiagnosticMedia> => {
    return apiRequest<DiagnosticMedia>(
      `/media/${encodeURIComponent(mediaId)}/review`,
      {
        method: 'POST',
        body: JSON.stringify({
          clinician_confirmed: clinicianConfirmed,
          clinician_notes: clinicianNotes,
        }),
      }
    );
  },

  getFileUrl: (mediaId: string): string => {
    return `${API_BASE_URL}/media/${encodeURIComponent(mediaId)}/file`;
  },
};

// 9. Clinical Notes & AI Scribe APIs
export const notesApi = {
  list: async (patientId: string): Promise<ClinicalNoteListResponse> => {
    return apiRequest<ClinicalNoteListResponse>(
      `/patients/${encodeURIComponent(patientId)}/notes`,
      { method: 'GET' }
    );
  },

  get: async (noteId: string): Promise<ClinicalNote> => {
    return apiRequest<ClinicalNote>(
      `/notes/${encodeURIComponent(noteId)}`,
      { method: 'GET' }
    );
  },

  create: async (
    patientId: string,
    title: string,
    noteType: NoteType,
    rawText: string,
    contentJson?: Record<string, any>,
    encounterId?: number
  ): Promise<ClinicalNote> => {
    return apiRequest<ClinicalNote>(
      `/patients/${encodeURIComponent(patientId)}/notes`,
      {
        method: 'POST',
        body: JSON.stringify({
          title,
          note_type: noteType,
          raw_text: rawText,
          content_json: contentJson,
          encounter_id: encounterId,
        }),
      }
    );
  },

  update: async (
    noteId: string,
    data: { title?: string; raw_text?: string; content_json?: Record<string, any> }
  ): Promise<ClinicalNote> => {
    return apiRequest<ClinicalNote>(
      `/notes/${encodeURIComponent(noteId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      }
    );
  },

  enqueueSynthesis: async (
    patientId: string,
    noteType: NoteType,
    encounterId?: number,
    chatSessionId?: string,
    customInstructions?: string
  ): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>(
      `/tasks/notes/synthesize`,
      {
        method: 'POST',
        body: JSON.stringify({
          patient_id: patientId,
          note_type: noteType,
          encounter_id: encounterId,
          chat_session_id: chatSessionId,
          custom_instructions: customInstructions,
        }),
      }
    );
  },

  signoff: async (
    noteId: string,
    confirmAccuracy: boolean,
    clinicianNotes?: string
  ): Promise<ClinicalNote> => {
    return apiRequest<ClinicalNote>(
      `/notes/${encodeURIComponent(noteId)}/signoff`,
      {
        method: 'POST',
        body: JSON.stringify({
          confirm_accuracy: confirmAccuracy,
          clinician_notes: clinicianNotes,
        }),
      }
    );
  },
};

// 10. Vital Telemetry & CDS Alerting APIs
export const vitalsApi = {
  ingest: async (
    patientId: string,
    vitalData: {
      heart_rate?: number;
      systolic_bp?: number;
      diastolic_bp?: number;
      respiratory_rate?: number;
      temperature?: number;
      spo2_percent?: number;
      weight_kg?: number;
      device_id?: string;
      source?: string;
    }
  ): Promise<VitalTelemetry> => {
    return apiRequest<VitalTelemetry>(
      `/patients/${encodeURIComponent(patientId)}/vitals`,
      {
        method: 'POST',
        body: JSON.stringify(vitalData),
      }
    );
  },

  simulate: async (
    patientId: string,
    profile: VitalSimulationProfile,
    deviceId?: string
  ): Promise<VitalTelemetry> => {
    return apiRequest<VitalTelemetry>(
      `/patients/${encodeURIComponent(patientId)}/vitals/simulate`,
      {
        method: 'POST',
        body: JSON.stringify({ profile, device_id: deviceId }),
      }
    );
  },

  list: async (patientId: string, skip = 0, limit = 50): Promise<VitalTelemetryListResponse> => {
    return apiRequest<VitalTelemetryListResponse>(
      `/patients/${encodeURIComponent(patientId)}/vitals?skip=${skip}&limit=${limit}`,
      { method: 'GET' }
    );
  },

  getLatest: async (patientId: string): Promise<VitalTelemetry | null> => {
    return apiRequest<VitalTelemetry | null>(
      `/patients/${encodeURIComponent(patientId)}/vitals/latest`,
      { method: 'GET' }
    );
  },

  listAlerts: async (patientId: string, statusFilter?: string): Promise<ClinicalAlertListResponse> => {
    const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : '';
    return apiRequest<ClinicalAlertListResponse>(
      `/patients/${encodeURIComponent(patientId)}/alerts${query}`,
      { method: 'GET' }
    );
  },

  getAlert: async (alertId: string): Promise<ClinicalAlert> => {
    return apiRequest<ClinicalAlert>(
      `/alerts/${encodeURIComponent(alertId)}`,
      { method: 'GET' }
    );
  },

  acknowledgeAlert: async (alertId: string, notes?: string): Promise<ClinicalAlert> => {
    return apiRequest<ClinicalAlert>(
      `/alerts/${encodeURIComponent(alertId)}/acknowledge`,
      {
        method: 'POST',
        body: JSON.stringify({ notes }),
      }
    );
  },

  dismissAlert: async (alertId: string, reason: string): Promise<ClinicalAlert> => {
    return apiRequest<ClinicalAlert>(
      `/alerts/${encodeURIComponent(alertId)}/dismiss`,
      {
        method: 'POST',
        body: JSON.stringify({ reason }),
      }
    );
  },
};

// 11. Clinical Care Plans & Task Orchestration APIs
export const carePlansApi = {
  create: async (
    patientId: string,
    planData: {
      title: string;
      category: CarePlanCategory;
      description: string;
      intent?: string;
      encounter_id?: number;
      goals?: any[];
      interventions?: any[];
      start_date?: string;
      end_date?: string;
    }
  ): Promise<CarePlan> => {
    return apiRequest<CarePlan>(
      `/patients/${encodeURIComponent(patientId)}/care-plans`,
      {
        method: 'POST',
        body: JSON.stringify(planData),
      }
    );
  },

  list: async (patientId: string, statusFilter?: string): Promise<CarePlanListResponse> => {
    const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : '';
    return apiRequest<CarePlanListResponse>(
      `/patients/${encodeURIComponent(patientId)}/care-plans${query}`,
      { method: 'GET' }
    );
  },

  get: async (planId: string): Promise<CarePlan> => {
    return apiRequest<CarePlan>(
      `/care-plans/${encodeURIComponent(planId)}`,
      { method: 'GET' }
    );
  },

  update: async (planId: string, planData: Partial<CarePlan>): Promise<CarePlan> => {
    return apiRequest<CarePlan>(
      `/care-plans/${encodeURIComponent(planId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify(planData),
      }
    );
  },

  review: async (
    planId: string,
    confirmAccuracy: boolean,
    clinicianNotes?: string,
    activateImmediately = true
  ): Promise<CarePlan> => {
    return apiRequest<CarePlan>(
      `/care-plans/${encodeURIComponent(planId)}/review`,
      {
        method: 'POST',
        body: JSON.stringify({
          confirm_accuracy: confirmAccuracy,
          clinician_notes: clinicianNotes,
          activate_immediately: activateImmediately,
        }),
      }
    );
  },

  complete: async (planId: string): Promise<CarePlan> => {
    return apiRequest<CarePlan>(
      `/care-plans/${encodeURIComponent(planId)}/complete`,
      { method: 'POST' }
    );
  },

  cancel: async (planId: string): Promise<CarePlan> => {
    return apiRequest<CarePlan>(
      `/care-plans/${encodeURIComponent(planId)}/cancel`,
      { method: 'POST' }
    );
  },

  enqueueSynthesis: async (
    patientId: string,
    category: CarePlanCategory,
    customInstructions?: string
  ): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>(
      `/tasks/care-plans/synthesize?patient_id=${encodeURIComponent(patientId)}`,
      {
        method: 'POST',
        body: JSON.stringify({
          category,
          custom_instructions: customInstructions,
        }),
      }
    );
  },

  createTask: async (
    patientId: string,
    taskData: {
      title: string;
      task_type?: CareTaskType;
      priority?: TaskPriority;
      instructions?: string;
      due_date: string;
      care_plan_id?: number;
      assigned_user_id?: number;
    }
  ): Promise<CareTask> => {
    return apiRequest<CareTask>(
      `/patients/${encodeURIComponent(patientId)}/care-tasks`,
      {
        method: 'POST',
        body: JSON.stringify(taskData),
      }
    );
  },

  listTasks: async (
    patientId: string,
    carePlanId?: string,
    statusFilter?: string
  ): Promise<CareTaskListResponse> => {
    const params = new URLSearchParams();
    if (carePlanId) params.append('care_plan_id', carePlanId);
    if (statusFilter) params.append('status', statusFilter);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return apiRequest<CareTaskListResponse>(
      `/patients/${encodeURIComponent(patientId)}/care-tasks${qs}`,
      { method: 'GET' }
    );
  },

  getTask: async (taskId: string): Promise<CareTask> => {
    return apiRequest<CareTask>(
      `/care-tasks/${encodeURIComponent(taskId)}`,
      { method: 'GET' }
    );
  },

  updateTask: async (taskId: string, taskData: Partial<CareTask>): Promise<CareTask> => {
    return apiRequest<CareTask>(
      `/care-tasks/${encodeURIComponent(taskId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify(taskData),
      }
    );
  },

  completeTask: async (taskId: string, completionNotes?: string): Promise<CareTask> => {
    return apiRequest<CareTask>(
      `/care-tasks/${encodeURIComponent(taskId)}/complete`,
      {
        method: 'POST',
        body: JSON.stringify({ completion_notes: completionNotes }),
      }
    );
  },
};

export const cohortsApi = {
  list: async (cohortType?: CohortType): Promise<CohortListResponse> => {
    const q = cohortType ? `?cohort_type=${encodeURIComponent(cohortType)}` : '';
    return apiRequest<CohortListResponse>(`/cohorts${q}`, { method: 'GET' });
  },

  get: async (cohortId: string): Promise<PatientCohort> => {
    return apiRequest<PatientCohort>(`/cohorts/${encodeURIComponent(cohortId)}`, { method: 'GET' });
  },

  create: async (data: {
    name: string;
    description: string;
    cohort_type?: CohortType;
    criteria?: CohortCriteria;
    is_dynamic?: boolean;
  }): Promise<PatientCohort> => {
    return apiRequest<PatientCohort>('/cohorts', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  update: async (cohortId: string, data: Partial<PatientCohort>): Promise<PatientCohort> => {
    return apiRequest<PatientCohort>(`/cohorts/${encodeURIComponent(cohortId)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  delete: async (cohortId: string): Promise<{ message: string; deleted: boolean }> => {
    return apiRequest<{ message: string; deleted: boolean }>(`/cohorts/${encodeURIComponent(cohortId)}`, {
      method: 'DELETE',
    });
  },

  listMembers: async (cohortId: string): Promise<CohortMembership[]> => {
    return apiRequest<CohortMembership[]>(`/cohorts/${encodeURIComponent(cohortId)}/members`, {
      method: 'GET',
    });
  },

  addMember: async (cohortId: string, patientId: string, notes?: string): Promise<CohortMembership> => {
    return apiRequest<CohortMembership>(`/cohorts/${encodeURIComponent(cohortId)}/members`, {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId, notes }),
    });
  },

  removeMember: async (cohortId: string, patientId: string): Promise<{ message: string }> => {
    return apiRequest<{ message: string }>(
      `/cohorts/${encodeURIComponent(cohortId)}/members/${encodeURIComponent(patientId)}`,
      { method: 'DELETE' }
    );
  },

  getAnalytics: async (cohortId: string): Promise<CohortAnalytics> => {
    return apiRequest<CohortAnalytics>(`/cohorts/${encodeURIComponent(cohortId)}/analytics`, {
      method: 'GET',
    });
  },

  calculateRisk: async (
    patientId: string,
    data: { risk_type: RiskType; encounter_id?: number; custom_context?: string }
  ): Promise<ClinicalRiskAssessment> => {
    return apiRequest<ClinicalRiskAssessment>(
      `/patients/${encodeURIComponent(patientId)}/risk-assessments`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  listRiskAssessments: async (
    patientId: string,
    riskType?: RiskType
  ): Promise<RiskAssessmentListResponse> => {
    const q = riskType ? `?risk_type=${encodeURIComponent(riskType)}` : '';
    return apiRequest<RiskAssessmentListResponse>(
      `/patients/${encodeURIComponent(patientId)}/risk-assessments${q}`,
      { method: 'GET' }
    );
  },

  getRiskAssessment: async (assessmentId: string): Promise<ClinicalRiskAssessment> => {
    return apiRequest<ClinicalRiskAssessment>(
      `/risk-assessments/${encodeURIComponent(assessmentId)}`,
      { method: 'GET' }
    );
  },
};
