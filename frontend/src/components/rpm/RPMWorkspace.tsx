import React, { useState, useEffect, useId } from 'react';
import { rpmApi, patientsApi } from '../../api/client';

import {
  Patient,
  PROMDefinition,
  PROMResponseDetail,
  RPMDevice,
  RPMEscalationAlert,
  RPMObservation,
  RPMProgram,
  RPMTelemetrySummary,
  TelehealthSession,
  User,
} from '../../types';

interface RPMWorkspaceProps {
  currentUser?: User | null;
  activePatient?: Patient | null;
}

export const RPMWorkspace: React.FC<RPMWorkspaceProps> = ({ currentUser, activePatient }) => {
  const [activeTab, setActiveTab] = useState<'clinician' | 'patient'>('clinician');
  const [programs, setPrograms] = useState<RPMProgram[]>([]);
  const [devices, setDevices] = useState<RPMDevice[]>([]);
  const [observations, setObservations] = useState<RPMObservation[]>([]);
  const [alerts, setAlerts] = useState<RPMEscalationAlert[]>([]);
  const [sessions, setSessions] = useState<TelehealthSession[]>([]);
  const [promDefs, setPromDefs] = useState<PROMDefinition[]>([]);
  const [promResponses, setPromResponses] = useState<PROMResponseDetail[]>([]);
  const [summary, setSummary] = useState<RPMTelemetrySummary | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Modals state
  const [isEnrollModalOpen, setIsEnrollModalOpen] = useState(false);
  const [isDeviceModalOpen, setIsDeviceModalOpen] = useState(false);
  const [isObsModalOpen, setIsObsModalOpen] = useState(false);
  const [isTelehealthModalOpen, setIsTelehealthModalOpen] = useState(false);
  const [isPromModalOpen, setIsPromModalOpen] = useState(false);
  const [selectedProm, setSelectedProm] = useState<PROMDefinition | null>(null);
  const [promAnswers, setPromAnswers] = useState<Record<string, number>>({});
  const [selectedAlert, setSelectedAlert] = useState<RPMEscalationAlert | null>(null);
  const [selectedSession, setSelectedSession] = useState<TelehealthSession | null>(null);

  // Form states
  const [selectedPatientId, setSelectedPatientId] = useState<string>(activePatient?.patient_id || '');
  const [enrollForm, setEnrollForm] = useState({
    condition_name: 'Essential Hypertension',
    program_name: 'Longitudinal Cardiovascular RPM Protocol',
    target_cadence_days: 1,
    clinical_goals: 'Maintain BP < 130/80 mmHg\nDaily morning telemetry logging',
  });
  const [deviceForm, setDeviceForm] = useState({
    device_type: 'blood_pressure_cuff',
    manufacturer: 'Omron Healthcare',
    model_number: 'BP-7000',
    serial_number: '',
  });
  const [obsForm, setObsForm] = useState({
    observation_type: 'systolic_bp' as any,
    numeric_value: 120,
    secondary_value: 80,
    unit_of_measure: 'mmHg',
    source_type: 'bluetooth_sync' as any,
  });
  const [telehealthForm, setTelehealthForm] = useState({
    scheduled_start: new Date(Date.now() + 86400000).toISOString().slice(0, 16),
    visit_reason: 'Remote Telemetry & Quality Review',
  });
  const [alertResolveForm, setAlertResolveForm] = useState({
    clinical_action_taken: '',
    create_care_task: true,
  });
  const [sessionNotesForm, setSessionNotesForm] = useState({
    session_notes: '',
    followup_instructions: '',
    create_followup_task: true,
  });

  const uniqueId = useId();

  useEffect(() => {
    if (currentUser?.role === 'patient') {
      setActiveTab('patient');
    }
  }, [currentUser]);

  useEffect(() => {
    loadAllData();
  }, [activePatient, selectedPatientId]);

  const loadAllData = async () => {
    setIsLoading(true);
    try {
      const pId = selectedPatientId || activePatient?.patient_id || undefined;
      const [
        progRes,
        devRes,
        obsRes,
        altRes,
        sesRes,
        promDefRes,
        promRespRes,
        ptsRes,
      ] = await Promise.all([
        rpmApi.listPrograms({ patient_id: pId }),
        rpmApi.listDevices({ patient_id: pId }),
        rpmApi.listObservations({ patient_id: pId }),
        rpmApi.listAlerts({ patient_id: pId }),
        rpmApi.listTelehealthSessions({ patient_id: pId }),
        rpmApi.listPromDefinitions(),
        rpmApi.listPromResponses({ patient_id: pId }),
        patientsApi.list(),
      ]);

      setPrograms(progRes.items || []);
      setDevices(devRes.items || []);
      setObservations(obsRes.items || []);
      setAlerts(altRes.items || []);
      setSessions(sesRes.items || []);
      setPromDefs(promDefRes.items || []);
      setPromResponses(promRespRes.items || []);

      setPatients(ptsRes || []);

      if (pId) {
        try {
          const sumRes = await rpmApi.getPatientSummary(pId);
          setSummary(sumRes);
        } catch {
          setSummary(null);
        }
      }
    } catch (err: any) {
      console.error('Failed to load RPM data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const showNotification = (type: 'success' | 'error', message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 4500);
  };

  // Handlers
  const handleEnroll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatientId) {
      showNotification('error', 'Please select a patient.');
      return;
    }
    try {
      await rpmApi.enrollProgram({
        patient_id: selectedPatientId,
        condition_name: enrollForm.condition_name,
        program_name: enrollForm.program_name,
        target_cadence_days: Number(enrollForm.target_cadence_days),
        clinical_goals: enrollForm.clinical_goals.split('\n').filter(Boolean),
      });
      showNotification('success', 'Patient enrolled in RPM program successfully.');
      setIsEnrollModalOpen(false);
      loadAllData();
    } catch (err: any) {
      showNotification('error', err?.message || 'Failed to enroll in RPM program.');
    }
  };

  const handleRegisterDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatientId) {
      showNotification('error', 'Please select a patient.');
      return;
    }
    try {
      await rpmApi.registerDevice({
        patient_id: selectedPatientId,
        device_type: deviceForm.device_type,
        manufacturer: deviceForm.manufacturer,
        model_number: deviceForm.model_number,
        serial_number: deviceForm.serial_number || `SN-${Date.now()}`,
      });
      showNotification('success', 'Connected device registered successfully.');
      setIsDeviceModalOpen(false);
      loadAllData();
    } catch (err: any) {
      showNotification('error', err?.message || 'Failed to register device.');
    }
  };

  const handleIngestObservation = async (e: React.FormEvent) => {
    e.preventDefault();
    const pId = selectedPatientId || activePatient?.patient_id;
    if (!pId) {
      showNotification('error', 'Patient ID is required.');
      return;
    }
    try {
      const res = await rpmApi.ingestObservation({
        patient_id: pId,
        observation_type: obsForm.observation_type,
        numeric_value: Number(obsForm.numeric_value),
        secondary_value: obsForm.secondary_value ? Number(obsForm.secondary_value) : undefined,
        unit_of_measure: obsForm.unit_of_measure,
        source_type: obsForm.source_type,
      });
      showNotification(
        res.classification === 'critical' ? 'error' : 'success',
        `Telemetry recorded: ${res.classification.toUpperCase()} (${res.numeric_value} ${res.unit_of_measure})`
      );
      setIsObsModalOpen(false);
      loadAllData();
    } catch (err: any) {
      showNotification('error', err?.message || 'Failed to ingest observation.');
    }
  };

  const handleScheduleTelehealth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatientId) {
      showNotification('error', 'Please select a patient.');
      return;
    }
    try {
      await rpmApi.scheduleTelehealthSession({
        patient_id: selectedPatientId,
        scheduled_start: new Date(telehealthForm.scheduled_start).toISOString(),
        visit_reason: telehealthForm.visit_reason,
      });
      showNotification('success', 'Telehealth consultation scheduled & clinical briefing synthesized.');
      setIsTelehealthModalOpen(false);
      loadAllData();
    } catch (err: any) {
      showNotification('error', err?.message || 'Failed to schedule telehealth session.');
    }
  };

  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await rpmApi.acknowledgeAlert(alertId, 'Clinician acknowledged telemetry escalation.');
      showNotification('success', 'Escalation alert acknowledged.');
      loadAllData();
    } catch (err: any) {
      showNotification('error', err?.message || 'Failed to acknowledge alert.');
    }
  };

  const handleResolveAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAlert) return;
    try {
      await rpmApi.resolveAlert(selectedAlert.alert_id, alertResolveForm);
      showNotification('success', 'Escalation alert resolved.');
      setSelectedAlert(null);
      loadAllData();
    } catch (err: any) {
      showNotification('error', err?.message || 'Failed to resolve alert.');
    }
  };

  const handleOpenPromSurvey = (prom: PROMDefinition) => {
    setSelectedProm(prom);
    const initialAnswers: Record<string, number> = {};
    (prom.questions_json || []).forEach((q) => {
      initialAnswers[q.id] = 0;
    });
    setPromAnswers(initialAnswers);
    setIsPromModalOpen(true);
  };

  const handleSubmitProm = async (e: React.FormEvent) => {
    e.preventDefault();
    const pId = selectedPatientId || activePatient?.patient_id;
    if (!pId || !selectedProm) {
      showNotification('error', 'Patient ID and Questionnaire required.');
      return;
    }
    try {
      const res = await rpmApi.submitPromResponse({
        prom_id: selectedProm.prom_id,
        patient_id: pId,
        answers: promAnswers,
      });
      showNotification(
        res.safety_flags_json?.length ? 'error' : 'success',
        `PROM Submitted: Score ${res.calculated_score} (${res.severity_interpretation})`
      );
      setIsPromModalOpen(false);
      loadAllData();
    } catch (err: any) {
      showNotification('error', err?.message || 'Failed to submit PROM questionnaire.');
    }
  };

  const handleUpdateSessionStatus = async (sessionId: string, newStatus: any) => {
    try {
      await rpmApi.updateTelehealthSession(sessionId, { status: newStatus });
      showNotification('success', `Telehealth session updated to ${newStatus}.`);
      loadAllData();
    } catch (err: any) {
      showNotification('error', err?.message || 'Failed to update session.');
    }
  };

  const handleCompleteSessionWithNotes = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSession) return;
    try {
      await rpmApi.updateTelehealthSession(selectedSession.session_id, {
        status: 'completed',
        session_notes: sessionNotesForm.session_notes,
        followup_instructions: sessionNotesForm.followup_instructions,
        create_followup_task: sessionNotesForm.create_followup_task,
      });
      showNotification('success', 'Virtual consultation completed & follow-up care task created.');
      setSelectedSession(null);
      loadAllData();
    } catch (err: any) {
      showNotification('error', err?.message || 'Failed to complete session.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-teal-900/40 via-cyan-900/30 to-blue-900/40 border border-teal-500/30 rounded-2xl p-6 backdrop-blur-md shadow-xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-teal-500/20 border border-teal-400/30 rounded-xl text-teal-300 text-lg font-bold">
                📡
              </div>
              <h1 className="text-2xl font-bold text-white tracking-wide">
                Remote Patient Monitoring (RPM) & Telehealth
              </h1>
            </div>
            <p className="text-teal-200/80 text-sm mt-1.5 max-w-2xl">
              Deterministic out-of-hospital vital telemetry ingestion, multi-tier escalation triage, standardized PROM scoring (PHQ-9, GAD-7), and virtual care briefings.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* View Mode Toggle */}
            <div className="flex bg-slate-900/80 p-1 rounded-xl border border-slate-700/60">
              <button
                type="button"
                onClick={() => setActiveTab('clinician')}
                className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-2 ${
                  activeTab === 'clinician'
                    ? 'bg-teal-500 text-slate-950 shadow-md font-bold'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                🩺 Clinician Hub
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('patient')}
                className={`px-4 py-2 text-xs font-semibold rounded-lg transition-all flex items-center gap-2 ${
                  activeTab === 'patient'
                    ? 'bg-cyan-500 text-slate-950 shadow-md font-bold'
                    : 'text-slate-300 hover:text-white'
                }`}
              >
                📱 Patient & PROMs View
              </button>
            </div>

            <button
              type="button"
              onClick={loadAllData}
              disabled={isLoading}
              className="p-2.5 bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl transition font-bold"
              title="Refresh Data"
            >
              🔄
            </button>
          </div>
        </div>

        {/* Global Patient Selector */}
        <div className="mt-5 pt-4 border-t border-teal-500/20 flex flex-wrap items-center gap-4 text-xs">
          <span className="text-teal-300 font-medium flex items-center gap-1.5">
            🔍 Select Patient Context:
          </span>
          <select
            value={selectedPatientId}
            onChange={(e) => setSelectedPatientId(e.target.value)}
            className="bg-slate-900/90 border border-slate-700 text-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:border-teal-400"
          >
            <option value="">-- All Enrolled Patients --</option>
            {patients.map((p) => (
              <option key={p.patient_id} value={p.patient_id}>
                {p.first_name} {p.last_name} ({p.patient_id})
              </option>
            ))}
          </select>

          {summary && (
            <div className="flex items-center gap-3 ml-auto text-xs text-slate-300">
              <span className="bg-teal-500/10 border border-teal-500/30 px-2.5 py-1 rounded-full text-teal-300">
                Adherence: <strong className="text-white">{summary.adherence_rate}%</strong>
              </span>
              <span className="bg-rose-500/10 border border-rose-500/30 px-2.5 py-1 rounded-full text-rose-300">
                Active Alerts: <strong className="text-white">{summary.active_alerts_count}</strong>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Notifications */}
      {notification && (
        <div
          className={`p-4 rounded-xl text-sm font-medium border flex items-center gap-3 transition-all ${
            notification.type === 'success'
              ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
              : 'bg-rose-950/60 border-rose-500/40 text-rose-300'
          }`}
        >
          <span>{notification.type === 'success' ? '✅' : '⚠️'}</span>
          <span>{notification.message}</span>
        </div>
      )}

      {/* High Priority Escalation Alerts Banner */}
      {alerts.filter((a) => a.status === 'open').length > 0 && (
        <div className="bg-gradient-to-r from-rose-950/80 via-red-900/40 to-slate-900/80 border border-rose-500/50 rounded-2xl p-5 shadow-lg">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-lg">🚨</span>
            <h3 className="text-base font-bold text-rose-200">
              Urgent RPM Telemetry Escalations ({alerts.filter((a) => a.status === 'open').length} Open)
            </h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {alerts
              .filter((a) => a.status === 'open')
              .map((alert) => (
                <div
                  key={alert.alert_id}
                  className="bg-slate-900/90 border border-rose-500/30 rounded-xl p-4 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-rose-400">{alert.alert_id}</span>
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 uppercase">
                        {alert.severity}
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 font-medium mt-1">
                      Patient: <strong className="text-white">{alert.patient_name || alert.patient_identifier}</strong>
                    </p>
                    <p className="text-xs text-rose-200/90 mt-2 bg-rose-950/40 p-2.5 rounded-lg border border-rose-900/40">
                      {alert.escalation_reason}
                    </p>
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => handleAcknowledgeAlert(alert.alert_id)}
                      className="px-3 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 transition"
                    >
                      Acknowledge
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedAlert(alert)}
                      className="px-3 py-1.5 text-xs font-semibold bg-rose-600 hover:bg-rose-500 text-white rounded-lg transition shadow"
                    >
                      Document & Resolve
                    </button>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Main Workspace View */}
      {activeTab === 'clinician' ? (
        /* ================= CLINICIAN DASHBOARD ================= */
        <div className="space-y-6">
          {/* Quick Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur">
              <span className="text-xs text-slate-400 font-medium">Active RPM Programs</span>
              <p className="text-2xl font-bold text-white mt-1">
                {programs.filter((p) => p.status === 'active').length}
              </p>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur">
              <span className="text-xs text-slate-400 font-medium">Connected Devices</span>
              <p className="text-2xl font-bold text-teal-400 mt-1">
                {devices.filter((d) => d.status === 'active').length}
              </p>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur">
              <span className="text-xs text-slate-400 font-medium">Telemetry Readings</span>
              <p className="text-2xl font-bold text-cyan-400 mt-1">{observations.length}</p>
            </div>
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 backdrop-blur">
              <span className="text-xs text-slate-400 font-medium">Scheduled Telehealth</span>
              <p className="text-2xl font-bold text-blue-400 mt-1">
                {sessions.filter((s) => s.status === 'scheduled').length}
              </p>
            </div>
          </div>

          {/* Action Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 border border-slate-800/80 p-4 rounded-xl">
            <div className="flex items-center gap-2 text-sm text-slate-300 font-medium">
              <span>✨</span>
              <span>Clinical RPM Orchestration</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setIsEnrollModalOpen(true)}
                className="px-3.5 py-2 text-xs font-semibold bg-teal-600 hover:bg-teal-500 text-slate-950 rounded-lg flex items-center gap-1.5 transition font-bold"
              >
                + Enroll Patient
              </button>
              <button
                type="button"
                onClick={() => setIsDeviceModalOpen(true)}
                className="px-3.5 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg border border-slate-700 flex items-center gap-1.5 transition"
              >
                📱 Register Device
              </button>
              <button
                type="button"
                onClick={() => setIsObsModalOpen(true)}
                className="px-3.5 py-2 text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-slate-950 rounded-lg flex items-center gap-1.5 transition font-bold"
              >
                📈 Log Telemetry
              </button>
              <button
                type="button"
                onClick={() => setIsTelehealthModalOpen(true)}
                className="px-3.5 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white rounded-lg flex items-center gap-1.5 transition"
              >
                📹 Schedule Telehealth
              </button>
            </div>
          </div>

          {/* Telemetry Stream & Telehealth Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Telemetry Stream */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-white font-bold">
                  <span>💓</span>
                  <h3>Continuous Physiological Telemetry</h3>
                </div>
                <span className="text-xs text-slate-400">Latest 15 streams</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="pb-2">Timestamp</th>
                      <th className="pb-2">Patient</th>
                      <th className="pb-2">Type</th>
                      <th className="pb-2">Reading</th>
                      <th className="pb-2">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {observations.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="py-6 text-center text-slate-500">
                          No RPM observations recorded yet.
                        </td>
                      </tr>
                    ) : (
                      observations.slice(0, 10).map((obs) => (
                        <tr key={obs.observation_id} className="hover:bg-slate-800/40">
                          <td className="py-2.5 text-slate-400 font-mono text-[11px]">
                            {new Date(obs.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </td>
                          <td className="py-2.5 font-medium text-slate-200">
                            {obs.patient_name || obs.patient_identifier}
                          </td>
                          <td className="py-2.5 text-slate-300 capitalize">
                            {obs.observation_type.replace('_', ' ')}
                          </td>
                          <td className="py-2.5 font-bold text-white font-mono">
                            {obs.numeric_value}
                            {obs.secondary_value ? `/${obs.secondary_value}` : ''} {obs.unit_of_measure}
                          </td>
                          <td className="py-2.5">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                                obs.classification === 'normal'
                                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                  : obs.classification === 'abnormal'
                                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                  : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                              }`}
                            >
                              {obs.classification}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Scheduled Telehealth Consultations */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2 text-white font-bold">
                  <span>📹</span>
                  <h3>Virtual Care Consultations</h3>
                </div>
                <span className="text-xs text-slate-400">{sessions.length} sessions</span>
              </div>

              <div className="space-y-3 overflow-y-auto max-h-[380px]">
                {sessions.length === 0 ? (
                  <p className="text-center text-slate-500 py-8 text-xs">No telehealth sessions scheduled.</p>
                ) : (
                  sessions.map((ses) => (
                    <div
                      key={ses.session_id}
                      className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 hover:border-slate-700 transition"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-xs font-mono font-bold text-blue-400">{ses.session_id}</span>
                          <h4 className="text-sm font-bold text-white mt-0.5">
                            {ses.patient_name || ses.patient_identifier}
                          </h4>
                        </div>
                        <span
                          className={`px-2.5 py-0.5 text-[10px] font-bold rounded-full uppercase border ${
                            ses.status === 'scheduled'
                              ? 'bg-blue-500/20 text-blue-300 border-blue-500/30'
                              : ses.status === 'in_progress'
                              ? 'bg-amber-500/20 text-amber-300 border-amber-500/30 animate-pulse'
                              : ses.status === 'completed'
                              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                              : 'bg-slate-800 text-slate-400 border-slate-700'
                          }`}
                        >
                          {ses.status.replace('_', ' ')}
                        </span>
                      </div>

                      <div className="flex items-center gap-4 text-xs text-slate-400 mt-2">
                        <span>
                          📅 {new Date(ses.scheduled_start).toLocaleDateString()}{' '}
                          {new Date(ses.scheduled_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <span>Reason: {ses.visit_reason}</span>
                      </div>

                      {/* Pre-visit RPM briefing preview */}
                      {ses.pre_visit_rpm_summary_json?.key_discussion_points && (
                        <div className="mt-3 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 text-xs">
                          <span className="text-teal-400 font-semibold flex items-center gap-1 text-[11px] mb-1">
                            ✨ Pre-Visit Telemetry Briefing:
                          </span>
                          <ul className="list-disc list-inside text-slate-300 space-y-0.5 text-[11px]">
                            {(ses.pre_visit_rpm_summary_json.key_discussion_points as string[]).slice(0, 2).map((pt, i) => (
                              <li key={i}>{pt}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Action buttons */}
                      <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-end gap-2 text-xs">
                        {ses.status === 'scheduled' && (
                          <button
                            type="button"
                            onClick={() => handleUpdateSessionStatus(ses.session_id, 'in_progress')}
                            className="px-3 py-1 bg-teal-600 hover:bg-teal-500 text-slate-950 font-bold rounded-lg transition"
                          >
                            Start Visit
                          </button>
                        )}
                        {ses.status === 'in_progress' && (
                          <button
                            type="button"
                            onClick={() => setSelectedSession(ses)}
                            className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg transition"
                          >
                            Complete & Document
                          </button>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* ================= PATIENT & PROMS HUB ================= */
        <div className="space-y-6">
          {/* Patient Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-teal-500/20 text-teal-300 rounded-xl text-lg font-bold">
                  📱
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">My Connected Devices</h4>
                  <span className="text-xs text-slate-400">{devices.length} registered wearables</span>
                </div>
              </div>
              <div className="space-y-2 mt-3">
                {devices.map((d) => (
                  <div key={d.device_id} className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 text-xs flex justify-between items-center">
                    <div>
                      <strong className="text-slate-200 capitalize">{d.device_type.replace('_', ' ')}</strong>
                      <p className="text-[11px] text-slate-400">{d.manufacturer} ({d.model_number})</p>
                    </div>
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 uppercase">
                      {d.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-cyan-500/20 text-cyan-300 rounded-xl text-lg font-bold">
                  💓
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Daily Vital Check-In</h4>
                  <span className="text-xs text-slate-400">Log today's readings</span>
                </div>
              </div>
              <p className="text-xs text-slate-300 mb-4">
                Record your home blood pressure, blood glucose, or heart rate to share with your care team.
              </p>
              <button
                type="button"
                onClick={() => setIsObsModalOpen(true)}
                className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs rounded-xl transition"
              >
                + Record Telemetry
              </button>
            </div>

            <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow">
              <div className="flex items-center gap-3 mb-3">
                <div className="p-2 bg-purple-500/20 text-purple-300 rounded-xl text-lg font-bold">
                  📝
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white">Outcome Questionnaires</h4>
                  <span className="text-xs text-slate-400">{promDefs.length} standard surveys</span>
                </div>
              </div>
              <p className="text-xs text-slate-300 mb-4">
                Complete clinically validated PROMs (PHQ-9, GAD-7, PROMIS-10) for wellness tracking.
              </p>
              <div className="space-y-2">
                {promDefs.map((prom) => (
                  <button
                    key={prom.prom_id}
                    type="button"
                    onClick={() => handleOpenPromSurvey(prom)}
                    className="w-full text-left p-2 bg-slate-950/60 hover:bg-slate-800 border border-slate-800 rounded-lg text-xs flex justify-between items-center transition"
                  >
                    <span className="text-slate-200 font-medium">{prom.title}</span>
                    <span className="text-purple-400 font-bold text-[11px]">Start &rarr;</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Historical Survey Responses */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-white font-bold">
                <span>📝</span>
                <h3>Completed Outcome Assessments (PROMs)</h3>
              </div>
              <span className="text-xs text-slate-400">{promResponses.length} submitted</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {promResponses.length === 0 ? (
                <p className="text-slate-500 text-xs col-span-full text-center py-6">
                  No PROM questionnaires completed yet.
                </p>
              ) : (
                promResponses.map((pr) => (
                  <div
                    key={pr.response_id}
                    className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-purple-400">{pr.prom_identifier || 'PROM'}</span>
                        <span className="text-[11px] text-slate-400">
                          {new Date(pr.completed_at).toLocaleDateString()}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-white mt-1">{pr.prom_title || 'Patient Assessment'}</h4>
                      <div className="mt-3 bg-purple-950/30 p-2.5 rounded-lg border border-purple-900/40 flex items-center justify-between">
                        <span className="text-xs text-slate-300">Score:</span>
                        <span className="text-sm font-bold text-purple-300">{pr.calculated_score}</span>
                      </div>
                      <p className="text-xs text-slate-300 mt-2">
                        Severity: <strong className="text-white">{pr.severity_interpretation}</strong>
                      </p>
                      {pr.safety_flags_json?.length > 0 && (
                        <div className="mt-2 text-[11px] text-rose-300 bg-rose-950/60 p-2 rounded border border-rose-800 flex items-center gap-1.5">
                          <span>⚠️</span>
                          <span>Safety protocol triggered</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* ================= MODALS ================= */}

      {/* Enroll Modal */}
      {isEnrollModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span>➕</span>
              Enroll Patient in RPM Protocol
            </h3>
            <form onSubmit={handleEnroll} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Target Clinical Condition</label>
                <input
                  type="text"
                  value={enrollForm.condition_name}
                  onChange={(e) => setEnrollForm({ ...enrollForm, condition_name: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Protocol / Program Title</label>
                <input
                  type="text"
                  value={enrollForm.program_name}
                  onChange={(e) => setEnrollForm({ ...enrollForm, program_name: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Target Monitoring Cadence (Days)</label>
                <input
                  type="number"
                  min="1"
                  max="30"
                  value={enrollForm.target_cadence_days}
                  onChange={(e) => setEnrollForm({ ...enrollForm, target_cadence_days: Number(e.target.value) })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Clinical Goals (One per line)</label>
                <textarea
                  rows={3}
                  value={enrollForm.clinical_goals}
                  onChange={(e) => setEnrollForm({ ...enrollForm, clinical_goals: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                />
              </div>
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsEnrollModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-slate-950 font-bold rounded-lg"
                >
                  Confirm Enrollment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Register Device Modal */}
      {isDeviceModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span>📱</span>
              Register Connected Medical Device
            </h3>
            <form onSubmit={handleRegisterDevice} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Device Type</label>
                <select
                  value={deviceForm.device_type}
                  onChange={(e) => setDeviceForm({ ...deviceForm, device_type: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                >
                  <option value="blood_pressure_cuff">Blood Pressure Cuff</option>
                  <option value="pulse_oximeter">Pulse Oximeter</option>
                  <option value="glucometer">Glucometer (Blood Glucose)</option>
                  <option value="weight_scale">Digital Weight Scale</option>
                  <option value="thermometer">Digital Thermometer</option>
                </select>
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Manufacturer</label>
                <input
                  type="text"
                  value={deviceForm.manufacturer}
                  onChange={(e) => setDeviceForm({ ...deviceForm, manufacturer: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Model Number</label>
                <input
                  type="text"
                  value={deviceForm.model_number}
                  onChange={(e) => setDeviceForm({ ...deviceForm, model_number: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                />
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Serial Number (Optional)</label>
                <input
                  type="text"
                  placeholder="Auto-generated if blank"
                  value={deviceForm.serial_number}
                  onChange={(e) => setDeviceForm({ ...deviceForm, serial_number: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                />
              </div>
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsDeviceModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-slate-950 font-bold rounded-lg"
                >
                  Register Device
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Ingest Observation Modal */}
      {isObsModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span>📈</span>
              Log Remote Telemetry Reading
            </h3>
            <form onSubmit={handleIngestObservation} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Measurement Type</label>
                <select
                  value={obsForm.observation_type}
                  onChange={(e) => {
                    const t = e.target.value as any;
                    let u = 'mmHg';
                    if (t === 'heart_rate') u = 'bpm';
                    if (t === 'spo2') u = '%';
                    if (t === 'blood_glucose') u = 'mg/dL';
                    if (t === 'weight') u = 'kg';
                    if (t === 'temperature') u = 'degC';
                    setObsForm({ ...obsForm, observation_type: t, unit_of_measure: u });
                  }}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                >
                  <option value="systolic_bp">Blood Pressure (Systolic & Diastolic)</option>
                  <option value="heart_rate">Heart Rate</option>
                  <option value="spo2">Oxygen Saturation (SpO2)</option>
                  <option value="blood_glucose">Blood Glucose</option>
                  <option value="weight">Body Weight</option>
                  <option value="temperature">Body Temperature</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    {obsForm.observation_type === 'systolic_bp' ? 'Systolic (mmHg)' : 'Value'}
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={obsForm.numeric_value}
                    onChange={(e) => setObsForm({ ...obsForm, numeric_value: Number(e.target.value) })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                    required
                  />
                </div>
                {obsForm.observation_type === 'systolic_bp' && (
                  <div>
                    <label className="block text-slate-300 font-medium mb-1">Diastolic (mmHg)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={obsForm.secondary_value}
                      onChange={(e) => setObsForm({ ...obsForm, secondary_value: Number(e.target.value) })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                      required
                    />
                  </div>
                )}
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Source Interface</label>
                <select
                  value={obsForm.source_type}
                  onChange={(e) => setObsForm({ ...obsForm, source_type: e.target.value as any })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                >
                  <option value="bluetooth_sync">Bluetooth Sync</option>
                  <option value="cellular_gateway">Cellular Gateway Hub</option>
                  <option value="manual_entry">Manual Patient Entry</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsObsModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-lg"
                >
                  Submit Telemetry
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Schedule Telehealth Modal */}
      {isTelehealthModalOpen && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-6 shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span>📹</span>
              Schedule Virtual Consultation
            </h3>
            <form onSubmit={handleScheduleTelehealth} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Scheduled Date & Time</label>
                <input
                  type="datetime-local"
                  value={telehealthForm.scheduled_start}
                  onChange={(e) => setTelehealthForm({ ...telehealthForm, scheduled_start: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Consultation Objective / Reason</label>
                <input
                  type="text"
                  value={telehealthForm.visit_reason}
                  onChange={(e) => setTelehealthForm({ ...telehealthForm, visit_reason: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                  required
                />
              </div>
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsTelehealthModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg"
                >
                  Schedule Visit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* PROM Questionnaire Survey Modal */}
      {isPromModalOpen && selectedProm && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-purple-500/40 rounded-2xl max-w-2xl w-full p-6 shadow-2xl max-h-[90vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <span className="text-xs font-mono font-bold text-purple-400">{selectedProm.prom_id}</span>
                <h3 className="text-base font-bold text-white mt-0.5">{selectedProm.title}</h3>
              </div>
              <span className="px-3 py-1 bg-purple-500/20 text-purple-300 font-bold text-xs rounded-full border border-purple-500/30">
                Validated Assessment
              </span>
            </div>

            <form onSubmit={handleSubmitProm} className="space-y-5 overflow-y-auto py-4 text-xs pr-1">
              <p className="text-slate-300 italic">
                Over the last 2 weeks, how often have you been bothered by any of the following problems?
              </p>

              {(selectedProm.questions_json || []).map((q, idx) => (
                <div key={q.id} className="bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
                  <p className="font-semibold text-slate-200 mb-2.5">
                    {idx + 1}. {q.prompt}
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {q.options.map((opt) => (
                      <label
                        key={opt.value}
                        className={`p-2 rounded-lg border text-center cursor-pointer transition text-[11px] ${
                          promAnswers[q.id] === opt.score
                            ? 'bg-purple-600 text-white font-bold border-purple-400'
                            : 'bg-slate-900 text-slate-300 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <input
                          type="radio"
                          name={`q_${q.id}`}
                          value={opt.score}
                          checked={promAnswers[q.id] === opt.score}
                          onChange={() => setPromAnswers({ ...promAnswers, [q.id]: opt.score })}
                          className="sr-only"
                        />
                        {opt.label} ({opt.score})
                      </label>
                    ))}
                  </div>
                </div>
              ))}

              <div className="flex justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsPromModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-purple-600 hover:bg-purple-500 text-white font-bold rounded-lg shadow-lg"
                >
                  Submit Assessment
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Resolve Alert Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-rose-500/40 rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
              <span>✅</span>
              Resolve Telemetry Escalation Alert
            </h3>
            <p className="text-xs text-rose-300 bg-rose-950/40 p-2.5 rounded-lg border border-rose-900/40 mb-4">
              Alert: {selectedAlert.escalation_reason}
            </p>
            <form onSubmit={handleResolveAlert} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Documented Clinical Action Taken
                </label>
                <textarea
                  rows={3}
                  placeholder="e.g. Telephoned patient, adjusted antihypertensive dosage, scheduled urgent follow-up."
                  value={alertResolveForm.clinical_action_taken}
                  onChange={(e) =>
                    setAlertResolveForm({ ...alertResolveForm, clinical_action_taken: e.target.value })
                  }
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                  required
                />
              </div>
              <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={alertResolveForm.create_care_task}
                  onChange={(e) =>
                    setAlertResolveForm({ ...alertResolveForm, create_care_task: e.target.checked })
                  }
                  className="rounded bg-slate-800 border-slate-700 text-teal-500"
                />
                Automatically attach follow-up CareTask to patient's active CarePlan
              </label>
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setSelectedAlert(null)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg"
                >
                  Complete Resolution
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Complete Virtual Consultation Modal */}
      {selectedSession && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-teal-500/40 rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <h3 className="text-base font-bold text-white mb-2 flex items-center gap-2">
              <span>✅</span>
              Complete Virtual Care Consultation
            </h3>
            <p className="text-xs text-slate-300 mb-4">
              Patient: <strong className="text-white">{selectedSession.patient_name || selectedSession.patient_identifier}</strong> ({selectedSession.session_id})
            </p>
            <form onSubmit={handleCompleteSessionWithNotes} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Clinical Consultation Notes</label>
                <textarea
                  rows={3}
                  placeholder="Summarize key findings, vitals review, and patient responses..."
                  value={sessionNotesForm.session_notes}
                  onChange={(e) => setSessionNotesForm({ ...sessionNotesForm, session_notes: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Follow-Up Patient Instructions</label>
                <textarea
                  rows={2}
                  placeholder="Instructions for patient lifestyle, medication titration, or upcoming tests..."
                  value={sessionNotesForm.followup_instructions}
                  onChange={(e) => setSessionNotesForm({ ...sessionNotesForm, followup_instructions: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
                />
              </div>
              <label className="flex items-center gap-2 text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sessionNotesForm.create_followup_task}
                  onChange={(e) =>
                    setSessionNotesForm({ ...sessionNotesForm, create_followup_task: e.target.checked })
                  }
                  className="rounded bg-slate-800 border-slate-700 text-teal-500"
                />
                Create follow-up CareTask for clinical team
              </label>
              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setSelectedSession(null)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-teal-600 hover:bg-teal-500 text-slate-950 font-bold rounded-lg"
                >
                  Finish Consultation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
