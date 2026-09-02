// ==============================================================================
// MediGen AI - Centralized HTTP & SSE API Client
// Strict Zero-Secret Architecture, Typed Endpoints & Robust Error Handling
// ==============================================================================

/// <reference types="vite/client" />

import {
  AbnormalFlag,
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
  ClinicalHandoff,
  ClinicalNote,
  ClinicalNoteListResponse,
  ClinicalOrder,
  ClinicalOrderListResponse,
  ClinicalRiskAssessment,
  ClinicalSafetyReport,
  CohortAnalytics,
  CohortCriteria,
  CohortListResponse,
  CohortMembership,
  CohortType,
  DiagnosticMedia,
  DiagnosticMediaListResponse,
  DiagnosticResult,
  DiagnosticResultListResponse,
  DiagnosticResultStatus,
  DischargeDisposition,
  DischargeProtocol,
  DischargeProtocolListResponse,
  DischargeStatus,
  HandoffFramework,
  HandoffListResponse,
  HandoffStatus,
  HandoffType,
  IllnessSeverity,
  MediaBodySite,
  MediaModality,
  MedicalDocument,
  NoteType,
  OrderBundleItem,
  OrderBundleSuggestResponse,
  OrderCategory,
  OrderPriority,
  OrderStatus,
  Patient,
  PatientCohort,
  QualityDomain,
  QualityMeasure,
  QualityMeasureGap,
  QualityMeasureGapListResponse,
  QualityMeasureListResponse,
  QualityMeasureReport,
  QualityMeasureReportListResponse,
  QualityMeasureResult,
  QualityMeasureResultListResponse,
  ReportScope,
  RiskAssessmentListResponse,
  RiskType,
  GapSeverity,
  GapStatus,

  PROMDefinition,
  PROMDefinitionListResponse,
  PROMResponseDetail,
  PROMResponseListResponse,
  RPMDevice,
  RPMDeviceListResponse,
  RPMEscalationAlert,
  RPMEscalationAlertListResponse,
  RPMObservation,
  RPMObservationListResponse,
  RPMObservationType,
  RPMProgram,
  RPMProgramListResponse,
  RPMSourceType,
  RPMTelemetrySummary,
  TelehealthSession,
  TelehealthSessionListResponse,
  TelehealthStatus,
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
  BatchMatchResponse,
  BiomarkerObservation,
  ClinicalTrial,
  ClinicalTrialDetail,
  ClinicalTrialListResponse,
  ClinicianReviewStatus,
  GenomicProfile,
  GenomicProfileDetail,
  GenomicProfileListResponse,
  MatchStatus,
  PrecisionEligibilityStatus,
  PrecisionTreatmentEligibility,
  PrecisionTreatmentEligibilityListResponse,
  TrialEligibilityCriterion,
  TrialMatch,
  TrialMatchListResponse,
  TrialPhase,
  TrialStatus,
  AgentRunStatus,
  AgentType,
  ApprovalStatus,
  CareCoordinationSynthesisResponse,
  ClinicalAgentDefinition,
  ClinicalAgentDefinitionListResponse,
  ClinicalAgentRecommendation,
  ClinicalAgentRun,
  ClinicalAgentRunDetail,
  ClinicalAgentRunListResponse,
  RecommendationActionClass,

  RecommendationPriority,
  FindingReviewStatus,
  ImagingAnalysisResponse,
  ImagingAsset,
  ImagingFinding,
  ImagingStudy,
  ImagingTimelineItem,
  ImagingTimelineResponse,
  RadiologyReport,
  ReportStatus,
  AuditEventListResponse,
  AuditIntegrityVerificationResponse,
  ClinicalAuditEvent,
  ComplianceSummaryResponse,
  ConsentVerificationRequest,
  ConsentVerificationResponse,
  DataRetentionPolicy,
  DataRetentionPolicyCreateRequest,
  LegalClinicalHold,
  LegalClinicalHoldCreateRequest,
  LegalClinicalHoldReleaseRequest,
  PatientConsent,
  PatientConsentCreateRequest,
  PatientConsentRevokeRequest,
  SecurityIncident,
  SecurityIncidentCreateRequest,
  SecurityIncidentUpdateRequest,
  SecurityScanResult,
  SystemLivenessResponse,
  SystemReadinessResponse,
  SystemMetricsResponse,
  FHIRCapabilityStatement,
  SmartConfiguration,
  JWKSResponse,
  SmartTokenResponse,
  SmartIntrospectResponse,
  CDSServicesDiscoveryResponse,
  CDSHookResponse,
  HealthOrganization,
  ClinicalFacility,
  DepartmentUnit,
  EHRIntegrationConfig,
  TerminologyNormalizeResponse,
  TerminologyCrossWalkResponse,
  WebSocketStats,
  OutboxEvent,
  OutboxMetrics,
  MFASetupResponse,
  MFAStatusResponse,
  MFAVerifyResponse,
  FHIRSubscription,
  BulkExportJob,
  EMPICandidateMatch,
  EMPICandidatesResponse,
  EMPILinkResponse,
  EMPIMergeResponse,
  EMPIMatchReviewItem,
  CCDAExportResponse,
  CCDAImportResponse,
  CCDADocumentExchange,
  RegionalPathway,
  PatientPathwayEnrollment,
  PGxRuleDefinition,
  ClinicalOrderSet,
  CDSEvaluationResponse,
  OrderSetExecuteResponse,
  CDSRuleOverrideResponse,
  CDSRuleEvaluationAudit,
  OrderSetCategory,
  CDSRuleTriggerEvent,
  MultiCenterStudySite,
  TrialProtocolDeviation,
  TrialCAPARecord,
  TrialIRBNotification,
  TrialPrescreenEvaluationResponse,
  MultiCenterTrialGovernanceSummary,
  DeviationCategory,
  DeviationSeverity,
  DeviationStatus,
  CAPARootCause,
  IRBSubmissionType,
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

// Facility Context Management
export const getActiveFacilityId = (): string | null => {
  return localStorage.getItem('medigen_active_facility_id') || sessionStorage.getItem('medigen_active_facility_id');
};

export const setActiveFacilityId = (facilityId: string | null): void => {
  if (facilityId) {
    localStorage.setItem('medigen_active_facility_id', facilityId);
  } else {
    localStorage.removeItem('medigen_active_facility_id');
    sessionStorage.removeItem('medigen_active_facility_id');
  }
  if (typeof window !== 'undefined' && window.dispatchEvent) {
    window.dispatchEvent(new CustomEvent('medigen:facility_changed', { detail: { facilityId } }));
  }
};

export const clearStoredToken = (): void => {
  localStorage.removeItem('medigen_token');
  sessionStorage.removeItem('medigen_token');
  localStorage.removeItem('medigen_user');
  sessionStorage.removeItem('medigen_user');
  localStorage.removeItem('medigen_active_facility_id');
  sessionStorage.removeItem('medigen_active_facility_id');
};

// Generic Fetch Wrapper
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const facilityId = getActiveFacilityId();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (facilityId && !headers.has('X-Facility-ID')) {
    headers.set('X-Facility-ID', facilityId);
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

  if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After') || '60';
    window.dispatchEvent(
      new CustomEvent('medigen:ratelimit', {
        detail: { retryAfter: parseInt(retryAfter, 10) },
      })
    );
    let errorDetail = `Rate limit exceeded. Please wait ${retryAfter}s before retrying.`;
    try {
      const errorData = await response.json();
      errorDetail = errorData.message || errorDetail;
    } catch {}
    throw new Error(errorDetail);
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

export const transitionsApi = {
  // Handoffs
  listHandoffs: async (patientId: string, status?: HandoffStatus): Promise<HandoffListResponse> => {
    const q = status ? `?status=${encodeURIComponent(status)}` : '';
    return apiRequest<HandoffListResponse>(
      `/patients/${encodeURIComponent(patientId)}/handoffs${q}`,
      { method: 'GET' }
    );
  },

  getHandoff: async (handoffId: string): Promise<ClinicalHandoff> => {
    return apiRequest<ClinicalHandoff>(`/handoffs/${encodeURIComponent(handoffId)}`, {
      method: 'GET',
    });
  },

  createHandoff: async (patientId: string, data: Partial<ClinicalHandoff>): Promise<ClinicalHandoff> => {
    return apiRequest<ClinicalHandoff>(
      `/patients/${encodeURIComponent(patientId)}/handoffs`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  synthesizeHandoff: async (
    patientId: string,
    data: {
      framework?: HandoffFramework;
      handoff_type?: HandoffType;
      receiver_user_id?: number;
      encounter_id?: number;
      custom_context?: string;
    }
  ): Promise<ClinicalHandoff> => {
    return apiRequest<ClinicalHandoff>(
      `/patients/${encodeURIComponent(patientId)}/handoffs/synthesize`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  updateHandoff: async (handoffId: string, data: Partial<ClinicalHandoff>): Promise<ClinicalHandoff> => {
    return apiRequest<ClinicalHandoff>(`/handoffs/${encodeURIComponent(handoffId)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  acknowledgeHandoff: async (handoffId: string, synthesisNotes: string): Promise<ClinicalHandoff> => {
    return apiRequest<ClinicalHandoff>(
      `/handoffs/${encodeURIComponent(handoffId)}/acknowledge`,
      {
        method: 'POST',
        body: JSON.stringify({ synthesis_notes: synthesisNotes }),
      }
    );
  },

  // Discharge Protocols
  listDischargeProtocols: async (
    patientId: string,
    status?: DischargeStatus
  ): Promise<DischargeProtocolListResponse> => {
    const q = status ? `?status=${encodeURIComponent(status)}` : '';
    return apiRequest<DischargeProtocolListResponse>(
      `/patients/${encodeURIComponent(patientId)}/discharge-protocols${q}`,
      { method: 'GET' }
    );
  },

  getDischargeProtocol: async (dischargeId: string): Promise<DischargeProtocol> => {
    return apiRequest<DischargeProtocol>(
      `/discharge-protocols/${encodeURIComponent(dischargeId)}`,
      { method: 'GET' }
    );
  },

  createDischargeProtocol: async (
    patientId: string,
    data: Partial<DischargeProtocol>
  ): Promise<DischargeProtocol> => {
    return apiRequest<DischargeProtocol>(
      `/patients/${encodeURIComponent(patientId)}/discharge-protocols`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  synthesizeDischargeProtocol: async (
    patientId: string,
    data: {
      encounter_id?: number;
      disposition?: DischargeDisposition;
      custom_instructions?: string;
    }
  ): Promise<DischargeProtocol> => {
    return apiRequest<DischargeProtocol>(
      `/patients/${encodeURIComponent(patientId)}/discharge-protocols/synthesize`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  updateDischargeProtocol: async (
    dischargeId: string,
    data: Partial<DischargeProtocol>
  ): Promise<DischargeProtocol> => {
    return apiRequest<DischargeProtocol>(
      `/discharge-protocols/${encodeURIComponent(dischargeId)}`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      }
    );
  },

  signoffDischargeProtocol: async (
    dischargeId: string,
    signoffRole: string,
    clinicalNotes?: string
  ): Promise<DischargeProtocol> => {
    return apiRequest<DischargeProtocol>(
      `/discharge-protocols/${encodeURIComponent(dischargeId)}/signoff`,
      {
        method: 'POST',
        body: JSON.stringify({ signoff_role: signoffRole, clinical_notes: clinicalNotes }),
      }
    );
  },
};

// =============================================================================
// PHASE 9.0.13: CPOE ORDERS & DIAGNOSTIC RESULTS API
// =============================================================================

export const ordersApi = {
  placeOrder: async (
    patientId: string,
    data: {
      encounter_id?: number;
      order_category: OrderCategory;
      order_type: string;
      priority: OrderPriority;
      clinical_indication: string;
      specimen_source?: string;
      order_details?: Record<string, any>;
    }
  ): Promise<ClinicalOrder> => {
    return apiRequest<ClinicalOrder>(
      `/patients/${encodeURIComponent(patientId)}/orders`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  suggestBundle: async (
    patientId: string,
    data: {
      encounter_id?: number;
      clinical_protocol?: string;
      custom_indication?: string;
    }
  ): Promise<OrderBundleSuggestResponse> => {
    return apiRequest<OrderBundleSuggestResponse>(
      `/patients/${encodeURIComponent(patientId)}/orders/suggest-bundle`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  listOrders: async (
    patientId: string,
    params?: {
      status?: OrderStatus;
      category?: OrderCategory;
    }
  ): Promise<ClinicalOrderListResponse> => {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.category) query.set('category', params.category);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<ClinicalOrderListResponse>(
      `/patients/${encodeURIComponent(patientId)}/orders${qs}`,
      { method: 'GET' }
    );
  },

  getOrder: async (orderId: string): Promise<ClinicalOrder> => {
    return apiRequest<ClinicalOrder>(`/orders/${encodeURIComponent(orderId)}`, {
      method: 'GET',
    });
  },

  updateOrder: async (
    orderId: string,
    data: {
      priority?: OrderPriority;
      status?: OrderStatus;
      clinical_indication?: string;
      specimen_source?: string;
      order_details?: Record<string, any>;
    }
  ): Promise<ClinicalOrder> => {
    return apiRequest<ClinicalOrder>(`/orders/${encodeURIComponent(orderId)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  recordResult: async (
    orderId: string,
    data: {
      encounter_id?: number;
      test_name: string;
      test_code_loinc?: string;
      status?: DiagnosticResultStatus;
      abnormal_flag?: AbnormalFlag;
      findings_summary: string;
      numeric_value?: number;
      unit_of_measure?: string;
      reference_range_low?: number;
      reference_range_high?: number;
      critical_threshold_low?: number;
      critical_threshold_high?: number;
      structured_components?: Array<Record<string, any>>;
    }
  ): Promise<DiagnosticResult> => {
    return apiRequest<DiagnosticResult>(
      `/orders/${encodeURIComponent(orderId)}/results`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  listResults: async (
    patientId: string,
    params?: {
      abnormal_flag?: AbnormalFlag;
    }
  ): Promise<DiagnosticResultListResponse> => {
    const query = new URLSearchParams();
    if (params?.abnormal_flag) query.set('abnormal_flag', params.abnormal_flag);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<DiagnosticResultListResponse>(
      `/patients/${encodeURIComponent(patientId)}/diagnostic-results${qs}`,
      { method: 'GET' }
    );
  },

  getResult: async (resultId: string): Promise<DiagnosticResult> => {
    return apiRequest<DiagnosticResult>(`/diagnostic-results/${encodeURIComponent(resultId)}`, {
      method: 'GET',
    });
  },

  reviewResult: async (
    resultId: string,
    data: {
      review_notes?: string;
    }
  ): Promise<DiagnosticResult> => {
    return apiRequest<DiagnosticResult>(
      `/diagnostic-results/${encodeURIComponent(resultId)}/review`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },
};

// 14. Clinical Quality Measures (CQMs), HEDIS/MIPS Compliance & Audit Reporting APIs
export const qualityApi = {
  listMeasures: async (params?: { domain?: QualityDomain }): Promise<QualityMeasureListResponse> => {
    const query = new URLSearchParams();
    if (params?.domain) query.set('domain', params.domain);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<QualityMeasureListResponse>(`/quality/measures${qs}`, { method: 'GET' });
  },

  getMeasure: async (measureId: string): Promise<QualityMeasure> => {
    return apiRequest<QualityMeasure>(`/quality/measures/${encodeURIComponent(measureId)}`, {
      method: 'GET',
    });
  },

  evaluatePatient: async (patientId: string): Promise<QualityMeasureResultListResponse> => {
    return apiRequest<QualityMeasureResultListResponse>(
      `/quality/patients/${encodeURIComponent(patientId)}/evaluate`,
      { method: 'POST' }
    );
  },

  getPatientResults: async (patientId: string): Promise<QualityMeasureResultListResponse> => {
    return apiRequest<QualityMeasureResultListResponse>(
      `/quality/patients/${encodeURIComponent(patientId)}/results`,
      { method: 'GET' }
    );
  },

  listGaps: async (params?: {
    patient_id?: string;
    measure_id?: string;
    status?: GapStatus;
    severity?: GapSeverity;
  }): Promise<QualityMeasureGapListResponse> => {
    const query = new URLSearchParams();
    if (params?.patient_id) query.set('patient_id', params.patient_id);
    if (params?.measure_id) query.set('measure_id', params.measure_id);
    if (params?.status) query.set('status', params.status);
    if (params?.severity) query.set('severity', params.severity);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<QualityMeasureGapListResponse>(`/quality/gaps${qs}`, { method: 'GET' });
  },

  updateGap: async (
    gapId: string,
    data: { status?: GapStatus; recommended_action?: string; due_date?: string }
  ): Promise<QualityMeasureGap> => {
    return apiRequest<QualityMeasureGap>(`/quality/gaps/${encodeURIComponent(gapId)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  createCareTaskForGap: async (gapId: string): Promise<QualityMeasureGap> => {
    return apiRequest<QualityMeasureGap>(
      `/quality/gaps/${encodeURIComponent(gapId)}/create-care-task`,
      { method: 'POST' }
    );
  },

  generateReport: async (data: {
    title?: string;
    report_scope?: ReportScope;
    scope_identifier?: string;
    measurement_period_start?: string;
    measurement_period_end?: string;
  }): Promise<QualityMeasureReport> => {
    return apiRequest<QualityMeasureReport>('/quality/reports/generate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listReports: async (params?: { report_scope?: ReportScope }): Promise<QualityMeasureReportListResponse> => {
    const query = new URLSearchParams();
    if (params?.report_scope) query.set('report_scope', params.report_scope);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<QualityMeasureReportListResponse>(`/quality/reports${qs}`, { method: 'GET' });
  },

  getReport: async (reportId: string): Promise<QualityMeasureReport> => {
    return apiRequest<QualityMeasureReport>(`/quality/reports/${encodeURIComponent(reportId)}`, {
      method: 'GET',
    });
  },

  enqueueCalculationTask: async (patientId?: string): Promise<BackgroundTask> => {
    const qs = patientId ? `?patient_id=${encodeURIComponent(patientId)}` : '';
    return apiRequest<BackgroundTask>(`/quality/tasks/calculate${qs}`, { method: 'POST' });
  },
};

// Remote Patient Monitoring (RPM), PROMs & Telehealth API
export const rpmApi = {
  enrollProgram: async (data: {
    patient_id: string;
    condition_name: string;
    program_name?: string;
    target_cadence_days?: number;
    clinical_goals?: string[];
  }): Promise<RPMProgram> => {
    return apiRequest<RPMProgram>('/rpm/programs/enroll', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listPrograms: async (params?: { patient_id?: string; status?: string }): Promise<RPMProgramListResponse> => {
    const query = new URLSearchParams();
    if (params?.patient_id) query.set('patient_id', params.patient_id);
    if (params?.status) query.set('status', params.status);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<RPMProgramListResponse>(`/rpm/programs${qs}`, { method: 'GET' });
  },

  registerDevice: async (data: {
    patient_id: string;
    device_type: string;
    manufacturer: string;
    model_number?: string;
    serial_number: string;
    supported_measurements?: string[];
  }): Promise<RPMDevice> => {
    return apiRequest<RPMDevice>('/rpm/devices', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listDevices: async (params?: { patient_id?: string; device_type?: string }): Promise<RPMDeviceListResponse> => {
    const query = new URLSearchParams();
    if (params?.patient_id) query.set('patient_id', params.patient_id);
    if (params?.device_type) query.set('device_type', params.device_type);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<RPMDeviceListResponse>(`/rpm/devices${qs}`, { method: 'GET' });
  },

  ingestObservation: async (data: {
    patient_id: string;
    device_id?: string;
    observation_type: RPMObservationType;
    numeric_value: number;
    secondary_value?: number;
    unit_of_measure: string;
    source_type?: RPMSourceType;
    raw_payload_json?: Record<string, any>;
  }): Promise<RPMObservation> => {
    return apiRequest<RPMObservation>('/rpm/observations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listObservations: async (params?: {
    patient_id?: string;
    observation_type?: string;
    classification?: string;
  }): Promise<RPMObservationListResponse> => {
    const query = new URLSearchParams();
    if (params?.patient_id) query.set('patient_id', params.patient_id);
    if (params?.observation_type) query.set('observation_type', params.observation_type);
    if (params?.classification) query.set('classification', params.classification);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<RPMObservationListResponse>(`/rpm/observations${qs}`, { method: 'GET' });
  },

  getPatientSummary: async (patientId: string): Promise<RPMTelemetrySummary> => {
    return apiRequest<RPMTelemetrySummary>(`/rpm/patients/${encodeURIComponent(patientId)}/summary`, {
      method: 'GET',
    });
  },

  listAlerts: async (params?: { patient_id?: string; status?: string }): Promise<RPMEscalationAlertListResponse> => {
    const query = new URLSearchParams();
    if (params?.patient_id) query.set('patient_id', params.patient_id);
    if (params?.status) query.set('status', params.status);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<RPMEscalationAlertListResponse>(`/rpm/alerts${qs}`, { method: 'GET' });
  },

  acknowledgeAlert: async (alertId: string, notes?: string): Promise<RPMEscalationAlert> => {
    return apiRequest<RPMEscalationAlert>(`/rpm/alerts/${encodeURIComponent(alertId)}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ notes }),
    });
  },

  resolveAlert: async (
    alertId: string,
    data: { clinical_action_taken: string; create_care_task?: boolean }
  ): Promise<RPMEscalationAlert> => {
    return apiRequest<RPMEscalationAlert>(`/rpm/alerts/${encodeURIComponent(alertId)}/resolve`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listPromDefinitions: async (domain?: string): Promise<PROMDefinitionListResponse> => {
    const qs = domain ? `?domain=${encodeURIComponent(domain)}` : '';
    return apiRequest<PROMDefinitionListResponse>(`/rpm/proms/definitions${qs}`, { method: 'GET' });
  },

  submitPromResponse: async (data: {
    prom_id: string;
    patient_id: string;
    answers: Record<string, any>;
    clinical_notes?: string;
  }): Promise<PROMResponseDetail> => {
    return apiRequest<PROMResponseDetail>('/rpm/proms/responses', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listPromResponses: async (params?: { patient_id?: string; prom_id?: string }): Promise<PROMResponseListResponse> => {
    const query = new URLSearchParams();
    if (params?.patient_id) query.set('patient_id', params.patient_id);
    if (params?.prom_id) query.set('prom_id', params.prom_id);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<PROMResponseListResponse>(`/rpm/proms/responses${qs}`, { method: 'GET' });
  },

  scheduleTelehealthSession: async (data: {
    patient_id: string;
    scheduled_start: string;
    visit_reason: string;
    appointment_id?: number;
    encounter_id?: number;
  }): Promise<TelehealthSession> => {
    return apiRequest<TelehealthSession>('/rpm/telehealth/sessions', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listTelehealthSessions: async (params?: {
    patient_id?: string;
    status?: string;
  }): Promise<TelehealthSessionListResponse> => {
    const query = new URLSearchParams();
    if (params?.patient_id) query.set('patient_id', params.patient_id);
    if (params?.status) query.set('status', params.status);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<TelehealthSessionListResponse>(`/rpm/telehealth/sessions${qs}`, { method: 'GET' });
  },

  getTelehealthSession: async (sessionId: string): Promise<TelehealthSession> => {
    return apiRequest<TelehealthSession>(`/rpm/telehealth/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'GET',
    });
  },

  updateTelehealthSession: async (
    sessionId: string,
    data: {
      status?: TelehealthStatus;
      session_notes?: string;
      followup_instructions?: string;
      create_followup_task?: boolean;
    }
  ): Promise<TelehealthSession> => {
    return apiRequest<TelehealthSession>(`/rpm/telehealth/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  enqueueObservationProcessing: async (patientId?: string): Promise<BackgroundTask> => {
    const qs = patientId ? `?patient_id=${encodeURIComponent(patientId)}` : '';
    return apiRequest<BackgroundTask>(`/rpm/tasks/observations/process${qs}`, { method: 'POST' });
  },
};

// ==============================================================================
// PHASE 9.0.16: CLINICAL TRIALS & PRECISION ONCOLOGY API CLIENT
// ==============================================================================

export const trialsApi = {
  listTrials: async (params?: {
    phase?: TrialPhase;
    status?: TrialStatus;
    condition?: string;
    search?: string;
    is_active?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<ClinicalTrialListResponse> => {
    const query = new URLSearchParams();
    if (params?.phase) query.set('phase', params.phase);
    if (params?.status) query.set('status', params.status);
    if (params?.condition) query.set('condition', params.condition);
    if (params?.search) query.set('search', params.search);
    if (params?.is_active !== undefined) query.set('is_active', String(params.is_active));
    if (params?.skip !== undefined) query.set('skip', String(params.skip));
    if (params?.limit !== undefined) query.set('limit', String(params.limit));
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<ClinicalTrialListResponse>(`/trials${qs}`, { method: 'GET' });
  },

  getTrial: async (trialId: string): Promise<ClinicalTrialDetail> => {
    return apiRequest<ClinicalTrialDetail>(`/trials/${encodeURIComponent(trialId)}`, { method: 'GET' });
  },

  createTrial: async (data: Partial<ClinicalTrial>): Promise<ClinicalTrial> => {
    return apiRequest<ClinicalTrial>('/trials', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  updateTrial: async (trialId: string, data: Partial<ClinicalTrial>): Promise<ClinicalTrial> => {
    return apiRequest<ClinicalTrial>(`/trials/${encodeURIComponent(trialId)}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  },

  addTrialCriterion: async (trialId: string, data: Partial<TrialEligibilityCriterion>): Promise<TrialEligibilityCriterion> => {
    return apiRequest<TrialEligibilityCriterion>(`/trials/${encodeURIComponent(trialId)}/criteria`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listTrialCriteria: async (trialId: string): Promise<TrialEligibilityCriterion[]> => {
    return apiRequest<TrialEligibilityCriterion[]>(`/trials/${encodeURIComponent(trialId)}/criteria`, { method: 'GET' });
  },

  listPatientGenomicProfiles: async (patientId: string): Promise<GenomicProfileListResponse> => {
    return apiRequest<GenomicProfileListResponse>(`/patients/${encodeURIComponent(patientId)}/genomic-profiles`, {
      method: 'GET',
    });
  },

  getGenomicProfile: async (profileId: string): Promise<GenomicProfileDetail> => {
    return apiRequest<GenomicProfileDetail>(`/genomic-profiles/${encodeURIComponent(profileId)}`, { method: 'GET' });
  },

  createGenomicProfile: async (patientId: string, data: any): Promise<GenomicProfile> => {
    return apiRequest<GenomicProfile>(`/patients/${encodeURIComponent(patientId)}/genomic-profiles`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  addBiomarkerObservation: async (profileId: string, data: Partial<BiomarkerObservation>): Promise<BiomarkerObservation> => {
    return apiRequest<BiomarkerObservation>(`/genomic-profiles/${encodeURIComponent(profileId)}/biomarkers`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listBiomarkers: async (profileId: string): Promise<BiomarkerObservation[]> => {
    return apiRequest<BiomarkerObservation[]>(`/genomic-profiles/${encodeURIComponent(profileId)}/biomarkers`, {
      method: 'GET',
    });
  },

  matchPatientToTrial: async (trialId: string, patientId: string): Promise<TrialMatch> => {
    return apiRequest<TrialMatch>(`/trials/${encodeURIComponent(trialId)}/match/${encodeURIComponent(patientId)}`, {
      method: 'POST',
    });
  },

  batchMatchPatient: async (patientId: string, trialIds?: string[]): Promise<BatchMatchResponse> => {
    return apiRequest<BatchMatchResponse>(`/patients/${encodeURIComponent(patientId)}/trial-matches`, {
      method: 'POST',
      body: JSON.stringify(trialIds ? { trial_ids: trialIds } : {}),
    });
  },

  listPatientTrialMatches: async (
    patientId: string,
    params?: { match_status?: MatchStatus; review_status?: ClinicianReviewStatus }
  ): Promise<TrialMatchListResponse> => {
    const query = new URLSearchParams();
    if (params?.match_status) query.set('match_status', params.match_status);
    if (params?.review_status) query.set('review_status', params.review_status);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<TrialMatchListResponse>(`/patients/${encodeURIComponent(patientId)}/trial-matches${qs}`, {
      method: 'GET',
    });
  },

  reviewTrialMatch: async (
    matchId: string,
    data: { clinician_review_status: ClinicianReviewStatus; review_notes?: string }
  ): Promise<TrialMatch> => {
    return apiRequest<TrialMatch>(`/trial-matches/${encodeURIComponent(matchId)}/review`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  evaluatePrecisionEligibility: async (patientId: string): Promise<PrecisionTreatmentEligibilityListResponse> => {
    return apiRequest<PrecisionTreatmentEligibilityListResponse>(
      `/patients/${encodeURIComponent(patientId)}/precision-eligibility/evaluate`,
      { method: 'POST' }
    );
  },

  listPatientPrecisionEligibility: async (patientId: string): Promise<PrecisionTreatmentEligibilityListResponse> => {
    return apiRequest<PrecisionTreatmentEligibilityListResponse>(
      `/patients/${encodeURIComponent(patientId)}/precision-eligibility`,
      { method: 'GET' }
    );
  },

  reviewPrecisionEligibility: async (
    eligibilityId: string,
    data: { clinician_review_status: ClinicianReviewStatus; review_notes?: string }
  ): Promise<PrecisionTreatmentEligibility> => {
    return apiRequest<PrecisionTreatmentEligibility>(
      `/precision-eligibility/${encodeURIComponent(eligibilityId)}/review`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  enqueueTrialMatchingTask: async (patientId: string): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>(`/tasks/patients/${encodeURIComponent(patientId)}/trial-matching`, {
      method: 'POST',
    });
  },
};

export const agentsApi = {
  listDefinitions: async (): Promise<ClinicalAgentDefinitionListResponse> => {
    return apiRequest<ClinicalAgentDefinitionListResponse>('/agents/definitions', {
      method: 'GET',
    });
  },

  listRuns: async (params?: {
    patient_id?: string;
    status?: AgentRunStatus;
    agent_type?: AgentType;
    skip?: number;
    limit?: number;
  }): Promise<ClinicalAgentRunListResponse> => {
    const query = new URLSearchParams();
    if (params?.patient_id) query.append('patient_id', params.patient_id);
    if (params?.status) query.append('status', params.status);
    if (params?.agent_type) query.append('agent_type', params.agent_type);
    if (params?.skip !== undefined) query.append('skip', params.skip.toString());
    if (params?.limit !== undefined) query.append('limit', params.limit.toString());
    const qs = query.toString() ? `?${query.toString()}` : '';
    return apiRequest<ClinicalAgentRunListResponse>(`/agents/runs${qs}`, {
      method: 'GET',
    });
  },

  getRun: async (runId: string): Promise<ClinicalAgentRunDetail> => {
    return apiRequest<ClinicalAgentRunDetail>(`/agents/runs/${encodeURIComponent(runId)}`, {
      method: 'GET',
    });
  },

  triggerRun: async (data: {
    patient_id: string;
    agent_type: AgentType;
    include_subagents?: AgentType[];
  }): Promise<ClinicalAgentRunDetail> => {
    return apiRequest<ClinicalAgentRunDetail>('/agents/runs', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  executeRun: async (runId: string): Promise<ClinicalAgentRunDetail> => {
    return apiRequest<ClinicalAgentRunDetail>(`/agents/runs/${encodeURIComponent(runId)}/execute`, {
      method: 'POST',
    });
  },

  approveRecommendation: async (
    recommendationId: string,
    data?: { review_notes?: string }
  ): Promise<ClinicalAgentRecommendation> => {
    return apiRequest<ClinicalAgentRecommendation>(
      `/agents/recommendations/${encodeURIComponent(recommendationId)}/approve`,
      {
        method: 'POST',
        body: JSON.stringify({ approval_status: 'approved', review_notes: data?.review_notes }),
      }
    );
  },

  rejectRecommendation: async (
    recommendationId: string,
    data?: { review_notes?: string }
  ): Promise<ClinicalAgentRecommendation> => {
    return apiRequest<ClinicalAgentRecommendation>(
      `/agents/recommendations/${encodeURIComponent(recommendationId)}/reject`,
      {
        method: 'POST',
        body: JSON.stringify({ approval_status: 'rejected', review_notes: data?.review_notes }),
      }
    );
  },

  getPatientCareCoordination: async (patientId: string): Promise<CareCoordinationSynthesisResponse> => {
    return apiRequest<CareCoordinationSynthesisResponse>(
      `/agents/patients/${encodeURIComponent(patientId)}/care-coordination`,
      { method: 'GET' }
    );
  },

  synthesizePatientCareCoordination: async (patientId: string): Promise<CareCoordinationSynthesisResponse> => {
    return apiRequest<CareCoordinationSynthesisResponse>(
      `/agents/patients/${encodeURIComponent(patientId)}/care-coordination/synthesize`,
      { method: 'POST' }
    );
  },

  enqueueCareCoordinationTask: async (patientId: string): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>(
      `/agents/tasks/patients/${encodeURIComponent(patientId)}/care-coordination`,
      { method: 'POST' }
    );
  },
};

// 19. Medical Imaging AI & Radiology Workflow APIs
export const imagingApi = {
  listStudies: async (
    patientId?: string,
    modality?: string,
    status?: string,
    skip: number = 0,
    limit: number = 100
  ): Promise<{ items: ImagingStudy[]; total: number }> => {
    const params = new URLSearchParams();
    if (patientId) params.append('patient_id', patientId);
    if (modality) params.append('modality', modality);
    if (status) params.append('status', status);
    params.append('skip', String(skip));
    params.append('limit', String(limit));

    const endpoint = patientId
      ? `/patients/${encodeURIComponent(patientId)}/imaging/studies?${params.toString()}`
      : `/imaging/studies?${params.toString()}`;

    return apiRequest<{ items: ImagingStudy[]; total: number }>(endpoint, { method: 'GET' });
  },

  getStudy: async (studyId: string): Promise<ImagingStudy> => {
    return apiRequest<ImagingStudy>(`/imaging/studies/${encodeURIComponent(studyId)}`, { method: 'GET' });
  },

  createStudy: async (
    patientId: string,
    data: {
      modality: string;
      body_site: string;
      study_description: string;
      accession_number?: string;
      performing_department?: string;
      referring_provider?: string;
      status?: string;
      source?: string;
    }
  ): Promise<ImagingStudy> => {
    return apiRequest<ImagingStudy>(
      `/patients/${encodeURIComponent(patientId)}/imaging/studies`,
      {
        method: 'POST',
        body: JSON.stringify({ patient_id: patientId, ...data }),
      }
    );
  },

  addAsset: async (
    studyId: string,
    data: {
      series_instance_uid?: string;
      sop_instance_uid?: string;
      series_number?: number;
      instance_number?: number;
      series_description?: string;
      modality?: string;
      body_site?: string;
      mime_type?: string;
      file_size_bytes?: number;
      storage_path: string;
      thumbnail_storage_path?: string;
    }
  ): Promise<ImagingAsset> => {
    return apiRequest<ImagingAsset>(
      `/imaging/studies/${encodeURIComponent(studyId)}/assets`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  listAssets: async (studyId: string): Promise<{ items: ImagingAsset[]; total: number }> => {
    return apiRequest<{ items: ImagingAsset[]; total: number }>(
      `/imaging/studies/${encodeURIComponent(studyId)}/assets`,
      { method: 'GET' }
    );
  },

  analyzeStudy: async (studyId: string): Promise<ImagingAnalysisResponse> => {
    return apiRequest<ImagingAnalysisResponse>(
      `/imaging/studies/${encodeURIComponent(studyId)}/analyze`,
      { method: 'POST' }
    );
  },

  listFindings: async (studyId: string): Promise<{ items: ImagingFinding[]; total: number }> => {
    return apiRequest<{ items: ImagingFinding[]; total: number }>(
      `/imaging/studies/${encodeURIComponent(studyId)}/findings`,
      { method: 'GET' }
    );
  },

  reviewFinding: async (
    findingId: string,
    reviewStatus: string,
    reviewNotes?: string
  ): Promise<ImagingFinding> => {
    return apiRequest<ImagingFinding>(
      `/imaging/findings/${encodeURIComponent(findingId)}/review`,
      {
        method: 'POST',
        body: JSON.stringify({ review_status: reviewStatus, review_notes: reviewNotes }),
      }
    );
  },

  getReport: async (reportId: string): Promise<RadiologyReport> => {
    return apiRequest<RadiologyReport>(`/imaging/reports/${encodeURIComponent(reportId)}`, { method: 'GET' });
  },

  updateReport: async (
    reportId: string,
    data: {
      clinical_indication?: string;
      technique?: string;
      comparison_studies?: string;
      findings?: string;
      impression?: string;
      recommendations?: string;
      critical_findings_summary?: string;
      is_critical?: boolean;
    }
  ): Promise<RadiologyReport> => {
    return apiRequest<RadiologyReport>(
      `/imaging/reports/${encodeURIComponent(reportId)}`,
      {
        method: 'PUT',
        body: JSON.stringify(data),
      }
    );
  },

  submitReportReview: async (reportId: string): Promise<RadiologyReport> => {
    return apiRequest<RadiologyReport>(
      `/imaging/reports/${encodeURIComponent(reportId)}/submit-review`,
      { method: 'POST' }
    );
  },

  finalizeReport: async (
    reportId: string,
    signatureNotes?: string
  ): Promise<RadiologyReport> => {
    return apiRequest<RadiologyReport>(
      `/imaging/reports/${encodeURIComponent(reportId)}/finalize`,
      {
        method: 'POST',
        body: JSON.stringify({ signature_notes: signatureNotes, confirm_accuracy: true }),
      }
    );
  },

  amendReport: async (
    reportId: string,
    amendmentReason: string,
    amendedImpression?: string,
    amendedFindings?: string,
    amendedRecommendations?: string
  ): Promise<RadiologyReport> => {
    return apiRequest<RadiologyReport>(
      `/imaging/reports/${encodeURIComponent(reportId)}/amend`,
      {
        method: 'POST',
        body: JSON.stringify({
          amendment_reason: amendmentReason,
          amended_impression: amendedImpression,
          amended_findings: amendedFindings,
          amended_recommendations: amendedRecommendations,
        }),
      }
    );
  },

  getTimeline: async (patientId: string): Promise<ImagingTimelineResponse> => {
    return apiRequest<ImagingTimelineResponse>(
      `/patients/${encodeURIComponent(patientId)}/imaging/timeline`,
      { method: 'GET' }
    );
  },

  enqueueAnalysisTask: async (studyId: string): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>(
      `/imaging/tasks/studies/${encodeURIComponent(studyId)}/analyze`,
      { method: 'POST' }
    );
  },
};

// FHIR R4 Interoperability Export API
export const fhirApi = {
  getCapabilityStatement: async (): Promise<FHIRCapabilityStatement> => {
    return apiRequest<FHIRCapabilityStatement>('/fhir/metadata');
  },

  exportPatientBundle: async (patientId: string): Promise<any> => {
    return apiRequest<any>(`/fhir/patients/${encodeURIComponent(patientId)}/bundle`);
  },

  importBundle: async (bundlePayload: any): Promise<any> => {
    return apiRequest<any>('/fhir/Bundle', {
      method: 'POST',
      body: JSON.stringify(bundlePayload),
    });
  },

  exportAgentTask: async (recommendationId: string): Promise<any> => {
    return apiRequest<any>(`/fhir/AgentTask/${encodeURIComponent(recommendationId)}`, { method: 'GET' });
  },

  exportAgentProvenance: async (runId: string): Promise<any> => {
    return apiRequest<any>(`/fhir/Provenance/${encodeURIComponent(runId)}`, { method: 'GET' });
  },

  exportImagingStudy: async (studyId: string): Promise<any> => {
    return apiRequest<any>(`/fhir/ImagingStudy/${encodeURIComponent(studyId)}`, { method: 'GET' });
  },

  exportRadiologyReport: async (reportId: string): Promise<any> => {
    return apiRequest<any>(`/fhir/ImagingReport/${encodeURIComponent(reportId)}`, { method: 'GET' });
  },

  exportImagingObservation: async (findingId: string): Promise<any> => {
    return apiRequest<any>(`/fhir/ImagingObservation/${encodeURIComponent(findingId)}`, { method: 'GET' });
  },

  exportConsent: async (consentId: string): Promise<any> => {
    return apiRequest<any>(`/fhir/Consent/${encodeURIComponent(consentId)}`, { method: 'GET' });
  },

  exportAuditEvent: async (eventId: string): Promise<any> => {
    return apiRequest<any>(`/fhir/AuditEvent/${encodeURIComponent(eventId)}`, { method: 'GET' });
  },

  exportPatientConsentsBundle: async (patientId: string): Promise<any> => {
    return apiRequest<any>(`/fhir/patients/${encodeURIComponent(patientId)}/consents`, { method: 'GET' });
  },
};

// 19. Clinical Security, Auditability, Consent & Compliance Governance API
export const securityApi = {
  getAuditEvents: async (params?: {
    patient_id?: string;
    user_id?: number;
    action?: string;
    resource_type?: string;
    outcome?: string;
    from_date?: string;
    to_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<AuditEventListResponse> => {
    const query = new URLSearchParams();
    if (params?.patient_id) query.append('patient_id', params.patient_id);
    if (params?.user_id) query.append('user_id', String(params.user_id));
    if (params?.action) query.append('action', params.action);
    if (params?.resource_type) query.append('resource_type', params.resource_type);
    if (params?.outcome) query.append('outcome', params.outcome);
    if (params?.from_date) query.append('from_date', params.from_date);
    if (params?.to_date) query.append('to_date', params.to_date);
    if (params?.page) query.append('page', String(params.page));
    if (params?.page_size) query.append('page_size', String(params.page_size));

    const queryString = query.toString();
    return apiRequest<AuditEventListResponse>(`/audit/events${queryString ? `?${queryString}` : ''}`, {
      method: 'GET',
    });
  },

  getAuditEvent: async (eventId: string): Promise<ClinicalAuditEvent> => {
    return apiRequest<ClinicalAuditEvent>(`/audit/events/${encodeURIComponent(eventId)}`, {
      method: 'GET',
    });
  },

  verifyAuditIntegrity: async (): Promise<AuditIntegrityVerificationResponse> => {
    return apiRequest<AuditIntegrityVerificationResponse>('/audit/verify-integrity', {
      method: 'POST',
    });
  },

  getPatientConsents: async (patientId: string, status?: string): Promise<PatientConsent[]> => {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    return apiRequest<PatientConsent[]>(`/patients/${encodeURIComponent(patientId)}/consents${query}`, {
      method: 'GET',
    });
  },

  getConsent: async (consentId: string): Promise<PatientConsent> => {
    return apiRequest<PatientConsent>(`/consents/${encodeURIComponent(consentId)}`, {
      method: 'GET',
    });
  },

  grantConsent: async (
    patientId: string,
    payload: PatientConsentCreateRequest
  ): Promise<PatientConsent> => {
    return apiRequest<PatientConsent>(`/patients/${encodeURIComponent(patientId)}/consents`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  revokeConsent: async (
    consentId: string,
    payload: PatientConsentRevokeRequest
  ): Promise<PatientConsent> => {
    return apiRequest<PatientConsent>(`/consents/${encodeURIComponent(consentId)}/revoke`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  verifyConsent: async (payload: ConsentVerificationRequest): Promise<ConsentVerificationResponse> => {
    return apiRequest<ConsentVerificationResponse>('/consents/verify', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listIncidents: async (
    status?: string,
    severity?: string,
    page = 1,
    pageSize = 50
  ): Promise<SecurityIncident[]> => {
    const query = new URLSearchParams();
    if (status) query.append('status', status);
    if (severity) query.append('severity', severity);
    query.append('page', String(page));
    query.append('page_size', String(pageSize));
    return apiRequest<SecurityIncident[]>(`/security/incidents?${query.toString()}`, {
      method: 'GET',
    });
  },

  getIncident: async (incidentId: string): Promise<SecurityIncident> => {
    return apiRequest<SecurityIncident>(`/security/incidents/${encodeURIComponent(incidentId)}`, {
      method: 'GET',
    });
  },

  createIncident: async (payload: SecurityIncidentCreateRequest): Promise<SecurityIncident> => {
    return apiRequest<SecurityIncident>('/security/incidents', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateIncident: async (
    incidentId: string,
    payload: SecurityIncidentUpdateRequest
  ): Promise<SecurityIncident> => {
    return apiRequest<SecurityIncident>(`/security/incidents/${encodeURIComponent(incidentId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  runSecurityScan: async (lookbackMinutes = 60): Promise<SecurityScanResult> => {
    return apiRequest<SecurityScanResult>(`/security/scan?lookback_minutes=${lookbackMinutes}`, {
      method: 'POST',
    });
  },

  getComplianceSummary: async (): Promise<ComplianceSummaryResponse> => {
    return apiRequest<ComplianceSummaryResponse>('/security/compliance/summary', {
      method: 'GET',
    });
  },

  getRetentionPolicies: async (): Promise<DataRetentionPolicy[]> => {
    return apiRequest<DataRetentionPolicy[]>('/security/retention/policies', {
      method: 'GET',
    });
  },

  createRetentionPolicy: async (
    payload: DataRetentionPolicyCreateRequest
  ): Promise<DataRetentionPolicy> => {
    return apiRequest<DataRetentionPolicy>('/security/retention/policies', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  listLegalHolds: async (status?: string, patientId?: string): Promise<LegalClinicalHold[]> => {
    const query = new URLSearchParams();
    if (status) query.append('status', status);
    if (patientId) query.append('patient_id', patientId);
    const queryString = query.toString();
    return apiRequest<LegalClinicalHold[]>(`/security/holds${queryString ? `?${queryString}` : ''}`, {
      method: 'GET',
    });
  },

  placeLegalHold: async (payload: LegalClinicalHoldCreateRequest): Promise<LegalClinicalHold> => {
    return apiRequest<LegalClinicalHold>('/security/holds', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  releaseLegalHold: async (
    holdId: string,
    payload: LegalClinicalHoldReleaseRequest
  ): Promise<LegalClinicalHold> => {
    return apiRequest<LegalClinicalHold>(`/security/holds/${encodeURIComponent(holdId)}/release`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  enqueueAuditIntegrityTask: async (): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>('/tasks/security/audit-integrity', {
      method: 'POST',
    });
  },

  enqueueAnomalyScanTask: async (lookbackMinutes = 60): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>(
      `/tasks/security/anomaly-scan?lookback_minutes=${lookbackMinutes}`,
      { method: 'POST' }
    );
  },

  enqueueComplianceReportTask: async (): Promise<BackgroundTask> => {
    return apiRequest<BackgroundTask>('/tasks/security/compliance-report', {
      method: 'POST',
    });
  },
};

// 21. Infrastructure, Health & System Diagnostics APIs (Phase 9.0.20)
export const systemApi = {
  getLiveness: async (): Promise<SystemLivenessResponse> => {
    return apiRequest<SystemLivenessResponse>('/health/live');
  },

  getReadiness: async (): Promise<SystemReadinessResponse> => {
    return apiRequest<SystemReadinessResponse>('/health/ready');
  },

  getMetrics: async (): Promise<SystemMetricsResponse> => {
    return apiRequest<SystemMetricsResponse>('/health/metrics');
  },

  getPrometheusMetricsText: async (): Promise<string> => {
    const token = getStoredToken();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch('/api/v1/health/metrics/prometheus', { headers });
    return res.text();
  },
};

// 22. SMART on FHIR 2.0 APIs (Phase 9.0.21)
export const smartApi = {
  getSmartConfig: async (): Promise<SmartConfiguration> => {
    const res = await fetch('/.well-known/smart-configuration');
    return res.json();
  },

  getJwks: async (): Promise<JWKSResponse> => {
    const res = await fetch('/.well-known/jwks.json');
    return res.json();
  },

  authorize: async (params: Record<string, string>): Promise<{ code: string; state?: string }> => {
    const qs = new URLSearchParams(params).toString();
    return apiRequest<{ code: string; state?: string }>(`/smart/authorize?${qs}`);
  },

  exchangeToken: async (params: {
    grant_type: string;
    code: string;
    redirect_uri: string;
    client_id: string;
    code_verifier?: string;
  }): Promise<SmartTokenResponse> => {
    const form = new URLSearchParams();
    form.append('grant_type', params.grant_type);
    form.append('code', params.code);
    form.append('redirect_uri', params.redirect_uri);
    form.append('client_id', params.client_id);
    if (params.code_verifier) form.append('code_verifier', params.code_verifier);

    const res = await fetch('/api/v1/smart/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form.toString(),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Token exchange failed' }));
      throw new Error(err.detail || 'Token exchange failed');
    }
    return res.json();
  },

  introspectToken: async (token: string): Promise<SmartIntrospectResponse> => {
    return apiRequest<SmartIntrospectResponse>('/smart/introspect', {
      method: 'POST',
      body: JSON.stringify({ token }),
    });
  },
};

// 23. CDS Hooks 2.0 APIs (Phase 9.0.21)
export const cdsApi = {
  discoverServices: async (): Promise<CDSServicesDiscoveryResponse> => {
    const res = await fetch('/cds-services');
    return res.json();
  },

  invokePatientView: async (patientId: string, userId = 'Practitioner/doc-01'): Promise<CDSHookResponse> => {
    const res = await fetch('/cds-services/patient-view', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hook: 'patient-view',
        hookInstance: `inst-${Date.now()}`,
        context: { userId, patientId },
      }),
    });
    return res.json();
  },

  invokeOrderSelect: async (
    patientId: string,
    selections: string[],
    userId = 'Practitioner/doc-01'
  ): Promise<CDSHookResponse> => {
    const res = await fetch('/cds-services/order-select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        hook: 'order-select',
        hookInstance: `inst-${Date.now()}`,
        context: { userId, patientId, selections },
      }),
    });
    return res.json();
  },
};

// 24. Multi-Tenant Health Systems & Facility APIs (Phase 9.0.21)
export const tenantApi = {
  listOrganizations: async (): Promise<HealthOrganization[]> => {
    return apiRequest<HealthOrganization[]>('/tenants/organizations');
  },

  createOrganization: async (data: { name: string; org_type?: string }): Promise<HealthOrganization> => {
    return apiRequest<HealthOrganization>('/tenants/organizations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listFacilities: async (orgId?: string): Promise<ClinicalFacility[]> => {
    const query = orgId ? `?org_id=${encodeURIComponent(orgId)}` : '';
    return apiRequest<ClinicalFacility[]>(`/tenants/facilities${query}`);
  },

  createFacility: async (data: {
    org_id: string;
    name: string;
    facility_code: string;
    address_json?: Record<string, any>;
  }): Promise<ClinicalFacility> => {
    return apiRequest<ClinicalFacility>('/tenants/facilities', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listDepartments: async (facilityId: string): Promise<DepartmentUnit[]> => {
    return apiRequest<DepartmentUnit[]>(`/tenants/facilities/${encodeURIComponent(facilityId)}/departments`);
  },

  createDepartment: async (data: {
    facility_id: string;
    name: string;
    dept_code: string;
    floor_or_wing?: string;
  }): Promise<DepartmentUnit> => {
    return apiRequest<DepartmentUnit>('/tenants/departments', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getEHRConfig: async (facilityId: string): Promise<EHRIntegrationConfig | null> => {
    return apiRequest<EHRIntegrationConfig | null>(
      `/tenants/facilities/${encodeURIComponent(facilityId)}/ehr-config`
    );
  },

  configureEHR: async (data: {
    facility_id: string;
    ehr_vendor: string;
    fhir_base_url: string;
    client_id: string;
    smart_auth_url?: string;
    smart_token_url?: string;
  }): Promise<EHRIntegrationConfig> => {
    return apiRequest<EHRIntegrationConfig>('/tenants/ehr-config', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};

// 25. Clinical Terminology Normalization APIs (Phase 9.0.21)
export const terminologyApi = {
  normalizeConcept: async (query: string, targetSystem?: string): Promise<TerminologyNormalizeResponse> => {
    return apiRequest<TerminologyNormalizeResponse>('/terminology/normalize', {
      method: 'POST',
      body: JSON.stringify({ query, target_system: targetSystem }),
    });
  },

  crosswalkCode: async (
    sourceSystem: string,
    sourceCode: string,
    targetSystem: string
  ): Promise<TerminologyCrossWalkResponse> => {
    return apiRequest<TerminologyCrossWalkResponse>('/terminology/crosswalk', {
      method: 'POST',
      body: JSON.stringify({
        source_system: sourceSystem,
        source_code: sourceCode,
        target_system: targetSystem,
      }),
    });
  },
};

// 26. Real-Time Telemetry & Telehealth WebSocket Helpers (Phase 9.0.21)
export const telehealthApi = {
  getIceServers: async (): Promise<{ iceServers: Array<{ urls: string }> }> => {
    return apiRequest<{ iceServers: Array<{ urls: string }> }>('/telehealth/ice-servers');
  },

  getWebSocketStats: async (): Promise<WebSocketStats> => {
    return apiRequest<WebSocketStats>('/ws/stats');
  },

  broadcastTelemetry: async (patientId: string, frame: Record<string, any>): Promise<{ status: string }> => {
    return apiRequest<{ status: string }>(`/telemetry/${encodeURIComponent(patientId)}/broadcast`, {
      method: 'POST',
      body: JSON.stringify(frame),
    });
  },
};

// 27. Transactional Outbox & Reliability APIs (Phase 9.0.22)
export const outboxApi = {
  listEvents: async (status?: string, limit = 50, offset = 0): Promise<OutboxEvent[]> => {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    params.append('limit', String(limit));
    params.append('offset', String(offset));
    return apiRequest<OutboxEvent[]>(`/outbox/events?${params.toString()}`);
  },

  replayDeadLetters: async (eventIds?: string[], limit = 50): Promise<{ replayed_count: number; message: string }> => {
    return apiRequest<{ replayed_count: number; message: string }>('/outbox/replay', {
      method: 'POST',
      body: JSON.stringify({ event_ids: eventIds, limit }),
    });
  },

  getMetrics: async (): Promise<OutboxMetrics> => {
    return apiRequest<OutboxMetrics>('/outbox/metrics');
  },
};

// 28. Multi-Factor Authentication (TOTP / MFA) APIs (Phase 9.0.22)
export const mfaApi = {
  setup: async (): Promise<MFASetupResponse> => {
    return apiRequest<MFASetupResponse>('/auth/mfa/setup', {
      method: 'POST',
    });
  },

  enable: async (code: string): Promise<MFAVerifyResponse> => {
    return apiRequest<MFAVerifyResponse>('/auth/mfa/enable', {
      method: 'POST',
      body: JSON.stringify({ code }),
    });
  },

  verify: async (code: string): Promise<MFAVerifyResponse> => {
    return apiRequest<MFAVerifyResponse>('/auth/mfa/verify', {
      method: 'POST',
      body: JSON.stringify({ code }),
    });
  },

  disable: async (code: string): Promise<MFAVerifyResponse> => {
    return apiRequest<MFAVerifyResponse>('/auth/mfa/disable', {
      method: 'POST',
      body: JSON.stringify({ code }),
    });
  },

  getStatus: async (): Promise<MFAStatusResponse> => {
    return apiRequest<MFAStatusResponse>('/auth/mfa/status');
  },
};

// 29. FHIR R4 Topic-Based Subscriptions APIs (Phase 9.0.22)
export const fhirSubscriptionsApi = {
  createSubscription: async (data: {
    topic: string;
    criteria: string;
    channel_type: 'REST_HOOK' | 'WEBSOCKET' | 'EMAIL';
    endpoint_url: string;
    secret_token?: string;
  }): Promise<FHIRSubscription> => {
    return apiRequest<FHIRSubscription>('/fhir/Subscription', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listSubscriptions: async (topic?: string, status?: string): Promise<FHIRSubscription[]> => {
    const params = new URLSearchParams();
    if (topic) params.append('topic', topic);
    if (status) params.append('status', status);
    const qs = params.toString();
    return apiRequest<FHIRSubscription[]>(`/fhir/Subscription${qs ? `?${qs}` : ''}`);
  },

  deleteSubscription: async (subscriptionId: string): Promise<{ success: boolean; message: string }> => {
    return apiRequest<{ success: boolean; message: string }>(`/fhir/Subscription/${encodeURIComponent(subscriptionId)}`, {
      method: 'DELETE',
    });
  },
};

// 30. FHIR Bulk Data Export ($export) APIs (Phase 9.0.22)
export const bulkExportApi = {
  kickoffExport: async (resourceTypes?: string[]): Promise<{ job_id: string; status: string; poll_url: string }> => {
    const params = new URLSearchParams();
    if (resourceTypes && resourceTypes.length > 0) {
      params.append('_type', resourceTypes.join(','));
    }
    const qs = params.toString();
    return apiRequest<{ job_id: string; status: string; poll_url: string }>(
      `/fhir/Patient/$export${qs ? `?${qs}` : ''}`,
      {
        method: 'POST',
        headers: { Prefer: 'respond-async' },
      }
    );
  },

  getExportStatus: async (jobId: string): Promise<BulkExportJob> => {
    return apiRequest<BulkExportJob>(`/fhir/bulk-export/${encodeURIComponent(jobId)}/status`);
  },
};

// =============================================================================
// 31. Phase 9.0.25: Enterprise Master Patient Index (EMPI) APIs
// =============================================================================
export const empiApi = {
  findCandidateMatches: async (patientId: string, threshold = 0.65): Promise<EMPICandidatesResponse> => {
    return apiRequest<EMPICandidatesResponse>(
      `/empi/match/candidates/${encodeURIComponent(patientId)}?threshold=${threshold}`
    );
  },

  linkPatient: async (data: {
    target_patient_id: string;
    patient_id: string;
    link_type?: string;
  }): Promise<EMPILinkResponse> => {
    return apiRequest<EMPILinkResponse>('/empi/link', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  unlinkPatient: async (patientId: string, reason?: string): Promise<{ success: boolean; message: string }> => {
    return apiRequest<{ success: boolean; message: string }>(
      `/empi/unlink/${encodeURIComponent(patientId)}${reason ? `?reason=${encodeURIComponent(reason)}` : ''}`,
      { method: 'POST' }
    );
  },

  mergeIdentities: async (data: {
    target_patient_id: string;
    source_patient_id: string;
    reason: string;
  }): Promise<EMPIMergeResponse> => {
    return apiRequest<EMPIMergeResponse>('/empi/merge', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  splitIdentity: async (mergeId: string, reason?: string): Promise<{ success: boolean; message: string }> => {
    return apiRequest<{ success: boolean; message: string }>(
      `/empi/split/${encodeURIComponent(mergeId)}${reason ? `?reason=${encodeURIComponent(reason)}` : ''}`,
      { method: 'POST' }
    );
  },

  listReviews: async (status?: string): Promise<EMPIMatchReviewItem[]> => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : '';
    return apiRequest<EMPIMatchReviewItem[]>(`/empi/reviews${qs}`);
  },

  resolveReview: async (
    reviewId: string,
    action: 'confirm_link' | 'reject_match',
    notes?: string
  ): Promise<{ success: boolean; message: string }> => {
    return apiRequest<{ success: boolean; message: string }>(`/empi/reviews/${encodeURIComponent(reviewId)}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ action, notes }),
    });
  },
};

// =============================================================================
// 32. Phase 9.0.25: Regional Cross-Hospital C-CDA Exchange APIs
// =============================================================================
export const ccdaApi = {
  exportDocument: async (
    patientId: string,
    documentType = 'continuity_of_care_document'
  ): Promise<CCDAExportResponse> => {
    return apiRequest<CCDAExportResponse>('/ccda/export', {
      method: 'POST',
      body: JSON.stringify({ patient_id: patientId, document_type: documentType }),
    });
  },

  downloadRawXmlUrl: (patientId: string, documentType = 'continuity_of_care_document') => {
    return `/api/v1/ccda/export/${encodeURIComponent(patientId)}/xml?document_type=${encodeURIComponent(documentType)}`;
  },

  importDocument: async (data: {
    patient_id: string;
    xml_content: string;
    source_facility?: string;
  }): Promise<CCDAImportResponse> => {
    return apiRequest<CCDAImportResponse>('/ccda/import', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listDocuments: async (patientId?: string): Promise<{ total: number; documents: CCDADocumentExchange[] }> => {
    const qs = patientId ? `?patient_id=${encodeURIComponent(patientId)}` : '';
    return apiRequest<{ total: number; documents: CCDADocumentExchange[] }>(`/ccda/documents${qs}`);
  },
};

// =============================================================================
// 33. Phase 9.0.25: Regional Multi-Hospital Clinical Pathways APIs
// =============================================================================
export const pathwaysApi = {
  listPathways: async (): Promise<{ total: number; pathways: RegionalPathway[] }> => {
    return apiRequest<{ total: number; pathways: RegionalPathway[] }>('/pathways');
  },

  getPathway: async (pathwayId: string): Promise<RegionalPathway> => {
    return apiRequest<RegionalPathway>(`/pathways/${encodeURIComponent(pathwayId)}`);
  },

  enrollPatient: async (data: {
    patient_id: string;
    pathway_id: string;
    facility_id?: string;
  }): Promise<PatientPathwayEnrollment> => {
    return apiRequest<PatientPathwayEnrollment>('/pathways/enroll', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  advanceStage: async (
    enrollmentId: string,
    data?: { target_stage_id?: string; variance_reason?: string }
  ): Promise<PatientPathwayEnrollment> => {
    return apiRequest<PatientPathwayEnrollment>(
      `/pathways/enrollments/${encodeURIComponent(enrollmentId)}/advance-stage`,
      {
        method: 'POST',
        body: JSON.stringify(data || {}),
      }
    );
  },

  completeMilestone: async (
    enrollmentId: string,
    milestoneId: string,
    notes?: string
  ): Promise<PatientPathwayEnrollment> => {
    return apiRequest<PatientPathwayEnrollment>(
      `/pathways/enrollments/${encodeURIComponent(enrollmentId)}/milestones/${encodeURIComponent(milestoneId)}/complete`,
      {
        method: 'POST',
        body: JSON.stringify({ milestone_id: milestoneId, notes }),
      }
    );
  },

  getPatientEnrollments: async (patientId: string): Promise<PatientPathwayEnrollment[]> => {
    return apiRequest<PatientPathwayEnrollment[]>(`/pathways/patient/${encodeURIComponent(patientId)}`);
  },
};

// =============================================================================
// 34. Phase 9.0.26: CDS Rules, PGx & Multidisciplinary Order Sets APIs
// =============================================================================
export const cdsPgxApi = {
  listRules: async (filters?: {
    gene_symbol?: string;
    drug_code?: string;
    cpic_level?: string;
    risk_severity?: string;
  }): Promise<{ total: number; rules: PGxRuleDefinition[] }> => {
    const params = new URLSearchParams();
    if (filters?.gene_symbol) params.append('gene_symbol', filters.gene_symbol);
    if (filters?.drug_code) params.append('drug_code', filters.drug_code);
    if (filters?.cpic_level) params.append('cpic_level', filters.cpic_level);
    if (filters?.risk_severity) params.append('risk_severity', filters.risk_severity);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return apiRequest<{ total: number; rules: PGxRuleDefinition[] }>(`/cds-pgx/rules${qs}`);
  },

  listOrderSets: async (filters?: {
    category?: OrderSetCategory;
    facility_id?: string;
  }): Promise<{ total: number; order_sets: ClinicalOrderSet[] }> => {
    const params = new URLSearchParams();
    if (filters?.category) params.append('category', filters.category);
    if (filters?.facility_id) params.append('facility_id', filters.facility_id);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return apiRequest<{ total: number; order_sets: ClinicalOrderSet[] }>(`/cds-pgx/order-sets${qs}`);
  },

  getOrderSet: async (orderSetId: string): Promise<ClinicalOrderSet> => {
    return apiRequest<ClinicalOrderSet>(`/cds-pgx/order-sets/${encodeURIComponent(orderSetId)}`);
  },

  executeOrderSet: async (
    orderSetId: string,
    data: {
      patient_id: string;
      selected_item_ids?: string[];
      notes?: string;
    }
  ): Promise<OrderSetExecuteResponse> => {
    return apiRequest<OrderSetExecuteResponse>(
      `/cds-pgx/order-sets/${encodeURIComponent(orderSetId)}/execute`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  evaluateCDS: async (data: {
    patient_id: string;
    trigger_event?: CDSRuleTriggerEvent;
    proposed_drug_code?: string;
    proposed_drug_name?: string;
  }): Promise<CDSEvaluationResponse> => {
    return apiRequest<CDSEvaluationResponse>('/cds-pgx/evaluate', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  recordOverride: async (data: {
    patient_id: string;
    rule_type: string;
    trigger_event?: CDSRuleTriggerEvent;
    severity: string;
    card_summary: string;
    card_detail: string;
    override_reason: string;
  }): Promise<CDSRuleOverrideResponse> => {
    return apiRequest<CDSRuleOverrideResponse>('/cds-pgx/override', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listAudits: async (patientId?: string): Promise<{ total: number; audits: CDSRuleEvaluationAudit[] }> => {
    const qs = patientId ? `?patient_id=${encodeURIComponent(patientId)}` : '';
    return apiRequest<{ total: number; audits: CDSRuleEvaluationAudit[] }>(`/cds-pgx/audits${qs}`);
  },
};

export const trialsGovernanceApi = {
  getPrescreening: async (patientId: string): Promise<TrialPrescreenEvaluationResponse> => {
    return apiRequest<TrialPrescreenEvaluationResponse>(
      `/trials-governance/prescreen/${encodeURIComponent(patientId)}`
    );
  },

  listSites: async (params?: {
    trial_id?: number;
    facility_id?: string;
  }): Promise<{ total: number; sites: MultiCenterStudySite[] }> => {
    const searchParams = new URLSearchParams();
    if (params?.trial_id) searchParams.append('trial_id', params.trial_id.toString());
    if (params?.facility_id) searchParams.append('facility_id', params.facility_id);
    const qs = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return apiRequest<{ total: number; sites: MultiCenterStudySite[] }>(
      `/trials-governance/sites${qs}`
    );
  },

  createSite: async (data: {
    trial_id: number;
    site_name: string;
    facility_id?: string;
    principal_investigator_user_id?: number;
    target_accrual?: number;
    irb_approval_number?: string;
    irb_approval_date?: string;
    irb_expiry_date?: string;
  }): Promise<MultiCenterStudySite> => {
    return apiRequest<MultiCenterStudySite>('/trials-governance/sites', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  listDeviations: async (params?: {
    trial_id?: number;
    severity?: DeviationSeverity;
    status?: DeviationStatus;
  }): Promise<{ total: number; deviations: TrialProtocolDeviation[] }> => {
    const searchParams = new URLSearchParams();
    if (params?.trial_id) searchParams.append('trial_id', params.trial_id.toString());
    if (params?.severity) searchParams.append('severity', params.severity);
    if (params?.status) searchParams.append('status', params.status);
    const qs = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return apiRequest<{ total: number; deviations: TrialProtocolDeviation[] }>(
      `/trials-governance/deviations${qs}`
    );
  },

  reportDeviation: async (data: {
    trial_id: number;
    site_id?: number;
    patient_id?: string;
    deviation_category: DeviationCategory;
    severity?: DeviationSeverity;
    description: string;
    occurred_at: string;
    discovered_at: string;
    impact_on_patient_safety?: string;
    impact_on_data_integrity?: string;
    requires_irb_submission?: boolean;
  }): Promise<TrialProtocolDeviation> => {
    return apiRequest<TrialProtocolDeviation>('/trials-governance/deviations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  createCAPA: async (
    deviationId: number,
    data: {
      root_cause_category: CAPARootCause;
      root_cause_analysis: string;
      corrective_action: string;
      preventive_action: string;
      assigned_owner_user_id: number;
      target_resolution_date: string;
    }
  ): Promise<TrialCAPARecord> => {
    return apiRequest<TrialCAPARecord>(
      `/trials-governance/deviations/${deviationId}/capa`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  submitIRB: async (
    deviationId: number,
    data: {
      irb_committee_name: string;
      submission_type: IRBSubmissionType;
      custom_remarks?: string;
    }
  ): Promise<TrialIRBNotification> => {
    return apiRequest<TrialIRBNotification>(
      `/trials-governance/deviations/${deviationId}/submit-irb`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    );
  },

  getTrialSummary: async (trialId: number): Promise<MultiCenterTrialGovernanceSummary> => {
    return apiRequest<MultiCenterTrialGovernanceSummary>(
      `/trials-governance/trials/${trialId}/summary`
    );
  },
};
