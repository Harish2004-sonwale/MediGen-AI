// ==============================================================================
// MediGen AI - Main Clinical Dashboard Page
// ==============================================================================

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { usePatient } from '../context/PatientContext';
import { useTasks } from '../hooks/useTasks';
import { Header } from '../components/layout/Header';
import { PatientRibbon } from '../components/layout/PatientRibbon';
import { PatientDirectory } from '../components/patients/PatientDirectory';
import { TimelineView } from '../components/timeline/TimelineView';
import { ClinicalChat } from '../components/chat/ClinicalChat';
import { SafetyPrescriberModal } from '../components/safety/SafetyPrescriberModal';
import { DocumentHub } from '../components/documents/DocumentHub';
import { MediaDiagnosticsHub } from '../components/media/MediaDiagnosticsHub';
import { ClinicalNoteWorkspace } from '../components/notes/ClinicalNoteWorkspace';
import { VitalTelemetryWorkspace } from '../components/telemetry/VitalTelemetryWorkspace';
import { CarePlanWorkspace } from '../components/care/CarePlanWorkspace';
import { CohortWorkspace } from '../components/cohorts/CohortWorkspace';
import { TransitionsWorkspace } from '../components/transitions/TransitionsWorkspace';
import { OrdersWorkspace } from '../components/orders/OrdersWorkspace';
import { QualityMeasuresWorkspace } from '../components/quality/QualityMeasuresWorkspace';
import { RPMWorkspace } from '../components/rpm/RPMWorkspace';
import { TrialsPrecisionWorkspace } from '../components/trials/TrialsPrecisionWorkspace';
import { ClinicalAgentsWorkspace } from '../components/agents/ClinicalAgentsWorkspace';
import { ImagingRadiologyWorkspace } from '../components/imaging/ImagingRadiologyWorkspace';
import { SecurityComplianceWorkspace } from '../components/security/SecurityComplianceWorkspace';
import { TaskMonitor } from '../components/tasks/TaskMonitor';
import { carePlansApi, mediaApi, notesApi } from '../api/client';
import { CarePlanCategory, NoteType } from '../types';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const { patients, selectedPatient, selectPatientById } = usePatient();
  const { tasks, retryTask, cancelTask, loadTasks, triggerDocumentOCR } = useTasks(
    selectedPatient?.patient_id
  );

  const [isSafetyModalOpen, setIsSafetyModalOpen] = useState<boolean>(false);
  const [isTasksModalOpen, setIsTasksModalOpen] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<
    | 'timeline'
    | 'chat'
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
  >('chat');









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


  const activeTaskCount = tasks.filter(
    (t) => t.status === 'queued' || t.status === 'running' || t.status === 'retrying'
  ).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Top Application Header */}
      <Header
        onOpenSafetyModal={() => setIsSafetyModalOpen(true)}
        onOpenTasksModal={() => setIsTasksModalOpen(true)}
        activeTaskCount={activeTaskCount}
      />

      {/* Active Patient Context Ribbon */}
      <PatientRibbon />

      {/* Main Clinical Dashboard Grid */}
      <main className="dashboard-grid">
        {/* Left Column: Patient Directory */}
        <section style={{ height: '100%', overflow: 'hidden' }}>
          <PatientDirectory />
        </section>

        {/* Center Column: Interactive Workspaces (Chat, Timeline, Documents, Media, Notes, Vitals Tabs) */}
        <section style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '12px', overflow: 'hidden' }}>
          {/* Navigation Tab Bar */}
          <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', flexWrap: 'wrap' }}>
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
              className={`btn btn-sm ${activeTab === 'documents' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('documents')}
            >
              📁 Medical Documents
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'media' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('media')}
            >
              🖼️ Diagnostics & Imaging
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'notes' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('notes')}
            >
              📝 Clinical Notes
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'vitals' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('vitals')}
            >
              💓 Vitals & CDS Alerts
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'care_plans' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('care_plans')}
            >
              📋 Care Plans & Tasks
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'cohorts' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('cohorts')}
            >
              👥 Population & Risk Analytics
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'transitions' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('transitions')}
            >
              🔄 Transitions & Discharge
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'orders' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('orders')}
            >
              📦 Orders & Diagnostics
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'quality' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('quality')}
            >
              📊 Clinical Quality & Compliance
            </button>
            <button
              className={`btn btn-sm ${activeTab === 'rpm' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('rpm')}
            >
              📡 Remote Monitoring & Telehealth
            </button>
            <button
              data-testid="tab-btn-trials"
              className={`btn btn-sm ${activeTab === 'trials' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('trials')}
            >
              🧬 Precision Oncology & Trials
            </button>
            <button
              data-testid="tab-btn-agents"
              className={`btn btn-sm ${activeTab === 'agents' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('agents')}
            >
              🤖 Clinical AI & Care Coordination
            </button>
            <button
              data-testid="tab-btn-imaging"
              className={`btn btn-sm ${activeTab === 'imaging' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('imaging')}
            >
              🩻 Medical Imaging & Radiology
            </button>
            <button
              data-testid="tab-btn-security"
              className={`btn btn-sm ${activeTab === 'security' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('security')}
            >
              🛡️ Security & Compliance
            </button>
          </div>

          {/* Active Workspace View */}
          <div style={{ flex: 1, overflow: 'hidden' }}>
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
          </div>








        </section>

        {/* Right Column: Longitudinal Timeline Mini-Feed & Quick Actions */}
        <section className="right-sidebar" style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <TimelineView patientId={selectedPatient?.patient_id} />
          </div>
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
    </div>
  );
};
