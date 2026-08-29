// ==============================================================================
// MediGen AI - Frontend Core Type Definitions
// Matching Authoritative FastAPI Pydantic Models & Contracts
// ==============================================================================

export type UserRole = 'admin' | 'doctor' | 'healthcare_staff' | 'patient';

export interface User {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Patient {
  id: number;
  patient_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  phone?: string;
  email?: string;
  address?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  blood_group?: string;
  allergies?: string;
  medical_history?: string;
  is_active: boolean;
  created_at: string;
  updated_at?: string;
}

export interface TimelineCitation {
  document_id: string;
  title: string;
  page_number?: number;
  chunk_id?: string;
  document_type?: string;
}

export interface TimelineEvent {
  event_id: string;
  patient_id: string;
  event_type: 'encounter' | 'document' | 'appointment';
  event_date: string;
  title: string;
  summary: string;
  metadata?: Record<string, any>;
}

export interface TimelineSummary {
  summary: string;
  citations: TimelineCitation[];
  total_events_analyzed: number;
  generated_at?: string;
}

export type SafetySeverity = 'INFO' | 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
export type SafetyAlertType =
  | 'medication_duplicate'
  | 'allergy_warning'
  | 'drug_interaction'
  | 'contraindication'
  | 'dosing_warning';

export interface ClinicalSafetyAlert {
  alert_id: string;
  patient_id: string;
  alert_type: SafetyAlertType;
  severity: SafetySeverity;
  title: string;
  explanation: string;
  medications: string[];
  source_references: string[];
  generated_at: string;
  provider: string;
  requires_clinician_review: boolean;
  citations: TimelineCitation[];
}

export interface ClinicalSafetyReport {
  patient_id: string;
  alerts: ClinicalSafetyAlert[];
  checked_items: number;
  safe_to_proceed: boolean;
  summary: string;
  disclaimer: string;
  generated_at: string;
}

export interface MedicalDocument {
  id: number;
  document_id: string;
  patient_id: number;
  title: string;
  document_type: string;
  file_path: string;
  mime_type: string;
  file_size_bytes: number;
  page_count?: number;
  status: string;
  created_at: string;
}

export interface ChatSession {
  session_id: string;
  patient_id: string;
  title: string;
  is_active: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  message_id: string;
  sender_role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: TimelineCitation[];
  insufficient_information?: boolean;
  created_at: string;
}

export interface ChatSessionDetail {
  session_id: string;
  patient_id: string;
  title: string;
  is_active: boolean;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export type BackgroundTaskStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'retrying'
  | 'cancelled';

export type BackgroundTaskType =
  | 'document_processing'
  | 'timeline_summary'
  | 'safety_check'
  | 'batch_indexing';

export interface BackgroundTask {
  task_id: string;
  task_type: BackgroundTaskType;
  status: BackgroundTaskStatus;
  patient_id?: string;
  progress: number;
  result_metadata: Record<string, any>;
  error_message?: string;
  retry_count: number;
  max_retries: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface TaskListResponse {
  items: BackgroundTask[];
  total: number;
  page: number;
  size: number;
}
