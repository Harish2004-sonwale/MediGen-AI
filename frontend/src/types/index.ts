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
  default_facility_id?: string;
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
  facility_id?: string;
  phone?: string;
  email?: string;
  address?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  blood_group?: string;
  allergies?: string;
  health_problem?: string;
  previous_diagnoses?: string;
  current_medications?: string;
  assigned_doctor_id?: number;
  assigned_doctor_name?: string;
  user_id?: number;
  status?: 'pending_review' | 'active' | 'appointment_scheduled' | 'under_care' | 'discharged' | 'inactive' | 'archived';
  is_active?: boolean;
  created_at: string;
  updated_at?: string;
}

export interface Doctor {
  id: number;
  doctor_id: string;
  user_id: number;
  full_name: string;
  professional_title: string;
  department: string;
  specialization: string;
  qualifications?: string;
  medical_degree?: string;
  medical_registration_number: string;
  years_of_experience: number;
  email: string;
  phone?: string;
  clinic_hospital_name?: string;
  consultation_location?: string;
  consultation_mode?: string;
  verification_status?: string;
  availability_status?: string;
}

export interface Appointment {
  id: number;
  appointment_id: string;
  patient_id: number;
  doctor_id: number;
  appointment_date: string;
  duration_minutes: number;
  consultation_mode: string;
  reason_for_visit: string;
  status: string;
  clinical_notes?: string;
  cancellation_reason?: string;
  patient?: Patient;
  doctor?: Doctor;
  created_at: string;
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

export type CohortType =
  | 'disease_registry'
  | 'risk_watch_list'
  | 'post_op_monitoring'
  | 'quality_measure'
  | 'custom_cohort';

export interface CohortCriteria {
  min_age?: number;
  max_age?: number;
  gender?: string;
  conditions?: string[];
  medications?: string[];
  min_systolic_bp?: number;
  max_systolic_bp?: number;
  min_spo2?: number;
  min_risk_score?: number;
  risk_tier?: string;
  active_alerts_only?: boolean;
}

export interface PatientCohort {
  id: number;
  cohort_id: string;
  name: string;
  description: string;
  cohort_type: CohortType;
  criteria_json?: CohortCriteria;
  is_dynamic: boolean;
  created_by_user_id?: number;
  created_at: string;
  updated_at: string;
  member_count: number;
}

export interface CohortListResponse {
  items: PatientCohort[];
  total: number;
}

export interface CohortMembership {
  id: number;
  cohort_id: number;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  enrolled_at: string;
  status: string;
  notes?: string;
  latest_risk_score?: number;
  latest_risk_tier?: string;
}

export interface CohortAnalytics {
  cohort_id: string;
  name: string;
  cohort_type: string;
  total_members: number;
  risk_tier_distribution: Record<string, number>;
  mean_risk_score: number;
  high_risk_patient_count: number;
  active_alerts_count: number;
  active_care_plans_count: number;
  overdue_tasks_count: number;
  generated_at: string;
}

export type RiskType =
  | 'readmission_30d'
  | 'cardiovascular_decompensation'
  | 'clinical_deterioration'
  | 'medication_adherence'
  | 'general_mortality';

export type RiskTier = 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';

export interface RiskFactor {
  factor_name: string;
  category: string;
  severity: string;
  observed_value?: string;
  clinical_rationale: string;
}

export interface RiskMitigationAction {
  action_title: string;
  priority: string;
  suggested_task_type?: string;
  target_timeline_days: number;
  rational: string;
}

export interface ClinicalRiskAssessment {
  id: number;
  assessment_id: string;
  patient_id: number;
  encounter_id?: number;
  risk_type: RiskType;
  risk_score: number;
  risk_tier: RiskTier;
  predicted_outcome: string;
  contributing_factors_json?: RiskFactor[];
  mitigation_recommendations_json?: RiskMitigationAction[];
  assessed_by_user_id?: number;
  is_ai_generated: boolean;
  assessed_at: string;
  created_at: string;
}

export interface RiskAssessmentListResponse {
  items: ClinicalRiskAssessment[];
  total: number;
}

export type HandoffFramework = 'ipass' | 'sbar';
export type HandoffType =
  | 'shift_change'
  | 'unit_transfer'
  | 'discharge_transition'
  | 'service_consultation';
export type IllnessSeverity = 'stable' | 'watcher' | 'unstable';
export type HandoffStatus = 'draft' | 'active' | 'acknowledged' | 'completed' | 'cancelled';

export interface HandoffActionItem {
  item_id: string;
  task_description: string;
  role_required: string;
  priority: string;
  is_completed: boolean;
}

export interface ContingencyPlan {
  plan_id: string;
  trigger_condition: string;
  immediate_action: string;
  escalation_contact: string;
}

export interface ClinicalHandoff {
  id: number;
  handoff_id: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  encounter_id?: number;
  sender_user_id?: number;
  sender_name?: string;
  receiver_user_id?: number;
  receiver_name?: string;
  framework: HandoffFramework;
  handoff_type: HandoffType;
  illness_severity: IllnessSeverity;
  status: HandoffStatus;
  summary: string;
  action_items_json?: HandoffActionItem[];
  situational_awareness_json?: ContingencyPlan[];
  synthesis_notes?: string;
  is_ai_generated: boolean;
  acknowledged_at?: string;
  created_at: string;
  updated_at: string;
}

export interface HandoffListResponse {
  items: ClinicalHandoff[];
  total: number;
}

export type DischargeDisposition =
  | 'home_self_care'
  | 'home_health_services'
  | 'skilled_nursing_facility'
  | 'rehab_facility'
  | 'hospice'
  | 'transfer_acute_care';

export type DischargeStatus =
  | 'draft'
  | 'under_review'
  | 'ready_for_discharge'
  | 'completed'
  | 'cancelled';

export interface MedicationReconciliationItem {
  medication_name: string;
  dose: string;
  route: string;
  frequency: string;
  reconciliation_status: string;
  clinical_rationale: string;
}

export interface FollowupAppointmentItem {
  provider_or_specialty: string;
  timeframe: string;
  purpose: string;
  contact_phone?: string;
}

export interface PendingDiagnosticItem {
  test_name: string;
  ordered_date?: string;
  follow_up_physician: string;
  instructions: string;
}

export interface WarningSymptomItem {
  symptom_title: string;
  urgency_level: string;
  action_instructions: string;
}

export interface DischargeProtocol {
  id: number;
  discharge_id: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  encounter_id?: number;
  attending_user_id?: number;
  attending_name?: string;
  nurse_user_id?: number;
  nurse_name?: string;
  pharmacist_user_id?: number;
  pharmacist_name?: string;
  status: DischargeStatus;
  disposition: DischargeDisposition;
  discharge_date?: string;
  hospital_course_summary: string;
  primary_discharge_diagnosis: string;
  secondary_diagnoses_json?: string[];
  medication_reconciliation_json?: MedicationReconciliationItem[];
  followup_instructions_json?: FollowupAppointmentItem[];
  pending_tests_json?: PendingDiagnosticItem[];
  warning_symptoms_json?: WarningSymptomItem[];
  activity_and_diet_instructions?: string;
  is_ai_generated: boolean;
  signed_off_at?: string;
  created_at: string;
  updated_at: string;
}

export interface DischargeProtocolListResponse {
  items: DischargeProtocol[];
  total: number;
}

// =============================================================================
// PHASE 9.0.13: CPOE ORDERS & DIAGNOSTIC RESULTS
// =============================================================================

export type OrderCategory = 'laboratory' | 'imaging' | 'medication' | 'nursing' | 'consultation';
export type OrderPriority = 'routine' | 'urgent' | 'stat';
export type OrderStatus = 'draft' | 'placed' | 'in_progress' | 'completed' | 'cancelled';
export type DiagnosticResultStatus = 'preliminary' | 'final' | 'amended' | 'corrected';
export type AbnormalFlag = 'normal' | 'abnormal_low' | 'abnormal_high' | 'panic_critical';

export interface ClinicalOrder {
  id: number;
  order_id: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  encounter_id?: number;
  ordering_user_id?: number;
  ordering_user_name?: string;
  order_category: OrderCategory;
  order_type: string;
  priority: OrderPriority;
  status: OrderStatus;
  clinical_indication: string;
  specimen_source?: string;
  order_details_json?: Record<string, any>;
  ai_safety_flags_json?: Array<{ severity: string; code: string; message: string }>;
  is_ai_suggested: boolean;
  placed_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ClinicalOrderListResponse {
  items: ClinicalOrder[];
  total: number;
}

export interface DiagnosticResult {
  id: number;
  result_id: string;
  order_id: number;
  order_identifier?: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  encounter_id?: number;
  test_name: string;
  test_code_loinc?: string;
  status: DiagnosticResultStatus;
  abnormal_flag: AbnormalFlag;
  findings_summary: string;
  numeric_value?: number;
  unit_of_measure?: string;
  reference_range_low?: number;
  reference_range_high?: number;
  critical_threshold_low?: number;
  critical_threshold_high?: number;
  structured_components_json?: Array<Record<string, any>>;
  reviewed_by_user_id?: number;
  reviewed_by_user_name?: string;
  reviewed_at?: string;
  resulted_at: string;
  created_at: string;
  updated_at: string;
}

export interface DiagnosticResultListResponse {
  items: DiagnosticResult[];
  total: number;
}

export interface OrderBundleItem {
  order_category: OrderCategory;
  order_type: string;
  priority: OrderPriority;
  clinical_indication: string;
  specimen_source?: string;
  order_details?: Record<string, any>;
}

export interface OrderBundleSuggestResponse {
  protocol_name: string;
  clinical_rationale: string;
  suggested_orders: OrderBundleItem[];
  pre_order_safety_warnings: string[];
}

// =============================================================================
// PHASE 9.0.14: CLINICAL QUALITY MEASURES (CQMS) & HEDIS/MIPS COMPLIANCE
// =============================================================================

export type QualityDomain =
  | 'chronic_disease_management'
  | 'patient_safety'
  | 'care_coordination'
  | 'preventive_care'
  | 'clinical_process';

export type ComplianceStatus =
  | 'compliant'
  | 'non_compliant'
  | 'excluded'
  | 'not_applicable';

export type GapSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type GapStatus = 'open' | 'in_remediation' | 'resolved' | 'dismissed';
export type ReportScope = 'patient' | 'provider' | 'department' | 'organization';

export interface QualityMeasure {
  id: number;
  measure_id: string;
  title: string;
  description: string;
  domain: QualityDomain;
  standard_framework: string;
  steward: string;
  version: string;
  target_rate: number;
  initial_population_criteria: string;
  denominator_criteria: string;
  numerator_criteria: string;
  exclusion_criteria?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface QualityMeasureListResponse {
  items: QualityMeasure[];
  total: number;
}

export interface QualityMeasureResult {
  id: number;
  result_id: string;
  measure_id: number;
  measure_code?: string;
  measure_title?: string;
  measure_domain?: QualityDomain;
  target_rate?: number;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  is_eligible: boolean;
  is_denominator_eligible: boolean;
  is_numerator_compliant: boolean;
  is_excluded: boolean;
  compliance_status: ComplianceStatus;
  calculated_value?: number;
  evidence_json?: Record<string, any>;
  gap_reason?: string;
  calculated_by_user_id?: number;
  calculated_at: string;
  created_at: string;
  updated_at: string;
}

export interface QualityMeasureResultListResponse {
  items: QualityMeasureResult[];
  total: number;
}

export interface QualityMeasureGap {
  id: number;
  gap_id: string;
  measure_id: number;
  measure_code?: string;
  measure_title?: string;
  measure_domain?: QualityDomain;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  severity: GapSeverity;
  status: GapStatus;
  missing_data_summary: string;
  recommended_action: string;
  linked_care_task_id?: number;
  identified_at: string;
  due_date?: string;
  resolved_at?: string;
  resolution_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface QualityMeasureGapListResponse {
  items: QualityMeasureGap[];
  total: number;
}

export interface QualityMeasureScoreSummary {
  measure_id: string;
  title: string;
  domain: string;
  standard_framework: string;
  target_rate: number;
  performance_rate: number;
  eligible_population: number;
  compliant_population: number;
  gap_count: number;
}

export interface QualityMeasureReport {
  id: number;
  report_id: string;
  title: string;
  report_scope: ReportScope;
  scope_identifier?: string;
  measurement_period_start: string;
  measurement_period_end: string;
  overall_performance_rate: number;
  total_eligible_population: number;
  total_compliant_population: number;
  measure_summaries_json: QualityMeasureScoreSummary[];
  audit_metadata_json: Record<string, any>;
  generated_by_user_id?: number;
  generated_by_name?: string;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface QualityMeasureReportListResponse {
  items: QualityMeasureReport[];
  total: number;
}

// ============================================================================
// Phase 9.0.15: Remote Patient Monitoring (RPM), PROMs & Telehealth
// ============================================================================

export type RPMProgramStatus = 'active' | 'graduated' | 'suspended' | 'cancelled';
export type RPMDeviceStatus = 'active' | 'inactive' | 'pending_verification' | 'decommissioned';
export type RPMObservationType =
  | 'systolic_bp'
  | 'diastolic_bp'
  | 'heart_rate'
  | 'spo2'
  | 'blood_glucose'
  | 'weight'
  | 'temperature'
  | 'respiratory_rate';
export type RPMSourceType = 'manual_entry' | 'bluetooth_sync' | 'cellular_gateway' | 'api_integration';
export type ObservationClassification = 'normal' | 'abnormal' | 'critical';
export type RPMEscalationStatus = 'open' | 'acknowledged' | 'in_progress' | 'resolved' | 'dismissed';
export type TelehealthStatus = 'scheduled' | 'waiting_room' | 'in_progress' | 'completed' | 'cancelled' | 'no_show';

export interface RPMProgram {
  id: number;
  program_id: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  condition_name: string;
  program_name: string;
  target_cadence_days: number;
  clinical_goals: string[];
  status: RPMProgramStatus;
  enrolled_at: string;
  created_at: string;
  updated_at: string;
}

export interface RPMProgramListResponse {
  items: RPMProgram[];
  total: number;
}

export interface RPMDevice {
  id: number;
  device_id: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  device_type: string;
  manufacturer: string;
  model_number: string;
  serial_number: string;
  status: RPMDeviceStatus;
  supported_measurements: string[];
  last_sync_at?: string;
  created_at: string;
  updated_at: string;
}

export interface RPMDeviceListResponse {
  items: RPMDevice[];
  total: number;
}

export interface RPMObservation {
  id: number;
  observation_id: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  device_id?: number;
  device_identifier?: string;
  observation_type: RPMObservationType;
  numeric_value: number;
  secondary_value?: number;
  unit_of_measure: string;
  source_type: RPMSourceType;
  classification: ObservationClassification;
  recorded_at: string;
  created_at: string;
}

export interface RPMObservationListResponse {
  items: RPMObservation[];
  total: number;
}

export interface RPMTelemetrySummary {
  patient_id: string;
  total_observations_count: number;
  critical_observations_count: number;
  abnormal_observations_count: number;
  normal_observations_count: number;
  average_systolic_bp?: number;
  average_diastolic_bp?: number;
  average_heart_rate?: number;
  average_spo2?: number;
  average_blood_glucose?: number;
  average_weight?: number;
  latest_observation_time?: string;
  adherence_rate: number;
  active_alerts_count: number;
}

export interface RPMEscalationAlert {
  id: number;
  alert_id: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  observation_id?: number;
  observation_summary?: string;
  severity: string;
  status: RPMEscalationStatus;
  escalation_reason: string;
  linked_care_task_id?: number;
  acknowledged_by_user_id?: number;
  acknowledged_by_name?: string;
  acknowledged_at?: string;
  clinical_action_taken?: string;
  resolved_at?: string;
  created_at: string;
  updated_at: string;
}

export interface RPMEscalationAlertListResponse {
  items: RPMEscalationAlert[];
  total: number;
}

export interface PROMQuestionOption {
  value: number | string;
  label: string;
  score: number;
}

export interface PROMQuestion {
  id: string;
  prompt: string;
  options: PROMQuestionOption[];
}

export interface PROMDefinition {
  id: number;
  prom_id: string;
  title: string;
  domain: string;
  version: string;
  scoring_method: string;
  questions_json: PROMQuestion[];
  interpretation_ranges_json: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PROMDefinitionListResponse {
  items: PROMDefinition[];
  total: number;
}

export interface PROMResponseDetail {
  id: number;
  response_id: string;
  prom_id: number;
  prom_identifier?: string;
  prom_title?: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  answers_json: Record<string, any>;
  calculated_score: number;
  severity_interpretation: string;
  safety_flags_json: string[];
  clinical_notes?: string;
  completed_at: string;
  created_at: string;
}

export interface PROMResponseListResponse {
  items: PROMResponseDetail[];
  total: number;
}

export interface TelehealthSession {
  id: number;
  session_id: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  clinician_user_id: number;
  clinician_name?: string;
  appointment_id?: number;
  encounter_id?: number;
  status: TelehealthStatus;
  scheduled_start: string;
  actual_start?: string;
  actual_end?: string;
  visit_reason: string;
  pre_visit_rpm_summary_json?: Record<string, any>;
  pre_visit_prom_summary_json?: Record<string, any>;
  session_notes?: string;
  followup_instructions?: string;
  created_at: string;
  updated_at: string;
}

export interface TelehealthSessionListResponse {
  items: TelehealthSession[];
  total: number;
}

// ============================================================================
// PHASE 9.0.16: CLINICAL TRIALS, GENOMICS & PRECISION ONCOLOGY TYPES
// ============================================================================

export type TrialPhase =
  | 'early_phase_1'
  | 'phase_1'
  | 'phase_1_2'
  | 'phase_2'
  | 'phase_2_3'
  | 'phase_3'
  | 'phase_4';

export type TrialStatus =
  | 'recruiting'
  | 'active_not_recruiting'
  | 'enrolling_by_invitation'
  | 'completed'
  | 'suspended'
  | 'terminated';

export type CriterionType = 'inclusion' | 'exclusion';

export type CriterionCategory =
  | 'biomarker'
  | 'diagnosis'
  | 'disease_stage'
  | 'age'
  | 'performance_status'
  | 'prior_therapy'
  | 'laboratory_value'
  | 'organ_function'
  | 'contraindication';

export type MatchStatus =
  | 'MATCHED'
  | 'POTENTIAL_MATCH'
  | 'INELIGIBLE'
  | 'INSUFFICIENT_DATA'
  | 'MANUAL_REVIEW';

export type PrecisionEligibilityStatus =
  | 'ELIGIBLE'
  | 'NOT_ELIGIBLE'
  | 'INSUFFICIENT_DATA'
  | 'MANUAL_REVIEW';

export type ClinicianReviewStatus =
  | 'pending_review'
  | 'confirmed_eligible'
  | 'declined_by_clinician'
  | 'enrolled_in_trial'
  | 'patient_declined'
  | 'approved_for_protocol'
  | 'rejected_by_clinician';

export interface TrialEligibilityCriterion {
  id: number;
  criterion_id: string;
  trial_id: number;
  category: CriterionCategory;
  criterion_type: CriterionType;
  field_name: string;
  operator: string;
  expected_value_str?: string;
  expected_value_num?: number;
  expected_value_json?: any;
  unit_of_measure?: string;
  is_required: boolean;
  description: string;
  created_at: string;
}

export interface ClinicalTrial {
  id: number;
  trial_id: string;
  nct_number?: string;
  title: string;
  official_title?: string;
  sponsor: string;
  phase: TrialPhase;
  status: TrialStatus;
  disease_condition: string;
  intervention_name: string;
  intervention_type: string;
  location_sites_json?: Array<Record<string, any>>;
  min_age_years?: number;
  max_age_years?: number;
  target_gender: string;
  summary?: string;
  inclusion_criteria_text?: string;
  exclusion_criteria_text?: string;
  contact_email?: string;
  contact_phone?: string;
  is_active: boolean;
  version: string;
  created_at: string;
  updated_at: string;
}

export interface ClinicalTrialDetail extends ClinicalTrial {
  criteria: TrialEligibilityCriterion[];
}

export interface ClinicalTrialListResponse {
  items: ClinicalTrial[];
  total: number;
}

export interface BiomarkerObservation {
  id: number;
  observation_id: string;
  profile_id: number;
  patient_id: number;
  gene_symbol: string;
  variant_name: string;
  alteration_type: string;
  hgvs_notation?: string;
  chromosome?: string;
  genomic_position?: string;
  reference_allele?: string;
  alternate_allele?: string;
  zygosity?: string;
  variant_allele_fraction?: number;
  pathogenicity: string;
  evidence_level: string;
  clinical_significance?: string;
  numeric_expression_value?: number;
  expression_unit?: string;
  detected_at: string;
  created_at: string;
}

export interface GenomicProfile {
  id: number;
  profile_id: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  specimen_type: string;
  specimen_collected_at?: string;
  test_name: string;
  sequencing_platform: string;
  performing_lab: string;
  accession_number?: string;
  tumor_mutation_burden?: number;
  microsatellite_instability_status?: string;
  overall_interpretation?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface GenomicProfileDetail extends GenomicProfile {
  biomarkers: BiomarkerObservation[];
}

export interface GenomicProfileListResponse {
  items: GenomicProfileDetail[];
  total: number;
}

export interface CriterionEvaluationResult {
  criterion_id: string;
  category: string;
  criterion_type: string;
  field_name: string;
  description: string;
  status: 'PASS' | 'FAIL' | 'UNKNOWN';
  evidence: string;
  reason: string;
}

export interface TrialMatch {
  id: number;
  match_id: string;
  trial_id: number;
  trial_identifier?: string;
  trial_title?: string;
  trial_phase?: string;
  trial_sponsor?: string;
  disease_condition?: string;
  intervention_name?: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  match_status: MatchStatus;
  match_score: number;
  matched_criteria_json: CriterionEvaluationResult[];
  failed_criteria_json: CriterionEvaluationResult[];
  unknown_criteria_json: CriterionEvaluationResult[];
  overall_explanation: string;
  provenance_hash: string;
  algorithm_version: string;
  clinician_review_status: ClinicianReviewStatus;
  reviewed_by_user_id?: number;
  reviewed_by_name?: string;
  review_notes?: string;
  reviewed_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TrialMatchListResponse {
  items: TrialMatch[];
  total: number;
}

export interface PrecisionTreatmentEligibility {
  id: number;
  eligibility_id: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  gene_symbol: string;
  variant_name: string;
  recommended_intervention: string;
  drug_class: string;
  indication: string;
  eligibility_status: PrecisionEligibilityStatus;
  evidence_source: string;
  supporting_observations_json: string[];
  contraindicating_observations_json: string[];
  unknown_factors_json: string[];
  provenance_hash: string;
  clinician_review_status: ClinicianReviewStatus;
  reviewed_by_user_id?: number;
  reviewed_by_name?: string;
  review_notes?: string;
  reviewed_at?: string;
  created_at: string;
}

export interface PrecisionTreatmentEligibilityListResponse {
  items: PrecisionTreatmentEligibility[];
  total: number;
}

export interface BatchMatchResponse {
  patient_id: string;
  total_evaluated_trials: number;
  matched_trials_count: number;
  potential_trials_count: number;
  ineligible_trials_count: number;
  matches: TrialMatch[];
}

// =============================================================================
// PHASE 9.0.17: ADVANCED CLINICAL AI AGENTS & AUTONOMOUS CARE COORDINATION
// =============================================================================

export type AgentType =
  | 'clinical_context'
  | 'risk_surveillance'
  | 'care_coordination'
  | 'diagnostic_followup'
  | 'medication_safety'
  | 'quality_gap'
  | 'rpm_telehealth'
  | 'transition_discharge'
  | 'trial_genomics'
  | 'master_orchestrator';

export type AgentRunStatus =
  | 'idle'
  | 'running'
  | 'completed'
  | 'waiting_for_approval'
  | 'failed'
  | 'cancelled';

export type RecommendationActionClass =
  | 'READ_ONLY'
  | 'RECOMMENDATION'
  | 'CLINICIAN_APPROVAL_REQUIRED'
  | 'HIGH_RISK';

export type RecommendationPriority = 'urgent' | 'high' | 'medium' | 'low';

export type ApprovalStatus =
  | 'pending_review'
  | 'approved'
  | 'rejected'
  | 'executed'
  | 'expired';

export interface AgentEvidenceReference {
  id?: number;
  evidence_id: string;
  recommendation_id?: number;
  entity_type: string;
  entity_identifier: string;
  title: string;
  excerpt?: string;
  confidence_score: number;
  created_at?: string;
}

export interface ClinicalAgentRecommendation {
  id: number;
  recommendation_id: string;
  run_id: number;
  patient_id: number;
  category: string;
  title: string;
  description: string;
  rationale: string;
  priority: RecommendationPriority;
  action_class: RecommendationActionClass;
  suggested_action_type?: string;
  suggested_action_payload_json?: Record<string, any>;
  approval_status: ApprovalStatus;
  reviewed_by_user_id?: number;
  reviewed_by_name?: string;
  review_notes?: string;
  reviewed_at?: string;
  execution_status?: string;
  executed_at?: string;
  execution_result_json?: Record<string, any>;
  provenance_hash: string;
  evidence_references: AgentEvidenceReference[];
  created_at: string;
  updated_at: string;
}

export interface ClinicalAgentDefinition {
  id: number;
  agent_id: string;
  name: string;
  agent_type: AgentType;
  description: string;
  version: string;
  is_active: boolean;
  default_action_class: RecommendationActionClass;
  created_at: string;
}

export interface ClinicalAgentDefinitionListResponse {
  items: ClinicalAgentDefinition[];
  total: number;
}

export interface ClinicalAgentRun {
  id: number;
  run_id: string;
  agent_type: AgentType;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  initiated_by_user_id?: number;
  initiated_by_name?: string;
  status: AgentRunStatus;
  start_time: string;
  end_time?: string;
  overall_summary?: string;
  context_hash: string;
  provenance_hash: string;
  recommendations_count: number;
  created_at: string;
}

export interface ClinicalAgentRunDetail extends ClinicalAgentRun {
  input_context_snapshot_json?: Record<string, any>;
  error_message?: string;
  recommendations: ClinicalAgentRecommendation[];
}

export interface ClinicalAgentRunListResponse {
  items: ClinicalAgentRun[];
  total: number;
}

export interface CareCoordinationSynthesisResponse {
  patient_id: string;
  patient_name: string;
  run_id: string;
  status: AgentRunStatus;
  overall_summary: string;
  provenance_hash: string;
  urgent_recommendations_count: number;
  high_recommendations_count: number;
  pending_approvals_count: number;
  recommendations: ClinicalAgentRecommendation[];
}

// ==============================================================================
// Phase 9.0.18: Medical Imaging AI, Multimodal Diagnostics & Radiology Types
// ==============================================================================

export type ImagingModality = 'XRAY' | 'CT' | 'MRI' | 'ULTRASOUND' | 'MAMMOGRAPHY' | 'PET_CT' | 'ECHOCARDIOGRAPHY' | 'OTHER';
export type ImagingBodySite = 'CHEST' | 'ABDOMEN' | 'PELVIS' | 'HEAD_BRAIN' | 'SPINE' | 'EXTREMITY' | 'CARDIAC' | 'BREAST' | 'NECK' | 'OTHER';
export type ImagingStudyStatus = 'ORDERED' | 'SCHEDULED' | 'IN_PROGRESS' | 'COMPLETED' | 'PRELIMINARY' | 'FINAL' | 'CANCELLED';
export type ImagingFindingType = 'NORMAL_APPEARANCE' | 'POSSIBLE_NODULE' | 'POSSIBLE_FRACTURE' | 'POSSIBLE_PNEUMONIA' | 'POSSIBLE_EFFUSION' | 'POSSIBLE_HEMORRHAGE' | 'POSSIBLE_MASS' | 'OTHER_ABNORMALITY';
export type FindingLaterality = 'LEFT' | 'RIGHT' | 'BILATERAL' | 'MIDLINE' | 'NOT_APPLICABLE';
export type FindingSeverity = 'NORMAL' | 'MILD' | 'MODERATE' | 'SEVERE' | 'CRITICAL';
export type FindingNature = 'OBSERVED_FACT' | 'AI_GENERATED_FINDING' | 'CLINICIAN_CONFIRMED_FINDING';
export type FindingReviewStatus = 'pending_review' | 'confirmed' | 'rejected' | 'amended';
export type ReportStatus = 'DRAFT' | 'AI_ASSISTED' | 'RADIOLOGIST_REVIEW' | 'FINALIZED' | 'AMENDED';

export interface ImagingAsset {
  id: number;
  asset_id: string;
  study_id: number;
  series_instance_uid?: string;
  sop_instance_uid?: string;
  series_number?: number;
  instance_number?: number;
  series_description?: string;
  modality: string;
  body_site?: string;
  mime_type: string;
  file_size_bytes: number;
  storage_path: string;
  thumbnail_storage_path?: string;
  image_dimensions?: Record<string, any>;
  dicom_metadata_json?: Record<string, any>;
  provenance_hash: string;
  created_at: string;
}

export interface ImagingFinding {
  id: number;
  finding_id: string;
  study_id: number;
  asset_id?: number;
  patient_id: number;
  finding_type: ImagingFindingType | string;
  anatomical_location: string;
  laterality: FindingLaterality | string;
  severity: FindingSeverity | string;
  confidence_score: number;
  is_critical: boolean;
  finding_nature: FindingNature | string;
  description: string;
  recommendation: string;
  bounding_box_json?: { x: number; y: number; width: number; height: number } | null;
  clinician_review_status: FindingReviewStatus | string;
  reviewed_by_user_id?: number;
  reviewed_at?: string;
  review_notes?: string;
  provenance_hash: string;
  created_at: string;
}

export interface RadiologyReport {
  id: number;
  report_id: string;
  study_id: number;
  study_identifier?: string;
  study_description?: string;
  modality?: string;
  body_site?: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  encounter_id?: number;
  order_id?: number;
  status: ReportStatus | string;
  clinical_indication: string;
  technique: string;
  comparison_studies: string;
  findings: string;
  impression: string;
  recommendations: string;
  critical_findings_summary?: string;
  is_critical: boolean;
  ai_assistance_metadata_json?: Record<string, any>;
  author_user_id?: number;
  author_name?: string;
  signed_by_user_id?: number;
  signed_by_name?: string;
  signed_at?: string;
  amendment_reason?: string;
  amended_from_report_id?: number;
  provenance_hash: string;
  created_at: string;
  updated_at: string;
}

export interface ImagingStudy {
  id: number;
  study_id: string;
  patient_id: number;
  patient_identifier?: string;
  patient_name?: string;
  encounter_id?: number;
  order_id?: number;
  modality: ImagingModality | string;
  body_site: ImagingBodySite | string;
  study_description: string;
  accession_number: string;
  study_datetime: string;
  performing_department: string;
  referring_provider?: string;
  status: ImagingStudyStatus | string;
  source: string;
  external_identifier?: string;
  metadata_json?: Record<string, any>;
  provenance_hash: string;
  created_at: string;
  updated_at: string;
  assets_count?: number;
  findings_count?: number;
  reports_count?: number;
  has_critical_findings?: boolean;
}

export interface MultimodalContextSnapshot {
  patient_id: string;
  patient_name: string;
  age_years: number;
  gender: string;
  clinical_indication: string;
  modality: string;
  body_site: string;
  active_diagnoses: string[];
  active_medications: string[];
  allergies: string[];
  recent_vitals: Record<string, any>[];
  active_alerts: Record<string, any>[];
  relevant_lab_results: Record<string, any>[];
  previous_studies: Record<string, any>[];
}

export interface ImagingAnalysisResponse {
  study_id: string;
  status: string;
  findings_count: number;
  critical_findings_count: number;
  findings: ImagingFinding[];
  draft_report?: RadiologyReport;
  multimodal_context: MultimodalContextSnapshot;
  provenance_hash: string;
  evaluated_at: string;
}

export interface ImagingTimelineItem {
  event_id: string;
  study_id: string;
  study_datetime: string;
  modality: string;
  body_site: string;
  description: string;
  status: string;
  accession_number: string;
  findings_count: number;
  has_critical: boolean;
  report_id?: string;
  report_status?: string;
}

export interface ImagingTimelineResponse {
  patient_id: string;
  total_studies: number;
  items: ImagingTimelineItem[];
}

// ============================================================================
// PHASE 9.0.19: CLINICAL SECURITY, AUDITABILITY, CONSENT & COMPLIANCE
// ============================================================================

export type AuditAction =
  | 'CREATE'
  | 'READ'
  | 'UPDATE'
  | 'DELETE'
  | 'EXECUTE'
  | 'EXPORT'
  | 'LOGIN'
  | 'LOGOUT'
  | 'CONSENT_GRANT'
  | 'CONSENT_REVOKE'
  | 'SECURITY_ALERT'
  | 'HOLD_APPLIED'
  | 'HOLD_RELEASED';

export type AuditOutcome =
  | 'SUCCESS'
  | 'DENIED_FORBIDDEN'
  | 'DENIED_NO_CONSENT'
  | 'WARNING'
  | 'ERROR';

export interface ClinicalAuditEvent {
  id: number;
  event_id: string;
  timestamp: string;
  user_id?: number;
  user_role: string;
  patient_id?: string;
  action: AuditAction | string;
  resource_type: string;
  resource_id?: string;
  ip_address?: string;
  user_agent?: string;
  purpose_of_use: string;
  outcome: AuditOutcome | string;
  metadata_json: Record<string, any>;
  prev_record_hash: string;
  record_hash: string;
}

export interface AuditEventListResponse {
  events: ClinicalAuditEvent[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface AuditIntegrityVerificationResponse {
  verified_at: string;
  total_records_checked: number;
  tamper_detected: boolean;
  broken_links_count: number;
  tampered_event_ids: string[];
  chain_head_hash?: string;
  status: 'VALID' | 'COMPROMISED' | string;
}

export type ConsentStatus = 'ACTIVE' | 'REVOKED' | 'EXPIRED' | 'PENDING';
export type ConsentPolicyRule = 'PERMIT' | 'DENY';
export type ConsentScope =
  | 'ALL_RECORDS'
  | 'RESEARCH_ONLY'
  | 'GENOMICS_ONLY'
  | 'BEHAVIORAL_HEALTH'
  | 'THIRD_PARTY_SHARING'
  | 'RESTRICT_EXPORT';

export interface PatientConsent {
  id: number;
  consent_id: string;
  patient_id: string;
  status: ConsentStatus | string;
  scope: ConsentScope | string;
  policy_rule: ConsentPolicyRule | string;
  purpose_of_use: string;
  data_category?: string;
  actor_type?: string;
  actor_reference?: string;
  valid_from: string;
  valid_to?: string;
  signed_by_patient: boolean;
  signer_name: string;
  signer_relationship: string;
  witness_or_clinician_id?: number;
  digital_signature_hash: string;
  revocation_reason?: string;
  revoked_at?: string;
  created_at: string;
}

export interface PatientConsentCreateRequest {
  scope: ConsentScope | string;
  policy_rule: ConsentPolicyRule | string;
  purpose_of_use: string;
  data_category?: string;
  actor_type?: string;
  actor_reference?: string;
  valid_from?: string;
  valid_to?: string;
  signed_by_patient?: boolean;
  signer_name: string;
  signer_relationship?: string;
  witness_or_clinician_id?: number;
}

export interface PatientConsentRevokeRequest {
  revocation_reason: string;
}

export interface ConsentVerificationRequest {
  patient_id: string;
  resource_type: string;
  action: string;
  purpose_of_use: string;
  data_category?: string;
}

export interface ConsentVerificationResponse {
  patient_id: string;
  resource_type: string;
  action: string;
  purpose_of_use: string;
  is_permitted: boolean;
  reason: string;
  matched_consent_id?: string;
  is_emergency_override: boolean;
}

export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type IncidentStatus = 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'FALSE_POSITIVE';

export interface SecurityIncident {
  id: number;
  incident_id: string;
  detected_at: string;
  severity: IncidentSeverity | string;
  status: IncidentStatus | string;
  event_type: string;
  user_id?: number;
  patient_id?: string;
  ip_address?: string;
  description: string;
  evidence_metadata: Record<string, any>;
  assigned_to_user_id?: number;
  resolution_notes?: string;
  resolved_at?: string;
  resolved_by_user_id?: number;
  created_at: string;
  updated_at: string;
}

export interface SecurityIncidentCreateRequest {
  severity: IncidentSeverity | string;
  event_type: string;
  description: string;
  user_id?: number;
  patient_id?: string;
  ip_address?: string;
  evidence_metadata?: Record<string, any>;
}

export interface SecurityIncidentUpdateRequest {
  status?: IncidentStatus | string;
  severity?: IncidentSeverity | string;
  assigned_to_user_id?: number;
  resolution_notes?: string;
}

export interface SecurityScanResult {
  scanned_at: string;
  events_analyzed: number;
  anomalies_detected: number;
  new_incidents_created: number;
  incident_ids: string[];
}

export interface DataRetentionPolicy {
  id: number;
  policy_code: string;
  data_category: string;
  retention_period_days: number;
  action_on_expiry: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DataRetentionPolicyCreateRequest {
  policy_code: string;
  data_category: string;
  retention_period_days: number;
  action_on_expiry: string;
  description: string;
  is_active?: boolean;
}

export type HoldStatus = 'ACTIVE' | 'RELEASED';

export interface LegalClinicalHold {
  id: number;
  hold_id: string;
  patient_id?: string;
  scope_category: string;
  reason: string;
  status: HoldStatus | string;
  placed_by_user_id: number;
  placed_at: string;
  released_by_user_id?: number;
  released_at?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface LegalClinicalHoldCreateRequest {
  patient_id?: string;
  scope_category?: string;
  reason: string;
  notes?: string;
}

export interface LegalClinicalHoldReleaseRequest {
  notes?: string;
}

export interface ComplianceSummaryResponse {
  generated_at: string;
  total_audit_events: number;
  recent_audit_events_24h: number;
  audit_tamper_integrity_status: 'VALID' | 'COMPROMISED' | string;
  total_active_consents: number;
  total_revoked_consents: number;
  open_security_incidents: number;
  critical_security_incidents: number;
  active_legal_holds: number;
  active_retention_policies: number;
  compliance_score_percent: number;
  status: 'COMPLIANT' | 'WARNING' | 'NON_COMPLIANT' | string;
}

// ============================================================================
// Phase 9.0.20: System Diagnostics, Operational Metrics & FHIR Metadata
// ============================================================================

export interface SystemLivenessResponse {
  status: 'alive' | string;
  service: string;
  version: string;
  environment: string;
  correlation_id?: string;
}

export interface SystemComponentHealth {
  status?: string;
  healthy: boolean;
  provider?: string;
  collection?: string;
  error?: string;
  metrics?: Record<string, any>;
  [key: string]: any;
}

export interface SystemReadinessResponse {
  status: 'ready' | 'not_ready' | string;
  ready: boolean;
  service: string;
  version: string;
  components: {
    database?: SystemComponentHealth;
    cache?: SystemComponentHealth;
    vector_store?: SystemComponentHealth;
    task_worker?: SystemComponentHealth;
    drug_knowledge?: SystemComponentHealth;
    [key: string]: SystemComponentHealth | undefined;
  };
  correlation_id?: string;
}

export interface SystemMetricsResponse {
  service: string;
  version: string;
  environment: string;
  http: {
    total_requests: number;
    uptime_seconds: number;
    requests_by_status: Record<string, number>;
    avg_duration_ms: number;
    recent_latencies_ms: number[];
  };
  tasks: {
    queued: number;
    running: number;
    completed: number;
    failed: number;
    active_threads?: number;
    [key: string]: any;
  };
  correlation_id?: string;
}

export interface FHIRCapabilityInteraction {
  code: string;
  documentation?: string;
}

export interface FHIRCapabilityResource {
  type: string;
  profile?: string;
  interaction: FHIRCapabilityInteraction[];
  searchParam?: Array<Record<string, string>>;
}

export interface FHIRCapabilityStatement {
  resourceType: 'CapabilityStatement';
  id?: string;
  status: string;
  date: string;
  publisher?: string;
  kind: string;
  software?: {
    name: string;
    version: string;
  };
  implementation?: {
    description: string;
    url: string;
  };
  fhirVersion: string;
  format: string[];
  rest: Array<{
    mode: string;
    documentation?: string;
    security?: Record<string, any>;
    resource: FHIRCapabilityResource[];
  }>;
}

// ==============================================================================
// Phase 9.0.21: Enterprise EHR Integration, SMART on FHIR 2.0 & CDS Hooks
// ==============================================================================

export interface SmartConfiguration {
  authorization_endpoint: string;
  token_endpoint: string;
  introspection_endpoint?: string;
  jwks_uri: string;
  issuer?: string;
  grant_types_supported: string[];
  code_challenge_methods_supported: string[];
  scopes_supported: string[];
  response_types_supported: string[];
  capabilities: string[];
}

export interface JWKKey {
  kty: string;
  use: string;
  alg: string;
  kid: string;
  n: string;
  e: string;
}

export interface JWKSResponse {
  keys: JWKKey[];
}

export interface SmartTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  scope: string;
  id_token?: string;
  patient?: string;
  encounter?: string;
  facility_id?: string;
  smart_style_url?: string;
}

export interface SmartIntrospectResponse {
  active: boolean;
  scope?: string;
  client_id?: string;
  sub?: string;
  exp?: number;
  iat?: number;
  iss?: string;
  patient?: string;
  facility_id?: string;
}

export interface CDSService {
  hook: string;
  name: string;
  id: string;
  title: string;
  description: string;
  prefetch?: Record<string, string>;
  usageRequirements?: string;
}

export interface CDSServicesDiscoveryResponse {
  services: CDSService[];
}

export interface CDSSource {
  label: string;
  url?: string;
  icon?: string;
  topic?: Record<string, any>;
}

export interface CDSSuggestionAction {
  type: string;
  description: string;
  resource?: Record<string, any>;
}

export interface CDSSuggestion {
  label: string;
  uuid?: string;
  isRecommended?: boolean;
  actions: CDSSuggestionAction[];
}

export interface CDSLink {
  label: string;
  url: string;
  type: string;
  appContext?: string;
}

export interface CDSCard {
  uuid?: string;
  summary: string;
  detail?: string;
  indicator: 'info' | 'warning' | 'critical';
  source: CDSSource;
  suggestions?: CDSSuggestion[];
  selectionBehavior?: string;
  links?: CDSLink[];
}

export interface CDSHookResponse {
  cards: CDSCard[];
}

export interface DepartmentUnit {
  id: number;
  department_id: string;
  facility_id: string;
  name: string;
  dept_code: string;
  floor_or_wing?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClinicalFacility {
  id: number;
  facility_id: string;
  org_id: string;
  name: string;
  facility_code: string;
  address_json: Record<string, any>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  departments?: DepartmentUnit[];
}

export interface HealthOrganization {
  id: number;
  org_id: string;
  name: string;
  org_type: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  facilities?: ClinicalFacility[];
}

export interface EHRIntegrationConfig {
  id: number;
  config_id: string;
  facility_id: string;
  ehr_vendor: string;
  fhir_base_url: string;
  client_id: string;
  smart_auth_url?: string;
  smart_token_url?: string;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface TerminologyConcept {
  system: string;
  code: string;
  display: string;
  confidence: number;
  match_type: string;
  source: string;
}

export interface TerminologyNormalizeResponse {
  query: string;
  normalized?: TerminologyConcept;
  alternatives: TerminologyConcept[];
  semantic_distance: number;
  status: string;
}

export interface TerminologyCrossWalkResponse {
  source_system: string;
  source_code: string;
  target_system: string;
  target_code?: string;
  target_display?: string;
  confidence: number;
  status: string;
}

export interface WebSocketStats {
  active_telemetry_patients: number;
  active_collaboration_rooms: number;
  active_telehealth_sessions: number;
  total_connected_clients: number;
}

// ============================================================================
// Phase 9.0.22: Enterprise Reliability, Concurrency, Interoperability & MFA
// ============================================================================

export interface OutboxEvent {
  id: number;
  event_id: string;
  event_type: string;
  aggregate_type: string;
  aggregate_id: string;
  payload: Record<string, any>;
  status: 'PENDING' | 'PUBLISHED' | 'FAILED' | 'DEAD_LETTER';
  attempts: number;
  max_attempts: number;
  error_message?: string;
  retry_after?: string;
  facility_id?: string;
  created_at: string;
  published_at?: string;
}

export interface OutboxMetrics {
  total: number;
  pending: number;
  published: number;
  failed: number;
  dead_letter: number;
}

export interface MFASetupResponse {
  secret: string;
  otpauth_uri: string;
  backup_codes: string[];
  message: string;
}

export interface MFAStatusResponse {
  is_enabled: boolean;
  backup_codes_remaining: number;
  last_used_at?: string;
}

export interface MFAVerifyResponse {
  verified: boolean;
  message: string;
}

export interface FHIRSubscription {
  id: number;
  subscription_id: string;
  topic: string;
  criteria: string;
  channel_type: 'REST_HOOK' | 'WEBSOCKET' | 'EMAIL';
  endpoint_url: string;
  status: 'ACTIVE' | 'OFF' | 'ERROR';
  facility_id?: string;
  created_at: string;
}

export interface BulkExportJob {
  id: number;
  job_id: string;
  user_id: number;
  facility_id?: string;
  status: 'ACCEPTED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  resource_types_json?: string[];
  output_urls_json?: Array<{
    type: string;
    url: string;
    count?: number;
  }>;
  progress_percent: number;
  created_at: string;
  completed_at?: string;
}

// =============================================================================
// PHASE 9.0.25: REGIONAL INTEROPERABILITY, EMPI & CLINICAL PATHWAYS
// =============================================================================

export type EMPIMatchGrade = 'exact' | 'probable' | 'possible' | 'distinct';

export interface EMPICandidateMatch {
  patient_id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender: string;
  facility_id: string;
  match_score: number;
  grade: EMPIMatchGrade;
  feature_breakdown: Record<string, number>;
  enterprise_id?: string;
  address?: string;
  phone?: string;
}

export interface EMPICandidatesResponse {
  query_patient_id: string;
  total_candidates: number;
  candidates: EMPICandidateMatch[];
}

export interface EMPILinkResponse {
  enterprise_id: string;
  patient_id: string;
  facility_id: string;
  match_score: number;
  link_type: string;
  created_at: string;
}

export interface EMPIMergeResponse {
  merge_id: string;
  target_enterprise_id: string;
  source_enterprise_id: string;
  target_patient_id: string;
  source_patient_id: string;
  merged_at: string;
  message: string;
}

export interface EMPIMatchReviewItem {
  id: number;
  review_id: string;
  patient_id_a: string;
  patient_id_b: string;
  facility_id_a: string;
  facility_id_b: string;
  match_score: number;
  feature_breakdown: Record<string, number>;
  status: 'pending_review' | 'confirmed_match' | 'rejected_match';
  reviewed_by_user_id?: number;
  review_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface CCDAClinicalItem {
  display_name: string;
  code?: string;
  code_system?: string;
  status?: string;
  date_recorded?: string;
  details?: Record<string, any>;
}

export interface CCDASectionData {
  section_title: string;
  template_id: string;
  items: CCDAClinicalItem[];
}

export interface CCDAExportResponse {
  document_id: string;
  patient_id: string;
  document_type: string;
  title: string;
  created_at: string;
  sha256_hash: string;
  xml_content: string;
  section_count: number;
}

export interface CCDAImportResponse {
  document_id: string;
  patient_id: string;
  document_type: string;
  title: string;
  sha256_hash: string;
  problems_count: number;
  allergies_count: number;
  medications_count: number;
  vitals_count: number;
  sections: CCDASectionData[];
  message: string;
}

export interface CCDADocumentExchange {
  id: number;
  document_id: string;
  patient_id: string;
  facility_id: string;
  document_type: string;
  direction: 'export' | 'import';
  title: string;
  source_facility?: string;
  destination_facility?: string;
  sha256_hash: string;
  section_count: number;
  parsed_summary_json: Record<string, any>;
  created_at: string;
}

export interface PathwayMilestone {
  milestone_id: string;
  stage_id: string;
  name: string;
  criteria_code: string;
  expected_order_type?: string;
  is_critical: boolean;
}

export interface PathwayStage {
  stage_id: string;
  pathway_id: string;
  sequence_order: number;
  name: string;
  description?: string;
  assigned_facility_id?: string;
  target_duration_minutes: number;
  required_role: string;
  clinical_criteria_json: Record<string, any>;
  is_mandatory: boolean;
  milestones: PathwayMilestone[];
}

export interface RegionalPathway {
  pathway_id: string;
  code: string;
  name: string;
  category: string;
  description: string;
  tenant_id: string;
  version: number;
  target_duration_hours: number;
  is_active: boolean;
  created_at: string;
  stages: PathwayStage[];
}

export interface PathwayStageEvent {
  event_id: string;
  stage_id: string;
  facility_id: string;
  actor_user_id: number;
  transition_type: string;
  started_at: string;
  completed_at?: string;
  duration_minutes?: number;
  variance_detected: boolean;
  variance_reason?: string;
}

export interface PatientPathwayEnrollment {
  id: number;
  enrollment_id: string;
  patient_id: string;
  pathway_id: string;
  facility_id: string;
  current_stage_id: string;
  status: 'active' | 'completed' | 'suspended' | 'cancelled';
  enrolled_at: string;
  completed_at?: string;
  completed_milestones: string[];
  variance_notes?: string;
  has_variance: boolean;
  pathway?: RegionalPathway;
  events?: PathwayStageEvent[];
}

// ==============================================================================
// Phase 9.0.26: Enterprise CDS Rules, Pharmacogenomics (PGx) & Order Sets
// ==============================================================================

export type CPICLevel = 'A' | 'B' | 'C' | 'D';
export type PGxRiskSeverity = 'critical' | 'high_risk' | 'moderate' | 'informational';
export type OrderSetCategory =
  | 'emergency_trauma'
  | 'critical_care'
  | 'inpatient_admission'
  | 'oncology_precision'
  | 'surgical_perioperative'
  | 'cardiovascular'
  | 'antimicrobial_stewardship'
  | 'neurology';

export type OrderSetItemType =
  | 'medication'
  | 'laboratory'
  | 'imaging'
  | 'nursing_vital'
  | 'dietary'
  | 'consult';

export type OrderSetExecutionStatus = 'executed' | 'partially_executed' | 'cancelled';

export type CDSRuleTriggerEvent =
  | 'order_select'
  | 'order_sign'
  | 'patient_view'
  | 'encounter_discharge';

export interface PGxRuleDefinition {
  id: number;
  rule_id: string;
  cpic_level: CPICLevel;
  gene_symbol: string;
  phenotype: string;
  drug_code: string;
  drug_name: string;
  risk_severity: PGxRiskSeverity;
  clinical_implication: string;
  recommendation_text: string;
  alternative_drugs: string[];
  evidence_source?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClinicalOrderSetItem {
  id: number;
  item_id: string;
  order_set_id: string;
  item_type: OrderSetItemType;
  code: string;
  name: string;
  default_dosage?: string;
  default_route?: string;
  default_frequency?: string;
  clinical_instructions?: string;
  is_required: boolean;
  sequence_order: number;
  created_at: string;
}

export interface ClinicalOrderSet {
  id: number;
  order_set_id: string;
  code: string;
  title: string;
  description?: string;
  category: OrderSetCategory;
  target_icd10?: string;
  facility_id?: string;
  version: string;
  is_active: boolean;
  items: ClinicalOrderSetItem[];
  created_at: string;
  updated_at: string;
}

export interface CDSPGxAlertCard {
  card_id: string;
  summary: string;
  detail: string;
  indicator: 'info' | 'warning' | 'critical';
  rule_type: string;
  gene_symbol?: string;
  cpic_level?: CPICLevel;
  phenotype?: string;
  current_drug?: string;
  alternative_drugs: string[];
  links: Array<{ label: string; url: string }>;
}

export interface CDSEvaluationResponse {
  patient_id: string;
  trigger_event: CDSRuleTriggerEvent;
  has_alerts: boolean;
  highest_severity: 'info' | 'warning' | 'critical';
  cards: CDSPGxAlertCard[];
  patient_genotype_summary: Record<string, string>;
  evaluated_at: string;
}

export interface OrderSetExecuteResponse {
  execution_id: string;
  order_set_id: string;
  patient_id: string;
  facility_id: string;
  status: OrderSetExecutionStatus;
  executed_items_count: number;
  generated_order_ids: string[];
  message: string;
  created_at: string;
}

export interface CDSRuleOverrideResponse {
  audit_id: string;
  patient_id: string;
  is_overridden: boolean;
  override_reason: string;
  message: string;
  created_at: string;
}

export interface CDSRuleEvaluationAudit {
  id: number;
  audit_id: string;
  patient_id: string;
  facility_id?: string;
  rule_type: string;
  trigger_event: CDSRuleTriggerEvent;
  severity: string;
  card_summary: string;
  card_detail: string;
  is_overridden: boolean;
  override_reason?: string;
  clinician_id?: number;
  created_at: string;
}

// ==============================================================================
// Phase 9.0.27: Clinical Trial Governance, Deviations, CAPA & Multi-Center Types
// ==============================================================================

export type StudySiteStatus = 'active' | 'recruiting_closed' | 'suspended' | 'terminated';
export type DeviationSeverity = 'minor' | 'major' | 'critical';
export type DeviationCategory =
  | 'inclusion_exclusion_breach'
  | 'informed_consent_variance'
  | 'missed_study_visit'
  | 'prohibited_medication'
  | 'investigational_product_dosing_error'
  | 'laboratory_out_of_window'
  | 'safety_reporting_delay';
export type DeviationStatus =
  | 'open'
  | 'under_investigation'
  | 'capa_assigned'
  | 'resolved'
  | 'irb_notified';
export type CAPARootCause =
  | 'investigator_oversight'
  | 'patient_noncompliance'
  | 'pharmacy_dispensation_delay'
  | 'laboratory_logistics_error'
  | 'staff_training_gap'
  | 'protocol_ambiguity';
export type CAPAStatus = 'draft' | 'in_progress' | 'verification_pending' | 'closed';
export type IRBSubmissionType =
  | 'initial_deviation_report'
  | 'follow_up_capa'
  | 'prompt_safety_report_ind'
  | 'annual_continuing_review';

export interface MultiCenterStudySite {
  id: number;
  site_id: string;
  trial_id: number;
  facility_id?: string;
  principal_investigator_user_id?: number;
  site_name: string;
  target_accrual: number;
  current_enrolled: number;
  site_status: StudySiteStatus;
  irb_approval_number?: string;
  irb_approval_date?: string;
  irb_expiry_date?: string;
  created_at: string;
  updated_at: string;
}

export interface TrialProtocolDeviation {
  id: number;
  deviation_id: string;
  trial_id: number;
  site_id?: number;
  patient_id?: number;
  reported_by_user_id: number;
  deviation_category: DeviationCategory;
  severity: DeviationSeverity;
  status: DeviationStatus;
  description: string;
  occurred_at: string;
  discovered_at: string;
  impact_on_patient_safety?: string;
  impact_on_data_integrity?: string;
  requires_irb_submission: boolean;
  irb_submitted_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TrialCAPARecord {
  id: number;
  capa_id: string;
  deviation_id: number;
  root_cause_category: CAPARootCause;
  root_cause_analysis: string;
  corrective_action: string;
  preventive_action: string;
  assigned_owner_user_id: number;
  target_resolution_date: string;
  actual_resolution_date?: string;
  status: CAPAStatus;
  effectiveness_check_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface TrialIRBNotification {
  id: number;
  notification_id: string;
  deviation_id: number;
  irb_committee_name: string;
  submission_type: IRBSubmissionType;
  document_content_json: Record<string, any>;
  submitted_by_user_id: number;
  submission_timestamp: string;
  acknowledgement_reference?: string;
  created_at: string;
}

export interface TrialPrescreenMatchCriterionResult {
  criterion_id: string;
  category: string;
  criterion_type: string;
  description: string;
  is_met: boolean;
  patient_value?: string;
  required: boolean;
}

export interface TrialPrescreenEvaluationItem {
  trial_id: number;
  nct_number?: string;
  title: string;
  phase: string;
  disease_condition: string;
  eligibility_score: number;
  is_eligible: boolean;
  matched_criteria_count: number;
  total_criteria_count: number;
  disqualifying_reasons: string[];
  criteria_results: TrialPrescreenMatchCriterionResult[];
}

export interface TrialPrescreenEvaluationResponse {
  patient_id: string;
  evaluated_at: string;
  total_trials_screened: number;
  eligible_trials_count: number;
  evaluations: TrialPrescreenEvaluationItem[];
}

export interface SiteAccrualMetric {
  site_id: string;
  site_name: string;
  facility_id?: string;
  target_accrual: number;
  current_enrolled: number;
  accrual_percentage: number;
  open_deviations_count: number;
  critical_deviations_count: number;
  status: StudySiteStatus;
}

export interface MultiCenterTrialGovernanceSummary {
  trial_id: number;
  trial_title: string;
  total_target_accrual: number;
  total_enrolled: number;
  overall_accrual_rate: number;
  active_sites_count: number;
  total_deviations_count: number;
  open_capas_count: number;
  sites_metrics: SiteAccrualMetric[];
}

// ==============================================================================
// Phase 9.0.28: Closed-Loop eMAR & Barcode BCMA Interfaces
// ==============================================================================

export type MARStatus = 'scheduled' | 'administered' | 'held' | 'refused' | 'missed' | 'discontinued';
export type BCMAVerificationStatus = 'pass' | 'warning_override' | 'mismatch_rejected';
export type HighAlertMedicationCategory =
  | 'insulin'
  | 'anticoagulant'
  | 'opioid_narcotic'
  | 'chemotherapy'
  | 'neuromuscular_blocker'
  | 'concentrated_electrolyte'
  | 'general';

export interface MedicationBarcodeItem {
  id: number;
  barcode: string;
  medication_name: string;
  rxnorm_code: string;
  ndc_code?: string;
  standard_dose: string;
  dosage_form: string;
  route: string;
  is_high_alert: boolean;
  high_alert_category?: HighAlertMedicationCategory;
  is_active: boolean;
  created_at: string;
}

export interface MedicationBarcodeListResponse {
  total: number;
  items: MedicationBarcodeItem[];
}

export interface MARRecord {
  id: number;
  mar_id: string;
  order_id?: number;
  patient_id: number;
  patient_identifier?: string;
  facility_id: string;
  medication_name: string;
  medication_code: string;
  prescribed_dose: string;
  prescribed_route: string;
  prescribed_frequency: string;
  scheduled_time: string;
  actual_admin_time?: string;
  status: MARStatus;
  administering_nurse_id?: number;
  administering_nurse_name?: string;
  administered_dose?: string;
  administered_route?: string;
  site_of_administration?: string;
  is_high_alert: boolean;
  requires_dual_witness: boolean;
  dual_witness_user_id?: number;
  dual_witness_user_name?: string;
  dual_witness_timestamp?: string;
  variance_reason?: string;
  patient_response_notes?: string;
  vital_signs_pre_admin_json?: Record<string, any>;
  barcode_scanned_patient_id?: string;
  barcode_scanned_med_id?: string;
  verification_passed: boolean;
  created_at: string;
  updated_at: string;
}

export interface MARScheduleListResponse {
  total: number;
  records: MARRecord[];
}

export interface RightVerificationResult {
  passed: boolean;
  expected: string;
  scanned: string;
  details?: string;
}

export interface BCMAVerify5RightsResponse {
  verification_status: BCMAVerificationStatus;
  overall_passed: boolean;
  patient_verification: RightVerificationResult;
  medication_verification: RightVerificationResult;
  dose_verification: RightVerificationResult;
  route_verification: RightVerificationResult;
  time_verification: RightVerificationResult;
  is_high_alert: boolean;
  requires_dual_signoff: boolean;
  matched_mar_record?: MARRecord;
  discrepancy_warnings: string[];
  verification_token: string;
  timestamp: string;
}

export interface MARScheduleDosesPayload {
  patient_id: string;
  order_id?: number;
  facility_id?: string;
  medication_name: string;
  medication_code: string;
  prescribed_dose: string;
  prescribed_route: string;
  frequency_code: string;
  start_time?: string;
  total_doses?: number;
  is_high_alert?: boolean;
  requires_dual_witness?: boolean;
}

export interface MARAdministerPayload {
  administered_dose?: string;
  administered_route?: string;
  site_of_administration?: string;
  scanned_patient_barcode?: string;
  scanned_med_barcode?: string;
  vital_signs_pre_admin?: Record<string, any>;
  variance_reason?: string;
  patient_response_notes?: string;
}

export interface MARHoldRefusePayload {
  status: MARStatus;
  clinical_reason: string;
  patient_response_notes?: string;
}

export interface DualSignoffPayload {
  witness_user_email: string;
  witness_password: string;
  witness_notes?: string;
}

// =============================================================================
// Phase 9.0.29: DICOM PACS Medical Imaging & Real-Time Waveforms
// =============================================================================

export type DICOMModality = 'CT' | 'MR' | 'CR' | 'DX' | 'US' | 'XA' | 'NM' | 'PT' | 'ECG' | 'OTHER';

export type AIFindingReviewStatus = 'pending_review' | 'confirmed' | 'rejected' | 'amended';

export type ArrhythmiaEventType =
  | 'stemi_elevation'
  | 'atrial_fibrillation'
  | 'ventricular_tachycardia'
  | 'asystole'
  | 'severe_bradycardia'
  | 'pvc_bigeminy'
  | 'normal_sinus_rhythm';

export type ArrhythmiaAlertSeverity = 'critical' | 'warning' | 'advisory';

export type AlertLifecycleStatus = 'active' | 'acknowledged' | 'resolved' | 'false_positive';

export interface AILesionFindingItem {
  id: number;
  finding_id: string;
  instance_id: number;
  lesion_type: string;
  anatomical_location: string;
  confidence_score: number;
  severity: string;
  geometry_type: string;
  coordinates_json: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
  heatmap_matrix_json?: Record<string, any>;
  model_name: string;
  model_version: string;
  clinician_review_status: AIFindingReviewStatus;
  reviewed_by_user_id?: number;
  review_notes?: string;
  reviewed_at?: string;
  created_at: string;
}

export interface DICOMInstanceItem {
  id: number;
  sop_instance_uid: string;
  series_id: number;
  sop_class_uid: string;
  instance_number: number;
  rows: number;
  columns: number;
  bits_allocated: number;
  bits_stored: number;
  high_bit: number;
  pixel_representation: number;
  photometric_interpretation: string;
  storage_path: string;
  thumbnail_path?: string;
  pixel_data_preview_url?: string;
  ai_findings: AILesionFindingItem[];
  created_at: string;
}

export interface DICOMSeriesItem {
  id: number;
  series_instance_uid: string;
  study_id: number;
  series_number: number;
  series_description: string;
  modality: DICOMModality;
  body_part_examined: string;
  patient_position: string;
  slice_thickness_mm?: number;
  pixel_spacing_row_mm?: number;
  pixel_spacing_col_mm?: number;
  window_center_default: number;
  window_width_default: number;
  rescale_intercept: number;
  rescale_slope: number;
  number_of_instances: number;
  instances: DICOMInstanceItem[];
  created_at: string;
}

export interface DICOMStudyItem {
  id: number;
  study_instance_uid: string;
  study_id: string;
  patient_id: number;
  patient_identifier?: string;
  facility_id: string;
  accession_number: string;
  study_description: string;
  modality: DICOMModality;
  body_site: string;
  study_datetime: string;
  referring_physician?: string;
  performing_institution: string;
  number_of_series: number;
  number_of_instances: number;
  dicom_attributes_json?: Record<string, any>;
  series_list: DICOMSeriesItem[];
  created_at: string;
  updated_at: string;
}

export interface DICOMStudyListResponse {
  total: number;
  studies: DICOMStudyItem[];
}

export interface ArrhythmiaAlertItem {
  id: number;
  alert_id: string;
  session_id: number;
  patient_id: number;
  event_type: ArrhythmiaEventType;
  severity: ArrhythmiaAlertSeverity;
  lead_involved: string;
  heart_rate_bpm: number;
  st_elevation_mm?: number;
  alert_description: string;
  status: AlertLifecycleStatus;
  triggered_at: string;
  cooldown_until: string;
  acknowledged_by_user_id?: number;
  acknowledged_at?: string;
  clinician_action_taken?: string;
}

export interface ECGSessionItem {
  id: number;
  session_id: string;
  patient_id: number;
  patient_identifier?: string;
  facility_id: string;
  encounter_id?: number;
  device_id: string;
  lead_configuration: string;
  sample_rate_hz: number;
  amplitude_unit: string;
  start_time: string;
  duration_seconds: number;
  current_rhythm_state: ArrhythmiaEventType;
  heart_rate_bpm: number;
  multi_lead_samples_json: Record<string, number[]>;
  is_active_streaming: boolean;
  alerts: ArrhythmiaAlertItem[];
  created_at: string;
}

export interface ECGSessionListResponse {
  total: number;
  sessions: ECGSessionItem[];
}

