// ==============================================================================
// MediGen AI - Doctor & Clinical Staff Intelligence Dashboard
// Clinician Workspace, EHR Patient Workspace, Diagnostic Hubs, AI Copilot & PACS
// ==============================================================================

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { usePatient } from '../../context/PatientContext';
import { useTasks } from '../../hooks/useTasks';
import { AppShell } from '../layout/AppShell';
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
import { CarePlanCategory, NoteType, Appointment } from '../../types';
import { mediaApi, notesApi, carePlansApi, appointmentsApi } from '../../api/client';

export const DoctorDashboard: React.FC = () => {
  const { user } = useAuth();
  const { selectedPatient, patients, selectPatientById } = usePatient();
  const [activeSection, setActiveSection] = useState<string>('overview');
  const [isSafetyModalOpen, setIsSafetyModalOpen] = useState(false);
  const [isTasksModalOpen, setIsTasksModalOpen] = useState(false);
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);

  // Appointment Form State
  const [appointmentDate, setAppointmentDate] = useState('');
  const [consultMode, setConsultMode] = useState('in_person');
  const [durationMins, setDurationMins] = useState(30);
  const [reasonForVisit, setReasonForVisit] = useState('');
  const [isScheduling, setIsScheduling] = useState(false);
  const [scheduleSuccess, setScheduleSuccess] = useState<string | null>(null);
  const [doctorAppointments, setDoctorAppointments] = useState<Appointment[]>([]);

  const { tasks, loadTasks, retryTask, cancelTask, triggerDocumentOCR } = useTasks(
    selectedPatient?.patient_id
  );

  const loadAppointments = async () => {
    try {
      const res = await appointmentsApi.list();
      setDoctorAppointments(Array.isArray(res) ? res : ((res as any)?.items || []));
    } catch {
      setDoctorAppointments([]);
    }
  };

  useEffect(() => {
    loadAppointments();
  }, []);

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
        reason_for_visit: reasonForVisit.trim(),
      });
      setScheduleSuccess(`Appointment scheduled successfully for ${selectedPatient.first_name} ${selectedPatient.last_name}.`);
      setIsScheduleModalOpen(false);
      loadAppointments();
      setTimeout(() => setScheduleSuccess(null), 5000);
    } catch (err: any) {
      alert(err.message || 'Failed to schedule appointment. Please check for scheduling conflicts.');
    } finally {
      setIsScheduling(false);
    }
  };

  const activeTaskCount = tasks.filter((t) => t.status === 'running' || t.status === 'queued' || t.status === 'retrying').length;

  const getSectionTitle = () => {
    switch (activeSection) {
      case 'overview': return 'Clinician Workspace & Overview';
      case 'chat': return 'AI Clinical Copilot & AI Scribe';
      case 'timeline': return 'Longitudinal Patient Timeline';
      case 'notes': return 'Clinical Notes & Documentation';
      case 'vitals': return 'Vital Signs & Telemetry Alerts';
      case 'care_plans': return 'Care Plans & Interventions';
      case 'transitions': return 'Care Transitions & Discharge';
      case 'orders': return 'Orders & Prescriptions';
      case 'emar': return 'Closed-Loop eMAR & BCMA';
      case 'cds_pgx': return 'CDS Rules, Pharmacogenomics & Order Sets';
      case 'documents': return 'Medical Document Hub & OCR';
      case 'media': return 'Diagnostics & Clinical Media';
      case 'imaging': return 'Radiology AI & Grad-CAM Heatmaps';
      case 'pacs_waveforms': return 'DICOM PACS & ECG Waveforms';
      case 'collaboration': return 'Live Telehealth Consultation';
      case 'cohorts': return 'Population & Cohort Analytics';
      case 'trials': return 'Precision Oncology & Clinical Trials';
      case 'agents': return 'Autonomous AI Clinical Agents';
      case 'quality': return 'Quality Measures & CQM Performance';
      case 'smart_ehr': return 'SMART on FHIR Gateway';
      default: return 'Clinical Workspace';
    }
  };

  return (
    <AppShell
      activeSection={activeSection}
      activeSectionTitle={getSectionTitle()}
      onSelectSection={setActiveSection}
      onOpenSafetyModal={() => setIsSafetyModalOpen(true)}
      onOpenTasksModal={() => setIsTasksModalOpen(true)}
      activeTaskCount={activeTaskCount}
    >
      {/* Schedule Success Toast */}
      {scheduleSuccess && (
        <div
          style={{
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid #10b981',
            color: '#34d399',
            padding: '10px 16px',
            borderRadius: '8px',
            fontSize: '0.85rem',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span>✅ {scheduleSuccess}</span>
          <button onClick={() => setScheduleSuccess(null)} style={{ background: 'none', border: 'none', color: '#34d399', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* 1. CLINICAL OVERVIEW SECTION */}
      {activeSection === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Welcome & Quick Action Banner */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffffff' }}>
                Clinical Intelligence Center
              </h1>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Clinical Practice & Patient Care Workspace
              </p>
            </div>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <button
                onClick={() => setIsScheduleModalOpen(true)}
                className="btn btn-primary"
                style={{ fontSize: '0.8125rem' }}
              >
                📅 Schedule Consultation
              </button>
              <button
                onClick={() => setActiveSection('chat')}
                className="btn btn-secondary"
                style={{ fontSize: '0.8125rem' }}
              >
                💬 Ask AI Copilot
              </button>
              <button
                onClick={() => setActiveSection('pacs_waveforms')}
                className="btn btn-secondary"
                style={{ fontSize: '0.8125rem' }}
              >
                🫀 DICOM / ECG Viewer
              </button>
            </div>
          </div>

          {/* Clinician Stat KPIs */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
            <div className="stat-card" style={{ borderLeft: '3px solid #38bdf8' }}>
              <span className="stat-card-title">Assigned Patients</span>
              <span className="stat-card-value" style={{ color: '#38bdf8' }}>{patients.length}</span>
              <span className="stat-card-subtitle">Active Inpatient & Ambulatory</span>
            </div>

            <div className="stat-card" style={{ borderLeft: '3px solid #34d399' }}>
              <span className="stat-card-title">Today's Appointments</span>
              <span className="stat-card-value" style={{ color: '#34d399' }}>{doctorAppointments.length}</span>
              <span className="stat-card-subtitle">Consultations Scheduled</span>
            </div>

            <div className="stat-card" style={{ borderLeft: '3px solid #fbbf24' }}>
              <span className="stat-card-title">CDS Alerts & Flags</span>
              <span className="stat-card-value" style={{ color: '#fbbf24' }}>0 Active</span>
              <span className="stat-card-subtitle">Safety & Drug Interaction Alerts</span>
            </div>

            <div className="stat-card" style={{ borderLeft: '3px solid #a855f7' }}>
              <span className="stat-card-title">AI Scribe & OCR Tasks</span>
              <span className="stat-card-value" style={{ color: '#c084fc' }}>{activeTaskCount} Running</span>
              <span className="stat-card-subtitle">Background Intelligence Queue</span>
            </div>
          </div>

          {/* Active Patient EHR Preview Card */}
          {selectedPatient && (
            <div
              className="glass-panel"
              style={{
                padding: '18px 20px',
                border: '1px solid rgba(2, 132, 199, 0.35)',
                background: 'linear-gradient(135deg, rgba(2, 132, 199, 0.08) 0%, rgba(17, 24, 39, 0.95) 100%)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#38bdf8', fontWeight: 700 }}>
                    Selected Patient Record
                  </span>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#ffffff', margin: '4px 0 2px 0' }}>
                    {selectedPatient.first_name} {selectedPatient.last_name}
                  </h2>
                  <div style={{ display: 'flex', gap: '12px', fontSize: '0.8rem', color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
                    <span>MRN: <code style={{ color: '#38bdf8' }}>{selectedPatient.patient_id}</code></span>
                    <span>DOB: {selectedPatient.date_of_birth}</span>
                    <span>Gender: {selectedPatient.gender}</span>
                    <span>Blood Group: <strong style={{ color: '#f87171' }}>{selectedPatient.blood_group || 'O+'}</strong></span>
                    <span>Allergies: <strong style={{ color: '#fbbf24' }}>{selectedPatient.allergies || 'None Reported'}</strong></span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => setActiveSection('timeline')}
                    className="btn btn-primary btn-sm"
                    style={{ fontSize: '0.75rem' }}
                  >
                    📅 Timeline
                  </button>
                  <button
                    onClick={() => setActiveSection('notes')}
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: '0.75rem' }}
                  >
                    📝 Notes
                  </button>
                  <button
                    onClick={() => setActiveSection('orders')}
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: '0.75rem' }}
                  >
                    📦 Orders
                  </button>
                  <button
                    onClick={() => setActiveSection('emar')}
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: '0.75rem' }}
                  >
                    💊 eMAR
                  </button>
                  <button
                    onClick={() => setActiveSection('imaging')}
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: '0.75rem' }}
                  >
                    🩻 Imaging
                  </button>
                </div>
              </div>

              {selectedPatient.health_problem && (
                <div style={{ marginTop: '12px', padding: '10px 14px', background: 'rgba(0,0,0,0.3)', borderRadius: '6px', fontSize: '0.8125rem' }}>
                  <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Reported Complaint: </span>
                  <span style={{ color: '#fbbf24' }}>{selectedPatient.health_problem}</span>
                </div>
              )}
            </div>
          )}

          {/* Split View: Patient Directory & Upcoming Appointments */}
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) 1fr', gap: '20px' }}>
            {/* Patient Directory */}
            <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', height: '420px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff' }}>Hospital Patients Directory</h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{patients.length} Total</span>
              </div>
              <div style={{ flex: 1, overflowY: 'auto' }}>
                <PatientDirectory />
              </div>
            </div>

            {/* Upcoming Appointments Table */}
            <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', height: '420px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff' }}>Upcoming Consultations</h3>
                <button
                  onClick={() => setIsScheduleModalOpen(true)}
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '0.7rem' }}
                >
                  + Book Slot
                </button>
              </div>

              <div style={{ flex: 1, overflowY: 'auto' }}>
                {doctorAppointments.length === 0 ? (
                  <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                    No appointments scheduled.
                  </div>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                        <th style={{ padding: '6px 8px' }}>Time</th>
                        <th style={{ padding: '6px 8px' }}>Patient</th>
                        <th style={{ padding: '6px 8px' }}>Reason</th>
                        <th style={{ padding: '6px 8px' }}>Mode</th>
                      </tr>
                    </thead>
                    <tbody>
                      {doctorAppointments.map((apt) => (
                        <tr key={apt.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                          <td style={{ padding: '8px', color: '#38bdf8', fontWeight: 600 }}>
                            {new Date(apt.appointment_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </td>
                          <td style={{ padding: '8px', color: '#ffffff', fontWeight: 600 }}>
                            {apt.patient ? `${apt.patient.first_name} ${apt.patient.last_name}` : `Patient #${apt.patient_id}`}
                          </td>
                          <td style={{ padding: '8px', color: 'var(--text-secondary)' }}>
                            {apt.reason_for_visit}
                          </td>
                          <td style={{ padding: '8px', textTransform: 'capitalize', color: 'var(--text-muted)' }}>
                            {apt.consultation_mode}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 2. CLINICAL WORKSPACE MODULES */}
      {activeSection === 'chat' && <ClinicalChat patientId={selectedPatient?.patient_id} />}
      {activeSection === 'timeline' && <TimelineView patientId={selectedPatient?.patient_id} />}
      {activeSection === 'notes' && (
        <ClinicalNoteWorkspace
          patientId={selectedPatient?.patient_id}
          onTriggerSynthesis={triggerNoteSynthesis}
        />
      )}
      {activeSection === 'vitals' && <VitalTelemetryWorkspace patientId={selectedPatient?.patient_id} />}
      {activeSection === 'care_plans' && (
        <CarePlanWorkspace
          patientId={selectedPatient?.patient_id}
          onTriggerSynthesis={triggerCarePlanSynthesis}
        />
      )}
      {activeSection === 'transitions' && (
        <TransitionsWorkspace
          patientId={selectedPatient?.patient_id}
          currentUser={user}
        />
      )}
      {activeSection === 'orders' && <OrdersWorkspace />}
      {activeSection === 'emar' && <EMARClosedLoopWorkspace />}
      {activeSection === 'cds_pgx' && <CDSPGxOrderSetWorkspace />}
      {activeSection === 'documents' && (
        <DocumentHub
          patientId={selectedPatient?.patient_id}
          onTriggerOCR={triggerDocumentOCR}
        />
      )}
      {activeSection === 'media' && (
        <MediaDiagnosticsHub
          patientId={selectedPatient?.patient_id}
          onTriggerAnalysis={triggerMediaAnalysis}
        />
      )}
      {activeSection === 'imaging' && (
        <ImagingRadiologyWorkspace
          currentUser={user}
          selectedPatientId={selectedPatient?.patient_id}
        />
      )}
      {activeSection === 'pacs_waveforms' && <DICOMPACSViewerWorkspace patientId={selectedPatient?.patient_id || 'PAT-00101'} />}
      {activeSection === 'collaboration' && <LiveCollaborationWorkspace selectedPatientId={selectedPatient?.patient_id} />}
      {activeSection === 'cohorts' && (
        <CohortWorkspace
          currentUser={user}
          currentPatientId={selectedPatient?.patient_id}
          onSelectPatient={(pid) => selectPatientById(pid)}
        />
      )}
      {activeSection === 'trials' && <TrialsPrecisionWorkspace initialPatientId={selectedPatient?.patient_id} />}
      {activeSection === 'agents' && <ClinicalAgentsWorkspace />}
      {activeSection === 'quality' && <QualityMeasuresWorkspace />}
      {activeSection === 'smart_ehr' && <SmartFhirEhrWorkspace selectedPatientId={selectedPatient?.patient_id} />}
      {activeSection === 'regional_interop' && <RegionalInteroperabilityWorkspace />}
      {activeSection === 'trials_governance' && <TrialsGovernanceWorkspace />}
      {activeSection === 'rpm' && <RPMWorkspace currentUser={user} activePatient={selectedPatient} />}
      {activeSection === 'security' && (
        <SecurityComplianceWorkspace
          patients={patients}
          selectedPatient={selectedPatient}
          onSelectPatient={(p) => selectPatientById(p.patient_id)}
        />
      )}
      {activeSection === 'diagnostics' && <SystemDiagnosticsWorkspace />}
      {activeSection === 'tenants' && <HealthSystemTenantWorkspace />}

      {/* SCHEDULE CONSULTATION MODAL */}
      {isScheduleModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999,
            padding: '20px',
          }}
        >
          <div className="glass-panel" style={{ width: '100%', maxWidth: '500px', padding: '24px', background: '#0f172a' }}>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ffffff', marginBottom: '8px' }}>
              Schedule Clinical Consultation
            </h3>
            {selectedPatient ? (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                Booking appointment for <strong style={{ color: '#ffffff' }}>{selectedPatient.first_name} {selectedPatient.last_name}</strong> ({selectedPatient.patient_id})
              </p>
            ) : (
              <p style={{ fontSize: '0.85rem', color: '#fbbf24', marginBottom: '16px' }}>
                ⚠️ Please select a patient from the directory first before booking a consultation.
              </p>
            )}

            <form onSubmit={handleCreateAppointment}>
              <div className="form-group">
                <label className="form-label">Consultation Date & Time</label>
                <input
                  type="datetime-local"
                  value={appointmentDate}
                  onChange={(e) => setAppointmentDate(e.target.value)}
                  className="form-input"
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">Consultation Mode</label>
                  <select
                    value={consultMode}
                    onChange={(e) => setConsultMode(e.target.value)}
                    className="form-select"
                  >
                    <option value="in_person">In-Person Clinic Visit</option>
                    <option value="telehealth">Telehealth Video Room</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Duration (Minutes)</label>
                  <select
                    value={durationMins}
                    onChange={(e) => setDurationMins(Number(e.target.value))}
                    className="form-select"
                  >
                    <option value={15}>15 Minutes (Brief)</option>
                    <option value={30}>30 Minutes (Standard)</option>
                    <option value={45}>45 Minutes (Extended)</option>
                    <option value={60}>60 Minutes (Comprehensive)</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Reason for Visit / Clinical Objective</label>
                <input
                  type="text"
                  value={reasonForVisit}
                  onChange={(e) => setReasonForVisit(e.target.value)}
                  className="form-input"
                  placeholder="e.g. Cardiology follow-up & hypertension assessment"
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
                <button
                  type="button"
                  onClick={() => setIsScheduleModalOpen(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isScheduling || !selectedPatient}
                  className="btn btn-primary"
                >
                  {isScheduling ? 'Scheduling...' : 'Confirm Appointment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Safety Prescriber Modal */}
      <SafetyPrescriberModal
        isOpen={isSafetyModalOpen}
        onClose={() => setIsSafetyModalOpen(false)}
        patientId={selectedPatient?.patient_id}
      />

      {/* Task Queue Monitor */}
      <TaskMonitor
        isOpen={isTasksModalOpen}
        onClose={() => setIsTasksModalOpen(false)}
        tasks={tasks}
        onRetry={retryTask}
        onCancel={cancelTask}
        onRefresh={loadTasks}
      />
    </AppShell>
  );
};
