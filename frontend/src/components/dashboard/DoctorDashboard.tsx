// ==============================================================================
// MediGen AI - Doctor & Clinical Staff Intelligence Dashboard
// ==============================================================================

import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { usePatient } from '../../context/PatientContext';
import { useTasks } from '../../hooks/useTasks';
import { Header } from '../layout/Header';
import { PatientRibbon } from '../layout/PatientRibbon';
import { PatientDirectory } from '../patients/PatientDirectory';
import { ClinicalChat } from '../chat/ClinicalChat';
import { TimelineView } from '../timeline/TimelineView';
import { DocumentHub } from '../documents/DocumentHub';
import { MediaDiagnosticsHub } from '../media/MediaDiagnosticsHub';
import { ClinicalNoteWorkspace } from '../notes/ClinicalNoteWorkspace';
import { VitalTelemetryWorkspace } from '../telemetry/VitalTelemetryWorkspace';
import { CarePlanWorkspace } from '../care/CarePlanWorkspace';
import { CohortWorkspace } from '../cohorts/CohortWorkspace';
import { TransitionsWorkspace } from '../transitions/TransitionsWorkspace';
import { OrdersWorkspace } from '../orders/OrdersWorkspace';
import { QualityMeasuresWorkspace } from '../quality/QualityMeasuresWorkspace';
import { RPMWorkspace } from '../rpm/RPMWorkspace';
import { TrialsPrecisionWorkspace } from '../trials/TrialsPrecisionWorkspace';
import { ClinicalAgentsWorkspace } from '../agents/ClinicalAgentsWorkspace';
import { ImagingRadiologyWorkspace } from '../imaging/ImagingRadiologyWorkspace';
import { SecurityComplianceWorkspace } from '../security/SecurityComplianceWorkspace';
import { SystemDiagnosticsWorkspace } from '../operations/SystemDiagnosticsWorkspace';
import { SmartFhirEhrWorkspace } from '../interop/SmartFhirEhrWorkspace';
import { LiveCollaborationWorkspace } from '../collaboration/LiveCollaborationWorkspace';
import { HealthSystemTenantWorkspace } from '../tenants/HealthSystemTenantWorkspace';
import { RegionalInteroperabilityWorkspace } from '../interop/RegionalInteroperabilityWorkspace';
import { CDSPGxOrderSetWorkspace } from '../cds/CDSPGxOrderSetWorkspace';
import { TrialsGovernanceWorkspace } from '../trials/TrialsGovernanceWorkspace';
import { EMARClosedLoopWorkspace } from '../emar/EMARClosedLoopWorkspace';
import { DICOMPACSViewerWorkspace } from '../pacs/DICOMPACSViewerWorkspace';
import { SafetyPrescriberModal } from '../safety/SafetyPrescriberModal';
import { TaskMonitor } from '../tasks/TaskMonitor';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { CarePlanCategory, NoteType } from '../../types';
import { mediaApi, notesApi, carePlansApi, appointmentsApi } from '../../api/client';

type TabType =
  | 'chat'
  | 'timeline'
  | 'documents'
  | 'media'
  | 'notes'
  | 'vitals'
  | 'care_plans'
  | 'cohorts'
  | 'transitions'
  | 'orders'
  | 'quality'
  | 'rpm'
  | 'trials'
  | 'agents'
  | 'imaging'
  | 'security'
  | 'diagnostics'
  | 'smart_ehr'
  | 'collaboration'
  | 'tenants'
  | 'regional_interop'
  | 'cds_pgx'
  | 'trials_governance'
  | 'emar'
  | 'pacs_waveforms';

type CategoryType = 'all' | 'clinical' | 'medications' | 'diagnostics' | 'ai_cds' | 'telehealth' | 'interop';

