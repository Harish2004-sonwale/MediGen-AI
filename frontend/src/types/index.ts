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
