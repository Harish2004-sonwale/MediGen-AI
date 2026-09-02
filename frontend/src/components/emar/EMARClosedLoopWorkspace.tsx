// ==============================================================================
// MediGen AI - Phase 9.0.28: Closed-Loop eMAR & Barcode Verification (BCMA) Workspace
// 5-Rights Bedside Safety Engine, Dual-Clinician High-Alert Signoff & Nursing Timeline
// ==============================================================================

import React, { useState, useEffect, useCallback } from 'react';
import { usePatient } from '../../context/PatientContext';
import { useAuth } from '../../context/AuthContext';
import { emarApi } from '../../api/client';
import {
  MARRecord,
  MARStatus,
  BCMAVerify5RightsResponse,
  MedicationBarcodeItem,
} from '../../types';

export const EMARClosedLoopWorkspace: React.FC = () => {
  const { selectedPatient } = usePatient();
  const { user } = useAuth();

  const [activeTab, setActiveTab] = useState<'timeline' | 'bcma_scanner' | 'schedule_order' | 'barcode_catalog'>('timeline');
  const [statusFilter, setStatusFilter] = useState<MARStatus | 'all'>('all');
  const [records, setRecords] = useState<MARRecord[]>([]);
  const [barcodes, setBarcodes] = useState<MedicationBarcodeItem[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<MARRecord | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // BCMA Scanner State
  const [scannedPatientBarcode, setScannedPatientBarcode] = useState<string>('');
  const [scannedMedBarcode, setScannedMedBarcode] = useState<string>('');
  const [intendedDose, setIntendedDose] = useState<string>('');
  const [intendedRoute, setIntendedRoute] = useState<string>('');
  const [bcmaResult, setBcmaResult] = useState<BCMAVerify5RightsResponse | null>(null);
  const [isVerifying5Rights, setIsVerifying5Rights] = useState<boolean>(false);

  // Administer Modal State
  const [isAdministerModalOpen, setIsAdministerModalOpen] = useState<boolean>(false);
  const [adminDose, setAdminDose] = useState<string>('');
  const [adminRoute, setAdminRoute] = useState<string>('');
  const [adminSite, setAdminSite] = useState<string>('Oral Swallowed with Water');
  const [bpValue, setBpValue] = useState<string>('124/80 mmHg');
  const [pulseValue, setPulseValue] = useState<string>('72 bpm');
  const [glucoseValue, setGlucoseValue] = useState<string>('110 mg/dL');
  const [varianceReason, setVarianceReason] = useState<string>('');
  const [patientResponseNotes, setPatientResponseNotes] = useState<string>('Patient tolerated dose well.');

  // Hold / Refuse Modal State
  const [isHoldModalOpen, setIsHoldModalOpen] = useState<boolean>(false);
  const [holdStatus, setHoldStatus] = useState<MARStatus>('held');
  const [holdReason, setHoldReason] = useState<string>('Held for SBP < 90 mmHg and heart rate < 55 bpm.');

  // Dual Signoff Modal State
  const [isDualSignoffModalOpen, setIsDualSignoffModalOpen] = useState<boolean>(false);
  const [witnessEmail, setWitnessEmail] = useState<string>('witness.nurse@hospital.org');
  const [witnessPassword, setWitnessPassword] = useState<string>('');
  const [witnessNotes, setWitnessNotes] = useState<string>('Independent second clinician check: verified dose & pump settings.');

  // Schedule New Doses State
  const [schedMedName, setSchedMedName] = useState<string>('Insulin Regular (Humulin R) 100 units/mL');
  const [schedMedCode, setSchedMedCode] = useState<string>('RXNORM-5856');
  const [schedDose, setSchedDose] = useState<string>('10 units');
  const [schedRoute, setSchedRoute] = useState<string>('subcutaneous');
  const [schedFreq, setSchedFreq] = useState<string>('TID');
  const [schedTotalDoses, setSchedTotalDoses] = useState<number>(4);
  const [schedIsHighAlert, setSchedIsHighAlert] = useState<boolean>(true);

  // Barcode Catalog Search State
  const [barcodeSearch, setBarcodeSearch] = useState<string>('');

  const loadData = useCallback(async () => {
    if (!selectedPatient) return;
    setIsLoading(true);
    try {
      const scheduleRes = await emarApi.getSchedule(
        selectedPatient.patient_id,
        statusFilter === 'all' ? undefined : statusFilter
      );
      setRecords(scheduleRes.records);
      if (scheduleRes.records.length > 0 && !selectedRecord) {
        setSelectedRecord(scheduleRes.records[0]);
      }
      const barcodeRes = await emarApi.listBarcodes();
      setBarcodes(barcodeRes.items);
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err.message || 'Failed to load eMAR schedule.' });
    } finally {
      setIsLoading(false);
    }
  }, [selectedPatient, statusFilter, selectedRecord]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Set default scanned patient barcode when patient changes
  useEffect(() => {
    if (selectedPatient) {
      setScannedPatientBarcode(selectedPatient.patient_id);
    }
  }, [selectedPatient]);

  // Trigger BCMA 5-Rights Verification
  const handleVerify5Rights = async () => {
    if (!selectedPatient) return;
    setIsVerifying5Rights(true);
    setFeedbackMsg(null);
    try {
      const res = await emarApi.verify5Rights({
        patient_id: selectedPatient.patient_id,
        scanned_patient_barcode: scannedPatientBarcode,
        scanned_med_barcode: scannedMedBarcode,
        mar_id: selectedRecord?.mar_id,
        intended_dose: intendedDose || selectedRecord?.prescribed_dose,
        intended_route: intendedRoute || selectedRecord?.prescribed_route,
      });
      setBcmaResult(res);
      if (res.verification_status === 'pass') {
        setFeedbackMsg({ type: 'success', text: '✅ BCMA 5-Rights PASSED: Ready for bedside administration.' });
      } else if (res.verification_status === 'warning_override') {
        setFeedbackMsg({ type: 'info', text: '⚠️ BCMA Warning: Variance detected. Clinician override required.' });
      } else {
        setFeedbackMsg({ type: 'error', text: '🛑 BCMA MISMATCH REJECTED: Safety stop. Do not administer.' });
      }
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err.message || '5-Rights verification error.' });
    } finally {
      setIsVerifying5Rights(false);
    }
  };

  // Administer Medication Dose
  const handleAdminister = async () => {
    if (!selectedRecord) return;
    try {
      const updated = await emarApi.administerDose(selectedRecord.mar_id, {
        administered_dose: adminDose || selectedRecord.prescribed_dose,
        administered_route: adminRoute || selectedRecord.prescribed_route,
        site_of_administration: adminSite,
        scanned_patient_barcode: scannedPatientBarcode,
        scanned_med_barcode: scannedMedBarcode,
        vital_signs_pre_admin: {
          blood_pressure: bpValue,
          heart_rate: pulseValue,
          blood_glucose: glucoseValue,
        },
        variance_reason: varianceReason || undefined,
        patient_response_notes: patientResponseNotes,
      });
      setSelectedRecord(updated);
      setIsAdministerModalOpen(false);
      setFeedbackMsg({ type: 'success', text: `✅ Dose for ${updated.medication_name} successfully administered!` });
      await loadData();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err.message || 'Failed to record administration.' });
    }
  };

  // Hold / Refuse Dose
  const handleHoldRefuse = async () => {
    if (!selectedRecord) return;
    try {
      const updated = await emarApi.holdOrRefuseDose(selectedRecord.mar_id, {
        status: holdStatus,
        clinical_reason: holdReason,
      });
      setSelectedRecord(updated);
      setIsHoldModalOpen(false);
      setFeedbackMsg({ type: 'info', text: `Dose marked as ${holdStatus.toUpperCase()} with documented rationale.` });
      await loadData();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err.message || 'Failed to hold/refuse dose.' });
    }
  };

  // Dual Signoff
  const handleDualSignoff = async () => {
    if (!selectedRecord) return;
    try {
      const updated = await emarApi.dualSignoff(selectedRecord.mar_id, {
        witness_user_email: witnessEmail,
        witness_password: witnessPassword,
        witness_notes: witnessNotes,
      });
      setSelectedRecord(updated);
      setIsDualSignoffModalOpen(false);
      setFeedbackMsg({ type: 'success', text: `✅ Independent dual witness signoff confirmed for High-Alert medication!` });
      await loadData();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err.message || 'Witness authentication failed.' });
    }
  };

  // Schedule New Inpatient Doses
  const handleScheduleDoses = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatient) return;
    try {
      const created = await emarApi.scheduleDoses({
        patient_id: selectedPatient.patient_id,
        medication_name: schedMedName,
        medication_code: schedMedCode,
        prescribed_dose: schedDose,
        prescribed_route: schedRoute,
        frequency_code: schedFreq,
        total_doses: schedTotalDoses,
        is_high_alert: schedIsHighAlert,
        requires_dual_witness: schedIsHighAlert,
      });
      setFeedbackMsg({ type: 'success', text: `✅ Successfully scheduled ${created.length} doses on patient eMAR.` });
      setActiveTab('timeline');
      await loadData();
    } catch (err: any) {
      setFeedbackMsg({ type: 'error', text: err.message || 'Failed to schedule medication.' });
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', padding: '16px', gap: '16px' }}>
      {/* Top Header & Patient Badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            💊 Closed-Loop eMAR & Barcode Medication Administration (BCMA)
          </h2>
          <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Bedside 5-Rights safety verification, ISMP high-alert dual witness authentication & nursing administration grid.
          </p>
        </div>

        {selectedPatient && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'var(--bg-secondary)', padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>
              Bedside Patient: <strong>{selectedPatient.first_name} {selectedPatient.last_name}</strong> ({selectedPatient.patient_id})
            </span>
            <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: '12px', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981', fontWeight: 700 }}>
              Wristband Active
            </span>
          </div>
        )}
      </div>

      {/* Global Feedback Alert */}
      {feedbackMsg && (
        <div
          style={{
            padding: '10px 16px',
            borderRadius: '8px',
            fontSize: '0.85rem',
            fontWeight: 600,
            background:
              feedbackMsg.type === 'success'
                ? 'rgba(16, 185, 129, 0.12)'
                : feedbackMsg.type === 'error'
                ? 'rgba(239, 68, 68, 0.12)'
                : 'rgba(59, 130, 246, 0.12)',
            color:
              feedbackMsg.type === 'success'
                ? '#059669'
                : feedbackMsg.type === 'error'
                ? '#dc2626'
                : '#2563eb',
            border: `1px solid ${
              feedbackMsg.type === 'success'
                ? '#10b981'
                : feedbackMsg.type === 'error'
                ? '#ef4444'
                : '#3b82f6'
            }`,
          }}
        >
          {feedbackMsg.text}
        </div>
      )}

      {/* Navigation Sub-Tabs */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px' }}>
        <button
          className={`btn btn-sm ${activeTab === 'timeline' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('timeline')}
        >
          📋 Inpatient eMAR Timeline
        </button>
        <button
          className={`btn btn-sm ${activeTab === 'bcma_scanner' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('bcma_scanner')}
        >
          📲 Bedside BCMA 5-Rights Scanner
        </button>
        <button
          className={`btn btn-sm ${activeTab === 'schedule_order' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('schedule_order')}
        >
          ➕ Schedule Inpatient Order
        </button>
        <button
          className={`btn btn-sm ${activeTab === 'barcode_catalog' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('barcode_catalog')}
        >
          🏷️ Pharmacy Barcode Catalog
        </button>
      </div>

      {/* Main Workspace Area */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* TAB 1: eMAR TIMELINE & RECORD GRID */}
        {activeTab === 'timeline' && (
          <div style={{ display: 'grid', gridTemplateColumns: '420px 1fr', gap: '16px', minHeight: '520px' }}>
            {/* Left Column: Scheduled Doses List */}
            <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '12px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>Administration Schedule</span>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value as any)}
                  style={{ padding: '4px 8px', borderRadius: '6px', fontSize: '0.8rem', background: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
                >
                  <option value="all">All Statuses</option>
                  <option value="scheduled">Scheduled / Due</option>
                  <option value="administered">Administered (Given)</option>
                  <option value="held">Held</option>
                  <option value="refused">Refused</option>
                </select>
              </div>

              {isLoading ? (
                <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-secondary)' }}>Loading eMAR...</div>
              ) : records.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '30px', color: 'var(--text-secondary)' }}>
                  No medication administration records found. Use "Schedule Inpatient Order" to create doses.
                </div>
              ) : (
                records.map((r) => (
                  <div
                    key={r.id}
                    id={`emar-item-${r.mar_id}`}
                    onClick={() => setSelectedRecord(r)}
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      border: `1px solid ${selectedRecord?.id === r.id ? 'var(--primary-color, #2563eb)' : 'var(--border-color)'}`,
                      background: selectedRecord?.id === r.id ? 'rgba(37, 99, 235, 0.08)' : 'var(--bg-primary)',
                      cursor: 'pointer',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.85rem' }}>{r.mar_id}</span>
                      <span
                        style={{
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '10px',
                          background:
                            r.status === 'administered'
                              ? '#dcfce7'
                              : r.status === 'scheduled'
                              ? '#dbeafe'
                              : '#fee2e2',
                          color:
                            r.status === 'administered'
                              ? '#15803d'
                              : r.status === 'scheduled'
                              ? '#1d4ed8'
                              : '#b91c1c',
                        }}
                      >
                        {r.status.toUpperCase()}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {r.is_high_alert && <span style={{ color: '#dc2626', marginRight: '4px' }}>⚠️ [HIGH-ALERT]</span>}
                      {r.medication_name}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Dose: <strong>{r.prescribed_dose}</strong> • Route: <strong>{r.prescribed_route.toUpperCase()}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                      <span>Scheduled: {new Date(r.scheduled_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      {r.requires_dual_witness && (
                        <span style={{ color: r.dual_witness_user_id ? '#15803d' : '#d97706', fontWeight: 600 }}>
                          {r.dual_witness_user_id ? '✓ Dual Signoff' : '⚠️ Witness Req'}
                        </span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Right Column: Record Detail & Bedside Administration Action Console */}
            {selectedRecord ? (
              <div style={{ background: 'var(--bg-secondary)', padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary-color, #2563eb)' }}>
                      eMAR Order Execution Record
                    </span>
                    <h3 style={{ margin: '4px 0 6px 0', fontSize: '1.2rem', fontWeight: 700 }}>
                      {selectedRecord.medication_name}
                    </h3>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      MAR ID: <strong>{selectedRecord.mar_id}</strong> | Facility: <strong>{selectedRecord.facility_id}</strong>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    {selectedRecord.status === 'scheduled' && (
                      <>
                        {selectedRecord.requires_dual_witness && !selectedRecord.dual_witness_user_id && (
                          <button
                            id="btn-dual-signoff-open"
                            onClick={() => setIsDualSignoffModalOpen(true)}
                            style={{ padding: '6px 14px', borderRadius: '6px', background: '#7c3aed', color: '#fff', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
                          >
                            👥 Dual Witness Signoff
                          </button>
                        )}
                        <button
                          id="btn-administer-open"
                          onClick={() => {
                            setAdminDose(selectedRecord.prescribed_dose);
                            setAdminRoute(selectedRecord.prescribed_route);
                            setIsAdministerModalOpen(true);
                          }}
                          style={{ padding: '6px 14px', borderRadius: '6px', background: '#059669', color: '#fff', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
                        >
                          💉 Administer Dose
                        </button>
                        <button
                          id="btn-hold-refuse-open"
                          onClick={() => setIsHoldModalOpen(true)}
                          style={{ padding: '6px 14px', borderRadius: '6px', background: '#d97706', color: '#fff', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer' }}
                        >
                          🛑 Hold / Refuse
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* 5-Rights Prescribed Spec Matrix */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                  <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>PRESCRIBED DOSE</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>{selectedRecord.prescribed_dose}</div>
                  </div>
                  <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>ROUTE</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>{selectedRecord.prescribed_route.toUpperCase()}</div>
                  </div>
                  <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>FREQUENCY</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>{selectedRecord.prescribed_frequency.toUpperCase()}</div>
                  </div>
                  <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontWeight: 600 }}>SCHEDULED TIME</div>
                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {new Date(selectedRecord.scheduled_time).toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* High Alert & Safety Banner */}
                {selectedRecord.is_high_alert && (
                  <div style={{ padding: '12px 16px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#b91c1c' }}>
                        ⚠️ ISMP High-Alert Medication Protocol
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-primary)' }}>
                        Requires independent dual-clinician witness verification of dose calculation and infusion rates before administration.
                      </div>
                    </div>
                    {selectedRecord.dual_witness_user_id ? (
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '4px 10px', borderRadius: '6px', background: '#15803d', color: '#fff' }}>
                        ✓ Witness Verified
                      </span>
                    ) : (
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '4px 10px', borderRadius: '6px', background: '#dc2626', color: '#fff' }}>
                        Pending Witness Signoff
                      </span>
                    )}
                  </div>
                )}

                {/* Administration Audit Details */}
                {selectedRecord.status === 'administered' && (
                  <div style={{ background: 'var(--bg-primary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#059669' }}>
                      ✓ Administration Completed & Logged
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', fontSize: '0.8rem' }}>
                      <div>Administered At: <strong>{selectedRecord.actual_admin_time ? new Date(selectedRecord.actual_admin_time).toLocaleString() : 'N/A'}</strong></div>
                      <div>Administered Route: <strong>{selectedRecord.administered_route}</strong></div>
                      <div>Site: <strong>{selectedRecord.site_of_administration || 'Standard'}</strong></div>
                    </div>
                    {selectedRecord.vital_signs_pre_admin_json && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        Pre-Admin Vitals: {JSON.stringify(selectedRecord.vital_signs_pre_admin_json)}
                      </div>
                    )}
                    {selectedRecord.patient_response_notes && (
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                        Notes: {selectedRecord.patient_response_notes}
                      </div>
                    )}
                  </div>
                )}

                {/* Held / Refused Audit Details */}
                {(selectedRecord.status === 'held' || selectedRecord.status === 'refused') && (
                  <div style={{ background: 'var(--bg-primary)', padding: '16px', borderRadius: '8px', border: '1px solid #d97706', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#d97706' }}>
                      🛑 Dose {selectedRecord.status.toUpperCase()} Documentation
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                      Clinical Reason: <strong>{selectedRecord.variance_reason}</strong>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ background: 'var(--bg-secondary)', padding: '40px', borderRadius: '12px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                Select a medication administration record to view details and execute bedside actions.
              </div>
            )}
          </div>
        )}

        {/* TAB 2: BCMA BEDSIDE 5-RIGHTS SCANNER SIMULATION */}
        {activeTab === 'bcma_scanner' && (
          <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: '16px' }}>
            {/* Left Column: Barcode Hardware Simulator */}
            <div style={{ background: 'var(--bg-secondary)', padding: '18px', borderRadius: '12px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>📲 Optical BCMA Scanner</h3>
              <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Simulate barcode optical laser capture at patient bedside.
              </p>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                  1. Patient Wristband Barcode (MRN)
                </label>
                <input
                  type="text"
                  value={scannedPatientBarcode}
                  onChange={(e) => setScannedPatientBarcode(e.target.value)}
                  placeholder="e.g. PAT-00101"
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                  2. Medication Unit Packaging Barcode (NDC / GS1)
                </label>
                <input
                  type="text"
                  value={scannedMedBarcode}
                  onChange={(e) => setScannedMedBarcode(e.target.value)}
                  placeholder="e.g. NDC-00002-8215-01"
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
                />
              </div>

              {/* Quick Barcode Preset Buttons */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Fast-Scan Test Barcodes:</span>
                <button
                  type="button"
                  onClick={() => setScannedMedBarcode('NDC-00002-8215-01')}
                  style={{ padding: '4px 8px', fontSize: '0.75rem', textAlign: 'left', borderRadius: '4px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', cursor: 'pointer' }}
                >
                  ⚡ Humulin R Insulin (NDC-00002-8215-01)
                </button>
                <button
                  type="button"
                  onClick={() => setScannedMedBarcode('NDC-00069-0266-01')}
                  style={{ padding: '4px 8px', fontSize: '0.75rem', textAlign: 'left', borderRadius: '4px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', cursor: 'pointer' }}
                >
                  ⚡ Amlodipine 5mg (NDC-00069-0266-01)
                </button>
                <button
                  type="button"
                  onClick={() => setScannedMedBarcode('NDC-00641-0400-25')}
                  style={{ padding: '4px 8px', fontSize: '0.75rem', textAlign: 'left', borderRadius: '4px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)', cursor: 'pointer' }}
                >
                  ⚡ Heparin Sodium (NDC-00641-0400-25)
                </button>
                <button
                  type="button"
                  onClick={() => setScannedMedBarcode('NDC-WRONG-DRUG-99')}
                  style={{ padding: '4px 8px', fontSize: '0.75rem', textAlign: 'left', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.1)', color: '#dc2626', border: '1px solid #ef4444', cursor: 'pointer' }}
                >
                  🛑 Simulate Wrong Drug Barcode Mismatch
                </button>
              </div>

              <button
                id="btn-run-bcma-verify"
                onClick={handleVerify5Rights}
                disabled={isVerifying5Rights || !scannedMedBarcode}
                style={{
                  marginTop: '8px',
                  padding: '10px 16px',
                  borderRadius: '6px',
                  background: 'var(--primary-color, #2563eb)',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  border: 'none',
                }}
              >
                {isVerifying5Rights ? 'Verifying 5 Rights...' : '🔍 Verify 5-Rights Bedside'}
              </button>
            </div>

            {/* Right Column: Live 5-Rights Verification Diagnostic Cards */}
            <div style={{ background: 'var(--bg-secondary)', padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>
                  Bedside 5-Rights Verification Engine
                </h3>
                {bcmaResult && (
                  <span
                    style={{
                      fontSize: '0.85rem',
                      fontWeight: 700,
                      padding: '4px 12px',
                      borderRadius: '8px',
                      background:
                        bcmaResult.verification_status === 'pass'
                          ? '#dcfce7'
                          : bcmaResult.verification_status === 'warning_override'
                          ? '#fef3c7'
                          : '#fee2e2',
                      color:
                        bcmaResult.verification_status === 'pass'
                          ? '#15803d'
                          : bcmaResult.verification_status === 'warning_override'
                          ? '#b45309'
                          : '#b91c1c',
                    }}
                  >
                    STATUS: {bcmaResult.verification_status.toUpperCase()}
                  </span>
                )}
              </div>

              {bcmaResult ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {/* The 5-Rights Cards */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
                    {/* Right 1: Patient */}
                    <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: `1px solid ${bcmaResult.patient_verification.passed ? '#10b981' : '#ef4444'}` }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: bcmaResult.patient_verification.passed ? '#10b981' : '#ef4444' }}>
                        1. RIGHT PATIENT {bcmaResult.patient_verification.passed ? '✓' : '✗'}
                      </div>
                      <div style={{ fontSize: '0.8rem', marginTop: '4px' }}>Expected: {bcmaResult.patient_verification.expected}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Scanned: {bcmaResult.patient_verification.scanned}</div>
                    </div>

                    {/* Right 2: Drug */}
                    <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: `1px solid ${bcmaResult.medication_verification.passed ? '#10b981' : '#ef4444'}` }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: bcmaResult.medication_verification.passed ? '#10b981' : '#ef4444' }}>
                        2. RIGHT MEDICATION {bcmaResult.medication_verification.passed ? '✓' : '✗'}
                      </div>
                      <div style={{ fontSize: '0.8rem', marginTop: '4px' }}>Expected: {bcmaResult.medication_verification.expected}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Scanned: {bcmaResult.medication_verification.scanned}</div>
                    </div>

                    {/* Right 3: Dose */}
                    <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: `1px solid ${bcmaResult.dose_verification.passed ? '#10b981' : '#ef4444'}` }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: bcmaResult.dose_verification.passed ? '#10b981' : '#ef4444' }}>
                        3. RIGHT DOSE {bcmaResult.dose_verification.passed ? '✓' : '✗'}
                      </div>
                      <div style={{ fontSize: '0.8rem', marginTop: '4px' }}>Prescribed: {bcmaResult.dose_verification.expected}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Unit Dose: {bcmaResult.dose_verification.scanned}</div>
                    </div>

                    {/* Right 4: Route */}
                    <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: `1px solid ${bcmaResult.route_verification.passed ? '#10b981' : '#ef4444'}` }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: bcmaResult.route_verification.passed ? '#10b981' : '#ef4444' }}>
                        4. RIGHT ROUTE {bcmaResult.route_verification.passed ? '✓' : '✗'}
                      </div>
                      <div style={{ fontSize: '0.8rem', marginTop: '4px' }}>Prescribed: {bcmaResult.route_verification.expected}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Intended: {bcmaResult.route_verification.scanned}</div>
                    </div>

                    {/* Right 5: Time */}
                    <div style={{ background: 'var(--bg-primary)', padding: '12px', borderRadius: '8px', border: `1px solid ${bcmaResult.time_verification.passed ? '#10b981' : '#f59e0b'}` }}>
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: bcmaResult.time_verification.passed ? '#10b981' : '#f59e0b' }}>
                        5. RIGHT TIME {bcmaResult.time_verification.passed ? '✓' : '⚠️'}
                      </div>
                      <div style={{ fontSize: '0.8rem', marginTop: '4px' }}>Window: ±60 min</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Evaluation: {bcmaResult.time_verification.passed ? 'On Time' : 'Time Variance'}</div>
                    </div>
                  </div>

                  {/* Discrepancies Alert */}
                  {bcmaResult.discrepancy_warnings.length > 0 && (
                    <div style={{ padding: '12px 16px', borderRadius: '8px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid #ef4444' }}>
                      <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#b91c1c', marginBottom: '4px' }}>
                        Bedside Discrepancy Warnings:
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.8rem', color: '#b91c1c' }}>
                        {bcmaResult.discrepancy_warnings.map((d, i) => (
                          <li key={i}>{d}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Verification Token Receipt */}
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', background: 'var(--bg-primary)', padding: '10px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                    Audit Verification Token: <code>{bcmaResult.verification_token}</code> | Timestamp: {new Date(bcmaResult.timestamp).toLocaleString()}
                  </div>
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                  Scan patient wristband and medication packaging barcode on the left to trigger real-time 5-rights verification.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: SCHEDULE INPATIENT ORDER */}
        {activeTab === 'schedule_order' && (
          <div style={{ background: 'var(--bg-secondary)', padding: '24px', borderRadius: '12px', border: '1px solid var(--border-color)', maxWidth: '640px' }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', fontWeight: 700 }}>
              ➕ Schedule Inpatient Medication Doses (eMAR)
            </h3>
            <form onSubmit={handleScheduleDoses} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                  Medication Name
                </label>
                <input
                  type="text"
                  value={schedMedName}
                  onChange={(e) => setSchedMedName(e.target.value)}
                  required
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                    RxNorm / Code
                  </label>
                  <input
                    type="text"
                    value={schedMedCode}
                    onChange={(e) => setSchedMedCode(e.target.value)}
                    required
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                    Prescribed Dose
                  </label>
                  <input
                    type="text"
                    value={schedDose}
                    onChange={(e) => setSchedDose(e.target.value)}
                    required
                    style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                    Route
                  </label>
                  <select
                    value={schedRoute}
                    onChange={(e) => setSchedRoute(e.target.value)}
                    style={{ width: '100%', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
                  >
                    <option value="oral">Oral (PO)</option>
                    <option value="subcutaneous">Subcutaneous (SubQ)</option>
                    <option value="intravenous">Intravenous (IV)</option>
                    <option value="intramuscular">Intramuscular (IM)</option>
                    <option value="inhalation">Inhalation</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                    Frequency
                  </label>
                  <select
                    value={schedFreq}
                    onChange={(e) => setSchedFreq(e.target.value)}
                    style={{ width: '100%', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
                  >
                    <option value="Q4H">Every 4 Hours (Q4H)</option>
                    <option value="Q6H">Every 6 Hours (Q6H)</option>
                    <option value="Q8H">Every 8 Hours (Q8H)</option>
                    <option value="Q12H">Twice Daily (BID / Q12H)</option>
                    <option value="TID">3 Times Daily (TID)</option>
                    <option value="DAILY">Once Daily (DAILY)</option>
                    <option value="STAT">Immediate (STAT)</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                    Total Doses
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={24}
                    value={schedTotalDoses}
                    onChange={(e) => setSchedTotalDoses(parseInt(e.target.value, 10))}
                    style={{ width: '100%', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  id="chk-high-alert"
                  checked={schedIsHighAlert}
                  onChange={(e) => setSchedIsHighAlert(e.target.checked)}
                />
                <label htmlFor="chk-high-alert" style={{ fontSize: '0.85rem', fontWeight: 600, color: '#dc2626' }}>
                  ⚠️ Flag as ISMP High-Alert Medication (Requires Independent Dual Witness Signoff)
                </label>
              </div>

              <button
                type="submit"
                style={{
                  marginTop: '10px',
                  padding: '10px 20px',
                  borderRadius: '6px',
                  background: 'var(--primary-color, #2563eb)',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: '0.9rem',
                  cursor: 'pointer',
                  border: 'none',
                }}
              >
                💾 Generate eMAR Schedule
              </button>
            </form>
          </div>
        )}

        {/* TAB 4: PHARMACY BARCODE CATALOG */}
        {activeTab === 'barcode_catalog' && (
          <div style={{ background: 'var(--bg-secondary)', padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>
                🏷️ Hospital Pharmacy Barcode Catalog (NDC & GS1-128)
              </h3>
              <input
                type="text"
                value={barcodeSearch}
                onChange={(e) => setBarcodeSearch(e.target.value)}
                placeholder="Filter by drug name or barcode..."
                style={{ padding: '6px 12px', borderRadius: '6px', fontSize: '0.8rem', width: '280px', background: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
              />
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ background: 'var(--bg-primary)', borderBottom: '2px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '8px 12px' }}>Barcode (NDC / GS1)</th>
                    <th style={{ padding: '8px 12px' }}>Medication Name</th>
                    <th style={{ padding: '8px 12px' }}>RxNorm Code</th>
                    <th style={{ padding: '8px 12px' }}>Standard Dose</th>
                    <th style={{ padding: '8px 12px' }}>Route</th>
                    <th style={{ padding: '8px 12px' }}>High-Alert Category</th>
                  </tr>
                </thead>
                <tbody>
                  {barcodes
                    .filter((b) =>
                      b.medication_name.toLowerCase().includes(barcodeSearch.toLowerCase()) ||
                      b.barcode.toLowerCase().includes(barcodeSearch.toLowerCase())
                    )
                    .map((b) => (
                      <tr key={b.id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontWeight: 700 }}>{b.barcode}</td>
                        <td style={{ padding: '8px 12px', fontWeight: 600 }}>{b.medication_name}</td>
                        <td style={{ padding: '8px 12px', color: 'var(--text-secondary)' }}>{b.rxnorm_code}</td>
                        <td style={{ padding: '8px 12px' }}>{b.standard_dose}</td>
                        <td style={{ padding: '8px 12px' }}>{b.route.toUpperCase()}</td>
                        <td style={{ padding: '8px 12px' }}>
                          {b.is_high_alert ? (
                            <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '2px 8px', borderRadius: '10px', background: '#fee2e2', color: '#b91c1c' }}>
                              ⚠️ {b.high_alert_category ? b.high_alert_category.toUpperCase() : 'HIGH ALERT'}
                            </span>
                          ) : (
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Standard</span>
                          )}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* MODAL 1: ADMINISTER DOSE */}
      {isAdministerModalOpen && selectedRecord && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'var(--bg-primary)', padding: '24px', borderRadius: '12px', maxWidth: '520px', width: '100%', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>
              💉 Bedside Medication Administration Signoff
            </h3>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Confirm administration details for <strong>{selectedRecord.medication_name}</strong>.
            </p>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Site of Administration</label>
              <select
                value={adminSite}
                onChange={(e) => setAdminSite(e.target.value)}
                style={{ width: '100%', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}
              >
                <option value="Oral Swallowed with Water">Oral Swallowed with Water</option>
                <option value="Abdomen Right Lower Quadrant SubQ">Abdomen Right Lower Quadrant SubQ</option>
                <option value="Left Deltoid IM">Left Deltoid IM</option>
                <option value="Right Deltoid IM">Right Deltoid IM</option>
                <option value="Right Antecubital IV Infusion">Right Antecubital IV Infusion</option>
                <option value="Left Forearm Peripheral IV">Left Forearm Peripheral IV</option>
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600 }}>Pre-Admin BP</label>
                <input
                  type="text"
                  value={bpValue}
                  onChange={(e) => setBpValue(e.target.value)}
                  style={{ width: '100%', padding: '6px', borderRadius: '4px', fontSize: '0.8rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600 }}>Heart Rate</label>
                <input
                  type="text"
                  value={pulseValue}
                  onChange={(e) => setPulseValue(e.target.value)}
                  style={{ width: '100%', padding: '6px', borderRadius: '4px', fontSize: '0.8rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600 }}>Blood Glucose</label>
                <input
                  type="text"
                  value={glucoseValue}
                  onChange={(e) => setGlucoseValue(e.target.value)}
                  style={{ width: '100%', padding: '6px', borderRadius: '4px', fontSize: '0.8rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Patient Response / Nursing Notes</label>
              <textarea
                value={patientResponseNotes}
                onChange={(e) => setPatientResponseNotes(e.target.value)}
                rows={2}
                style={{ width: '100%', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
              <button
                onClick={() => setIsAdministerModalOpen(false)}
                style={{ padding: '8px 16px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                id="btn-confirm-administer"
                onClick={handleAdminister}
                style={{ padding: '8px 16px', borderRadius: '6px', background: '#059669', color: '#fff', fontWeight: 700, border: 'none', cursor: 'pointer' }}
              >
                ✓ Confirm Administration
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: HOLD / REFUSE DOSE */}
      {isHoldModalOpen && selectedRecord && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'var(--bg-primary)', padding: '24px', borderRadius: '12px', maxWidth: '480px', width: '100%', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>
              🛑 Document Held / Refused Dose
            </h3>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>Status Action</label>
              <select
                value={holdStatus}
                onChange={(e) => setHoldStatus(e.target.value as any)}
                style={{ width: '100%', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}
              >
                <option value="held">Held (Clinical Parameter)</option>
                <option value="refused">Refused (Patient Choice)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                Mandatory Clinical Justification
              </label>
              <textarea
                value={holdReason}
                onChange={(e) => setHoldReason(e.target.value)}
                required
                rows={3}
                placeholder="Document clinical reason (e.g. SBP < 90, NPO for procedure, patient refused nausea medication)..."
                style={{ width: '100%', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
              <button
                onClick={() => setIsHoldModalOpen(false)}
                style={{ padding: '8px 16px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                id="btn-confirm-hold-refuse"
                onClick={handleHoldRefuse}
                style={{ padding: '8px 16px', borderRadius: '6px', background: '#d97706', color: '#fff', fontWeight: 700, border: 'none', cursor: 'pointer' }}
              >
                🛑 Confirm Documentation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: DUAL CLINICIAN WITNESS SIGNOFF */}
      {isDualSignoffModalOpen && selectedRecord && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ background: 'var(--bg-primary)', padding: '24px', borderRadius: '12px', maxWidth: '480px', width: '100%', border: '1px solid var(--border-color)', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: '#7c3aed' }}>
              👥 Independent Dual-Clinician Witness Signoff
            </h3>
            <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              Independent credential verification for High-Alert medication <strong>{selectedRecord.medication_name}</strong>.
            </p>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                Witness Clinician Email
              </label>
              <input
                type="email"
                value={witnessEmail}
                onChange={(e) => setWitnessEmail(e.target.value)}
                required
                style={{ width: '100%', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                Witness Password
              </label>
              <input
                type="password"
                value={witnessPassword}
                onChange={(e) => setWitnessPassword(e.target.value)}
                placeholder="Enter witness password..."
                required
                style={{ width: '100%', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                Witness Independent Check Notes
              </label>
              <textarea
                value={witnessNotes}
                onChange={(e) => setWitnessNotes(e.target.value)}
                rows={2}
                style={{ width: '100%', padding: '8px', borderRadius: '6px', fontSize: '0.85rem', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
              <button
                onClick={() => setIsDualSignoffModalOpen(false)}
                style={{ padding: '8px 16px', borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border-color)', cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                id="btn-confirm-dual-signoff"
                onClick={handleDualSignoff}
                disabled={!witnessEmail || !witnessPassword}
                style={{ padding: '8px 16px', borderRadius: '6px', background: '#7c3aed', color: '#fff', fontWeight: 700, border: 'none', cursor: 'pointer' }}
              >
                ✓ Authenticate Witness
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