export const DoctorDashboard: React.FC = () => {
  const { user } = useAuth();
  const { selectedPatient, patients, selectPatientById } = usePatient();
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  const [activeCategory, setActiveCategory] = useState<CategoryType>('all');
  const [isSafetyModalOpen, setIsSafetyModalOpen] = useState(false);
  const [isTasksModalOpen, setIsTasksModalOpen] = useState(false);
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);

  // Appointment Form State
  const [appointmentDate, setAppointmentDate] = useState('2026-09-20T10:30');
  const [consultMode, setConsultMode] = useState('in_person');
  const [durationMins, setDurationMins] = useState(30);
  const [reasonForVisit, setReasonForVisit] = useState('Cardiology Clinical Follow-up');
  const [isScheduling, setIsScheduling] = useState(false);
  const [scheduleSuccess, setScheduleSuccess] = useState<string | null>(null);

  const { tasks, loadTasks, retryTask, cancelTask, triggerDocumentOCR } = useTasks(
    selectedPatient?.patient_id
  );

  const triggerMediaAnalysis = async (mediaId: string) => {
    await mediaApi.enqueueAnalysis(mediaId);
    await loadTasks();
  };

  const triggerNoteSynthesis = async (noteType: NoteType) => {
    if (!selectedPatient) return;
    await notesApi.enqueueSynthesis(selectedPatient.patient_id, noteType);
    await loadTasks();
  };

  const triggerCarePlanSynthesis = async (category: CarePlanCategory, customInstructions?: string) => {
    if (!selectedPatient) return;
    await carePlansApi.enqueueSynthesis(selectedPatient.patient_id, category, customInstructions);
    await loadTasks();
  };

  const handleCreateAppointment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatient) return;
    setIsScheduling(true);
    try {
      await appointmentsApi.create({
        patient_id: selectedPatient.id,
        doctor_id: 1,
        appointment_date: new Date(appointmentDate).toISOString(),
        duration_minutes: durationMins,
        consultation_mode: consultMode,
        reason_for_visit: reasonForVisit.trim() || 'Clinical Follow-up',
      });
      setScheduleSuccess(`Appointment scheduled for ${selectedPatient.first_name} ${selectedPatient.last_name} on ${new Date(appointmentDate).toLocaleDateString()}.`);
      setTimeout(() => setScheduleSuccess(null), 5000);
      setIsScheduleModalOpen(false);
    } catch (err: any) {
      alert(err.message || 'Failed to schedule appointment');
    } finally {
      setIsScheduling(false);
    }
  };

  const activeTaskCount = tasks.filter(
    (t) => t.status === 'queued' || t.status === 'running' || t.status === 'retrying'
  ).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', background: 'var(--bg-primary, #0b0f19)' }}>
      {/* Top Application Header */}
      <Header
        onOpenSafetyModal={() => setIsSafetyModalOpen(true)}
        onOpenTasksModal={() => setIsTasksModalOpen(true)}
        activeTaskCount={activeTaskCount}
      />

      {/* Active Patient Context Ribbon */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)' }}>
        <div style={{ flex: 1 }}>
          <PatientRibbon />
        </div>
        <div style={{ padding: '0 16px', display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={() => setIsScheduleModalOpen(true)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem' }}
          >
            📅 Schedule Consultation
          </button>
        </div>
      </div>

      {scheduleSuccess && (
        <div style={{ background: '#065f46', color: '#a7f3d0', padding: '8px 24px', textAlign: 'center', fontSize: '0.85rem' }}>
          ✅ {scheduleSuccess}
        </div>
      )}

      {/* Main Clinical Dashboard Grid */}
      <main className="dashboard-grid" style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {/* Left Column: Patient Directory */}
        <section style={{ height: '100%', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          <ErrorBoundary fallbackTitle="Patient Directory">
            <PatientDirectory />
          </ErrorBoundary>
        </section>

        {/* Center Column: Interactive Workspaces */}
        <section style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '8px', minHeight: 0, overflow: 'hidden' }}>
          {/* Primary Navigation Category Bar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 0',
              borderBottom: '1px solid rgba(255,255,255,0.08)',
              overflowX: 'auto',
              flexShrink: 0,
            }}
          >
            <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 700, paddingRight: '4px' }}>
              View:
            </span>
            <button
              className={`btn btn-xs ${activeCategory === 'all' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveCategory('all')}
              style={{ padding: '3px 10px', fontSize: '0.75rem' }}
            >
              ⭐ All Modules
            </button>
            <button
              className={`btn btn-xs ${activeCategory === 'clinical' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveCategory('clinical')}
              style={{ padding: '3px 10px', fontSize: '0.75rem' }}
            >
              📋 Clinical Care
            </button>
            <button
              className={`btn btn-xs ${activeCategory === 'medications' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveCategory('medications')}
              style={{ padding: '3px 10px', fontSize: '0.75rem' }}
            >
              💊 Medications & Orders
            </button>
            <button
              className={`btn btn-xs ${activeCategory === 'diagnostics' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveCategory('diagnostics')}
              style={{ padding: '3px 10px', fontSize: '0.75rem' }}
            >
              🔬 Diagnostics & PACS
            </button>
            <button
              className={`btn btn-xs ${activeCategory === 'ai_cds' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveCategory('ai_cds')}
              style={{ padding: '3px 10px', fontSize: '0.75rem' }}
            >
              🤖 AI Copilot & CDS
            </button>
            <button
              className={`btn btn-xs ${activeCategory === 'telehealth' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveCategory('telehealth')}
              style={{ padding: '3px 10px', fontSize: '0.75rem' }}
            >
              📡 Telehealth
            </button>
            <button
              className={`btn btn-xs ${activeCategory === 'interop' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveCategory('interop')}
              style={{ padding: '3px 10px', fontSize: '0.75rem' }}
            >
              🌐 Interoperability
            </button>
          </div>

          {/* Module Action Subtabs (Dynamic & Scrollable with all data-testids) */}
          <div
            style={{
              display: 'flex',
              gap: '6px',
              paddingBottom: '6px',
              borderBottom: '1px solid var(--border-color)',
              overflowX: 'auto',
              flexWrap: 'wrap',
              flexShrink: 0,
            }}
          >
            {/* Clinical Workspaces */}
            {(activeCategory === 'all' || activeCategory === 'clinical') && (
              <>
                <button
                  className={`btn btn-sm ${activeTab === 'chat' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('chat')}
                >
                  💬 AI Copilot & Chat
                </button>
                <button
                  className={`btn btn-sm ${activeTab === 'timeline' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('timeline')}
                >
                  📅 Longitudinal Timeline
                </button>
                <button
                  className={`btn btn-sm ${activeTab === 'vitals' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('vitals')}
                >
                  💓 Vitals & CDS Alerts
                </button>
                <button
                  className={`btn btn-sm ${activeTab === 'notes' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('notes')}
                >
                  📝 Clinical Notes
                </button>
                <button
                  className={`btn btn-sm ${activeTab === 'care_plans' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('care_plans')}
                >
                  📋 Care Plans & Tasks
                </button>
                <button
                  className={`btn btn-sm ${activeTab === 'transitions' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('transitions')}
                >
                  🔄 Transitions & Discharge
                </button>
              </>
            )}

            {/* Medications Workspaces */}
            {(activeCategory === 'all' || activeCategory === 'medications') && (
              <>
                <button
                  className={`btn btn-sm ${activeTab === 'orders' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('orders')}
                >
                  📦 Orders & Prescriptions
                </button>
                <button
                  data-testid="tab-btn-emar"
                  className={`btn btn-sm ${activeTab === 'emar' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('emar')}
                >
                  💊 Closed-Loop eMAR & BCMA
                </button>
              </>
            )}

            {/* Diagnostics & Imaging Workspaces */}
            {(activeCategory === 'all' || activeCategory === 'diagnostics') && (
              <>
                <button
                  className={`btn btn-sm ${activeTab === 'documents' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('documents')}
                >
                  📁 Medical Documents
                </button>
                <button
                  className={`btn btn-sm ${activeTab === 'media' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('media')}
                >
                  🖼️ Diagnostics & Media
                </button>
                <button
                  data-testid="tab-btn-imaging"
                  className={`btn btn-sm ${activeTab === 'imaging' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('imaging')}
                >
                  🩻 Radiology & AI Heatmaps
                </button>
                <button
                  data-testid="tab-btn-pacs-waveforms"
                  className={`btn btn-sm ${activeTab === 'pacs_waveforms' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('pacs_waveforms')}
                >
                  🖼️ DICOM PACS & Waveforms
                </button>
              </>
            )}

            {/* AI & Decision Support */}
            {(activeCategory === 'all' || activeCategory === 'ai_cds') && (
              <>
                <button
                  data-testid="tab-btn-agents"
                  className={`btn btn-sm ${activeTab === 'agents' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('agents')}
                >
                  🤖 Clinical AI Agents
                </button>
                <button
                  data-testid="tab-btn-cds-pgx"
                  className={`btn btn-sm ${activeTab === 'cds_pgx' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('cds_pgx')}
                >
                  🧬 CDS Rules, PGx & Order Sets
                </button>
                <button
                  data-testid="tab-btn-trials"
                  className={`btn btn-sm ${activeTab === 'trials' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('trials')}
                >
                  🧬 Precision Oncology & Trials
                </button>
              </>
            )}

            {/* Telehealth & Coordination */}
            {(activeCategory === 'all' || activeCategory === 'telehealth') && (
              <>
                <button
                  className={`btn btn-sm ${activeTab === 'rpm' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('rpm')}
                >
                  📡 Remote Monitoring & RPM
                </button>
                <button
                  className={`btn btn-sm ${activeTab === 'cohorts' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('cohorts')}
                >
                  👥 Population Analytics
                </button>
                <button
                  data-testid="tab-btn-collaboration"
                  className={`btn btn-sm ${activeTab === 'collaboration' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('collaboration')}
                >
                  🔴 Live Telemetry & Collaboration
                </button>
              </>
            )}

            {/* Interoperability & Governance */}
            {(activeCategory === 'all' || activeCategory === 'interop') && (
              <>
                <button
                  data-testid="tab-btn-smart-ehr"
                  className={`btn btn-sm ${activeTab === 'smart_ehr' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('smart_ehr')}
                >
                  🔌 SMART on FHIR & CDS Hooks
                </button>
                <button
                  data-testid="tab-btn-regional-interop"
                  className={`btn btn-sm ${activeTab === 'regional_interop' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('regional_interop')}
                >
                  🌐 Regional Interoperability & EMPI
                </button>
                <button
                  className={`btn btn-sm ${activeTab === 'quality' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('quality')}
                >
                  📊 Quality & CQM Measures
                </button>
                <button
                  data-testid="tab-btn-trials-governance"
                  className={`btn btn-sm ${activeTab === 'trials_governance' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('trials_governance')}
                >
                  🏛️ Trials Governance & GCP
                </button>
                <button
                  data-testid="tab-btn-security"
                  className={`btn btn-sm ${activeTab === 'security' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('security')}
                >
                  🛡️ Security & Compliance
                </button>
                <button
                  data-testid="tab-btn-diagnostics"
                  className={`btn btn-sm ${activeTab === 'diagnostics' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('diagnostics')}
                >
                  ⚙️ System Diagnostics
                </button>
                <button
                  data-testid="tab-btn-tenants"
                  className={`btn btn-sm ${activeTab === 'tenants' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setActiveTab('tenants')}
                >
                  🏥 Facilities & Tenants
                </button>
              </>
            )}
          </div>

          {/* Active Workspace View (Scrollable & Wrapped in ErrorBoundary) */}
          <div style={{ flex: 1, minHeight: 0, overflowY: 'auto' }}>
            <ErrorBoundary fallbackTitle={`Workspace Error: ${activeTab}`}>
              {activeTab === 'chat' && <ClinicalChat patientId={selectedPatient?.patient_id} />}
              {activeTab === 'timeline' && <TimelineView patientId={selectedPatient?.patient_id} />}
              {activeTab === 'documents' && (
                <DocumentHub
                  patientId={selectedPatient?.patient_id}
                  onTriggerOCR={triggerDocumentOCR}
                />
              )}
              {activeTab === 'media' && (
                <MediaDiagnosticsHub
                  patientId={selectedPatient?.patient_id}
                  onTriggerAnalysis={triggerMediaAnalysis}
                />
              )}
              {activeTab === 'notes' && (
                <ClinicalNoteWorkspace
                  patientId={selectedPatient?.patient_id}
                  onTriggerSynthesis={triggerNoteSynthesis}
                />
              )}
              {activeTab === 'vitals' && (
                <VitalTelemetryWorkspace
                  patientId={selectedPatient?.patient_id}
                />
              )}
              {activeTab === 'care_plans' && (
                <CarePlanWorkspace
                  patientId={selectedPatient?.patient_id}
                  onTriggerSynthesis={triggerCarePlanSynthesis}
                />
              )}
              {activeTab === 'cohorts' && (
                <CohortWorkspace
                  currentUser={user}
                  currentPatientId={selectedPatient?.patient_id}
                  onSelectPatient={(pid) => selectPatientById(pid)}
                />
              )}
              {activeTab === 'transitions' && (
                <TransitionsWorkspace
                  patientId={selectedPatient?.patient_id}
                  currentUser={user}
                />
              )}
              {activeTab === 'orders' && <OrdersWorkspace />}
              {activeTab === 'quality' && <QualityMeasuresWorkspace />}
              {activeTab === 'rpm' && (
                <RPMWorkspace
                  currentUser={user}
                  activePatient={selectedPatient}
                />
              )}
              {activeTab === 'trials' && (
                <TrialsPrecisionWorkspace
                  initialPatientId={selectedPatient?.patient_id}
                />
              )}
              {activeTab === 'agents' && (
                <ClinicalAgentsWorkspace />
              )}
              {activeTab === 'imaging' && (
                <ImagingRadiologyWorkspace
                  currentUser={user}
                  selectedPatientId={selectedPatient?.patient_id}
                />
              )}
              {activeTab === 'security' && (
                <SecurityComplianceWorkspace
                  patients={patients}
                  selectedPatient={selectedPatient}
                  onSelectPatient={(p) => selectPatientById(p.patient_id)}
                />
              )}
              {activeTab === 'diagnostics' && (
                <SystemDiagnosticsWorkspace />
              )}
              {activeTab === 'smart_ehr' && (
                <SmartFhirEhrWorkspace selectedPatientId={selectedPatient?.patient_id} />
              )}
              {activeTab === 'collaboration' && (
                <LiveCollaborationWorkspace selectedPatientId={selectedPatient?.patient_id} />
              )}
              {activeTab === 'tenants' && (
                <HealthSystemTenantWorkspace />
              )}
              {activeTab === 'regional_interop' && (
                <RegionalInteroperabilityWorkspace />
              )}
              {activeTab === 'cds_pgx' && (
                <CDSPGxOrderSetWorkspace />
              )}
              {activeTab === 'trials_governance' && (
                <TrialsGovernanceWorkspace />
              )}
              {activeTab === 'emar' && (
                <EMARClosedLoopWorkspace />
              )}
              {activeTab === 'pacs_waveforms' && (
                <DICOMPACSViewerWorkspace patientId={selectedPatient?.patient_id || 'PAT-00101'} />
              )}
            </ErrorBoundary>
          </div>
        </section>

        {/* Right Column: Longitudinal Timeline Mini-Feed */}
        <section className="right-sidebar" style={{ height: '100%', minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <ErrorBoundary fallbackTitle="Timeline Stream">
            <div style={{ flex: 1, minHeight: 0 }}>
              <TimelineView patientId={selectedPatient?.patient_id} />
            </div>
          </ErrorBoundary>
        </section>
      </main>

      {/* Safety Decision Support Modal */}
      <SafetyPrescriberModal
        patientId={selectedPatient?.patient_id}
        isOpen={isSafetyModalOpen}
        onClose={() => setIsSafetyModalOpen(false)}
      />

      {/* Task Monitor Modal */}
      <TaskMonitor
        tasks={tasks}
        isOpen={isTasksModalOpen}
        onClose={() => setIsTasksModalOpen(false)}
        onRetry={retryTask}
        onCancel={cancelTask}
        onRefresh={loadTasks}
      />

      {/* Schedule Consultation Modal */}
      {isScheduleModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            background: 'rgba(5, 10, 20, 0.85)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '20px',
          }}
        >
          <div className="glass-panel" style={{ width: '100%', maxWidth: '520px', padding: '24px', borderRadius: '12px', background: '#0f172a' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0, color: '#38bdf8' }}>
                Schedule Clinical Consultation
              </h3>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setIsScheduleModalOpen(false)}>✕</button>
            </div>

            <div style={{ padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', marginBottom: '16px' }}>
              <div style={{ fontWeight: 600, color: '#ffffff', fontSize: '0.9rem' }}>
                Patient: {selectedPatient?.first_name} {selectedPatient?.last_name} ({selectedPatient?.patient_id})
              </div>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '4px' }}>
                Attending: Dr. Amit Kulkarni &bull; Cardiology & Internal Medicine
              </div>
            </div>

            <form onSubmit={handleCreateAppointment} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div className="form-group">
                <label className="form-label" style={{ color: '#cbd5e1' }}>Appointment Date & Time *</label>
                <input
                  type="datetime-local"
                  className="form-input"
                  value={appointmentDate}
                  onChange={(e) => setAppointmentDate(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label" style={{ color: '#cbd5e1' }}>Consultation Mode</label>
                  <select
                    className="form-input"
                    value={consultMode}
                    onChange={(e) => setConsultMode(e.target.value)}
                  >
                    <option value="in_person">In-Person Consultation</option>
                    <option value="telehealth">Telehealth / Video Call</option>
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label" style={{ color: '#cbd5e1' }}>Duration (Minutes)</label>
                  <select
                    className="form-input"
                    value={durationMins}
                    onChange={(e) => setDurationMins(Number(e.target.value))}
                  >
                    <option value={15}>15 Minutes (Follow-up)</option>
                    <option value={30}>30 Minutes (Standard)</option>
                    <option value={45}>45 Minutes (Comprehensive)</option>
                    <option value={60}>60 Minutes (Initial Intake)</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" style={{ color: '#cbd5e1' }}>Reason for Consultation *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Follow-up for chest tightness and ECG review"
                  value={reasonForVisit}
                  onChange={(e) => setReasonForVisit(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setIsScheduleModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={isScheduling}>
                  {isScheduling ? 'Scheduling...' : 'Confirm Appointment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

