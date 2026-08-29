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

export type MediaModality =
  | 'xray_chest'
  | 'ct_scan'
  | 'mri'
  | 'ultrasound'
  | 'dermatology'
  | 'pathology'
  | 'other';

export type MediaBodySite =
  | 'chest'
  | 'brain'
  | 'abdomen'
  | 'pelvis'
  | 'extremity'
  | 'spine'
  | 'skin'
  | 'whole_body'
  | 'other';

export type MediaStatus =
  | 'uploaded'
  | 'analyzing'
  | 'analyzed'
  | 'reviewed'
  | 'failed';

export interface ImagingFindingItem {
  observation: string;
  anatomical_region: string;
  confidence: number;
  is_abnormal: boolean;
  severity?: string;
}

export interface StructuredImagingFinding {
  modality: MediaModality;
  confidence_score: number;
  primary_observation: string;
  findings: ImagingFindingItem[];
  differential_notes: string[];
  disclaimer: string;
}

export interface DiagnosticMedia {
  id: number;
  media_id: string;
  patient_id: number;
  uploader_user_id?: number;
  encounter_id?: number;
  title: string;
  modality: MediaModality;
  body_site?: MediaBodySite;
  original_filename: string;
  file_size_bytes: number;
  mime_type: string;
  status: MediaStatus;
  confidence_score?: number;
  findings_summary?: string;
  structured_findings?: StructuredImagingFinding;
  anomalies_detected?: ImagingFindingItem[];
  requires_clinician_review: boolean;
  clinician_confirmed: boolean;
  clinician_notes?: string;
  created_at: string;
  analyzed_at?: string;
  reviewed_at?: string;
}

export interface DiagnosticMediaListResponse {
  items: DiagnosticMedia[];
  total: number;
}

export type NoteType =
  | 'soap'
  | 'consultation'
  | 'discharge_summary'
  | 'procedure_note'
  | 'referral_letter';

export type NoteStatus = 'draft' | 'finalized' | 'amended';

export interface SOAPSection {
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}

export interface ClinicalNote {
  id: number;
  note_id: string;
  patient_id: number;
  author_user_id?: number;
  encounter_id?: number;
  title: string;
  note_type: NoteType;
  status: NoteStatus;
  content_json?: Record<string, any>;
  raw_text: string;
  is_ai_generated: boolean;
  requires_clinician_review: boolean;
  signed_by_user_id?: number;
  signed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ClinicalNoteListResponse {
  items: ClinicalNote[];
  total: number;
}

export type VitalSimulationProfile =
  | 'normal'
  | 'hypoxic'
  | 'hypertensive_crisis'
  | 'tachycardic'
  | 'bradycardic';

export interface VitalTelemetry {
  id: number;
  reading_id: string;
  patient_id: number;
  encounter_id?: number;
  heart_rate?: number;
  systolic_bp?: number;
  diastolic_bp?: number;
  respiratory_rate?: number;
  temperature_c?: number;
  spo2_percent?: number;
  weight_kg?: number;
  device_id?: string;
  source: string;
  measured_at: string;
  created_at: string;
}

export interface VitalTelemetryListResponse {
  items: VitalTelemetry[];
  total: number;
}

export type AlertSeverity = 'INFO' | 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
export type AlertStatus = 'active' | 'acknowledged' | 'dismissed' | 'resolved';

export interface ClinicalAlert {
  id: number;
  alert_id: string;
  patient_id: number;
  encounter_id?: number;
  reading_id?: number;
  alert_type: string;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  explanation: string;

  parameters_json?: Record<string, any>;
  recurrence_count: number;
  acknowledged_by_user_id?: number;
  acknowledged_at?: string;
  dismissal_reason?: string;
  last_triggered_at: string;
  created_at: string;
}

export interface ClinicalAlertListResponse {
  items: ClinicalAlert[];
  total: number;
}

export type CarePlanStatus =
  | 'draft'
  | 'reviewed'
  | 'active'
  | 'completed'
  | 'suspended'
  | 'cancelled';

export type CarePlanCategory =
  | 'chronic_disease_management'
  | 'post_discharge_followup'
  | 'preventive_care'
  | 'rehabilitation'
  | 'acute_care_plan';

export interface CarePlanGoal {
  goal_id: string;
  title: string;
  target_metric?: string;
  target_date?: string;
  status: string;
  notes?: string;
}

export interface CarePlanIntervention {
  intervention_id: string;
  description: string;
  category: string;
  responsible_party?: string;
  status: string;
}

export interface CarePlan {
  id: number;
  plan_id: string;
  patient_id: number;
  author_user_id?: number;
  encounter_id?: number;
  title: string;
  category: CarePlanCategory;
  status: CarePlanStatus;
  intent: string;
  description: string;
  goals_json?: CarePlanGoal[];
  interventions_json?: CarePlanIntervention[];
  is_ai_generated: boolean;
  reviewed_by_user_id?: number;
  reviewed_at?: string;
  start_date: string;
  end_date?: string;
  created_at: string;
  updated_at: string;
}

export interface CarePlanListResponse {
  items: CarePlan[];
  total: number;
}

export type TaskPriority = 'LOW' | 'ROUTINE' | 'URGENT' | 'STAT';
export type CareTaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled';
export type CareTaskType =
  | 'followup_appointment'
  | 'lab_test_order'
  | 'diagnostic_imaging_order'
  | 'patient_education'
  | 'medication_reconciliation'
  | 'telemetry_check'
  | 'general_task';

export interface CareTask {
  id: number;
  task_id: string;
  patient_id: number;
  care_plan_id?: number;
  encounter_id?: number;
  appointment_id?: number;
  assigned_user_id?: number;
  title: string;
  task_type: CareTaskType;
  priority: TaskPriority;
  status: CareTaskStatus;
  instructions?: string;
  due_date: string;
  is_overdue: boolean;
  completed_at?: string;
  completion_notes?: string;
  created_at: string;
}

export interface CareTaskListResponse {
  items: CareTask[];
  total: number;
}
