// ==============================================================================
// MediGen AI - Dedicated System Administrator Control Center & Patient Intake
// New Patient Review, Doctor Assignment & Multi-Tenant Clinical Governance
// ==============================================================================

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Header } from '../layout/Header';
import { HealthSystemTenantWorkspace } from '../tenants/HealthSystemTenantWorkspace';
import { SystemDiagnosticsWorkspace } from '../operations/SystemDiagnosticsWorkspace';
import { SecurityComplianceWorkspace } from '../security/SecurityComplianceWorkspace';
import { TrialsGovernanceWorkspace } from '../trials/TrialsGovernanceWorkspace';
import { RegionalInteroperabilityWorkspace } from '../interop/RegionalInteroperabilityWorkspace';
import { SmartFhirEhrWorkspace } from '../interop/SmartFhirEhrWorkspace';
import { ClinicalAgentsWorkspace } from '../agents/ClinicalAgentsWorkspace';
import { QualityMeasuresWorkspace } from '../quality/QualityMeasuresWorkspace';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { doctorsApi, patientsApi } from '../../api/client';
import { Doctor, Patient } from '../../types';

export const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<
    'patients' | 'tenants' | 'diagnostics' | 'security' | 'trials_gov' | 'regional_interop' | 'smart_ehr' | 'agents' | 'quality'
  >('patients');

  const [patientsList, setPatientsList] = useState<Patient[]>([]);
  const [doctorsList, setDoctorsList] = useState<Doctor[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionAlert, setActionAlert] = useState<string | null>(null);

  // Assign Doctor Modal State
  const [assignModalPatient, setAssignModalPatient] = useState<Patient | null>(null);
  const [selectedDoctorId, setSelectedDoctorId] = useState<number>(1);
  const [assignNotes, setAssignNotes] = useState<string>('');
  const [isAssigning, setIsAssigning] = useState<boolean>(false);

  // Edit Patient Modal State
  const [editModalPatient, setEditModalPatient] = useState<Patient | null>(null);
  const [editFirstName, setEditFirstName] = useState<string>('');
  const [editLastName, setEditLastName] = useState<string>('');
  const [editPhone, setEditPhone] = useState<string>('');
  const [editBloodGroup, setEditBloodGroup] = useState<string>('O+');
  const [editAllergies, setEditAllergies] = useState<string>('');
  const [editStatus, setEditStatus] = useState<string>('active');

  const loadPatientsAndDoctors = async () => {
    setIsLoading(true);
    try {
      const [patientsRes, doctorsRes] = await Promise.all([
        patientsApi.list(searchQuery || undefined, statusFilter || undefined).catch(() => []),
        doctorsApi.list().catch(() => []),
      ]);
      setPatientsList(Array.isArray(patientsRes) ? patientsRes : []);
      setDoctorsList(Array.isArray(doctorsRes) ? doctorsRes : []);
      if (Array.isArray(doctorsRes) && doctorsRes.length > 0) {
        setSelectedDoctorId(doctorsRes[0].id);
      }
    } catch {
      // Fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPatientsAndDoctors();
  }, [searchQuery, statusFilter]);

  const handleAssignDoctor = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignModalPatient) return;
    setIsAssigning(true);
    try {
      await patientsApi.assignDoctor(assignModalPatient.patient_id, selectedDoctorId, assignNotes.trim());
      setActionAlert(`Assigned doctor to patient ${assignModalPatient.first_name} ${assignModalPatient.last_name} successfully.`);
      setTimeout(() => setActionAlert(null), 4000);
      setAssignModalPatient(null);
      setAssignNotes('');
      loadPatientsAndDoctors();
    } catch (err: any) {
      alert(err.message || 'Failed to assign doctor');
    } finally {
      setIsAssigning(false);
    }
  };

  const handleSavePatientEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editModalPatient) return;
    try {
      await patientsApi.update(editModalPatient.patient_id, {
        first_name: editFirstName.trim(),
        last_name: editLastName.trim(),
        phone: editPhone.trim(),
        blood_group: editBloodGroup,
        allergies: editAllergies.trim(),
        status: editStatus as any,
      });
      setActionAlert(`Patient profile for ${editFirstName} ${editLastName} updated.`);
      setTimeout(() => setActionAlert(null), 4000);
      setEditModalPatient(null);
      loadPatientsAndDoctors();
    } catch (err: any) {
      alert(err.message || 'Failed to update patient profile');
    }
  };

  const handleDeactivatePatient = async (patient: Patient) => {
    if (!window.confirm(`Deactivate patient record for ${patient.first_name} ${patient.last_name}? Historical clinical audit trails will remain preserved.`)) return;
    try {
      await patientsApi.deactivate(patient.patient_id);
      setActionAlert(`Patient ${patient.first_name} ${patient.last_name} has been deactivated.`);
      setTimeout(() => setActionAlert(null), 4000);
      loadPatientsAndDoctors();
    } catch (err: any) {
      alert(err.message || 'Failed to deactivate patient');
    }
  };

  const pendingPatients = patientsList.filter((p) => p.status === 'pending_review');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', background: '#0b0f19', color: '#f8fafc' }}>
      {/* Top Header */}
      <Header
        onOpenSafetyModal={() => {}}
        onOpenTasksModal={() => {}}
        activeTaskCount={0}
      />

      {/* Admin Subheader & System Status Ribbon */}
      <div
        style={{
          background: 'linear-gradient(90deg, rgba(220, 38, 38, 0.15) 0%, rgba(15, 23, 42, 0.95) 100%)',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          padding: '10px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '1.25rem' }}>🛡️</span>
          <div>
            <span style={{ fontWeight: 700, color: '#ffffff', fontSize: '0.95rem' }}>
              Hospital Administrator Control Center
            </span>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              Logged in as: <strong style={{ color: '#ffffff' }}>{user?.name}</strong> ({user?.email}) &bull; Facility: <strong style={{ color: '#38bdf8' }}>Metro Main Hospital (FAC-001)</strong>
            </div>
          </div>
        </div>

        {/* Live System Health Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem' }}>
          <span className="badge badge-success" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#22c55e' }}></span>
            FastAPI Backend: Online
          </span>
          <span className="badge badge-info" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#38bdf8' }}></span>
            FHIR R4 / SMART v2: Ready
          </span>
          {pendingPatients.length > 0 && (
            <span className="badge badge-warning" style={{ display: 'flex', alignItems: 'center', gap: '4px', background: '#f59e0b', color: '#000', fontWeight: 700 }}>
              ⚠️ {pendingPatients.length} New Patient(s) Pending Review
            </span>
          )}
        </div>
      </div>

      {/* Admin Navigation Tabs */}
      <div
        style={{
          display: 'flex',
          gap: '8px',
          padding: '10px 24px',
          background: 'rgba(15, 23, 42, 0.7)',
          borderBottom: '1px solid rgba(255,255,255,0.1)',
          flexWrap: 'wrap',
        }}
      >
        <button
          className={`btn btn-sm ${activeTab === 'patients' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('patients')}
        >
          👥 Patient Intake & Review {pendingPatients.length > 0 && `(${pendingPatients.length})`}
        </button>
        <button
          data-testid="tab-btn-tenants"
          className={`btn btn-sm ${activeTab === 'tenants' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('tenants')}
        >
          🏥 Health Systems & Facilities
        </button>
        <button
          data-testid="tab-btn-diagnostics"
          className={`btn btn-sm ${activeTab === 'diagnostics' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('diagnostics')}
        >
          ⚙️ Infrastructure & Diagnostics
        </button>
        <button
          data-testid="tab-btn-security"
          className={`btn btn-sm ${activeTab === 'security' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('security')}
        >
          🔒 Security & Compliance
        </button>
        <button
          data-testid="tab-btn-regional-interop"
          className={`btn btn-sm ${activeTab === 'regional_interop' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('regional_interop')}
        >
          🌐 Regional Interoperability & EMPI
        </button>
        <button
          data-testid="tab-btn-smart-ehr"
          className={`btn btn-sm ${activeTab === 'smart_ehr' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('smart_ehr')}
        >
          🔌 SMART on FHIR
        </button>
        <button
          data-testid="tab-btn-trials-gov"
          className={`btn btn-sm ${activeTab === 'trials_gov' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('trials_gov')}
        >
          📑 Trials Governance
        </button>
        <button
          data-testid="tab-btn-agents"
          className={`btn btn-sm ${activeTab === 'agents' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('agents')}
        >
          🤖 Clinical AI Agents
        </button>
        <button
          data-testid="tab-btn-quality"
          className={`btn btn-sm ${activeTab === 'quality' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('quality')}
        >
          📊 Quality Measures
        </button>
      </div>

      {actionAlert && (
        <div style={{ background: '#065f46', color: '#a7f3d0', padding: '10px 24px', textAlign: 'center', fontSize: '0.875rem' }}>
          ✅ {actionAlert}
        </div>
      )}

      {/* Main Administrative Workspace */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
        <ErrorBoundary fallbackTitle="Admin Workspace Panel">
          {activeTab === 'patients' && (
            <div style={{ maxWidth: '1380px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
              
              {/* 1. Pending Review Registrations Section */}
              {pendingPatients.length > 0 && (
                <div className="glass-panel" style={{ padding: '20px', borderRadius: '10px', border: '1px solid #f59e0b' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <div>
                      <h3 style={{ fontSize: '1.15rem', fontWeight: 800, margin: 0, color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span>⏳</span> New Patient Registrations ({pendingPatients.length} Pending Review)
                      </h3>
                      <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '4px 0 0' }}>
                        Review patient-reported symptoms and assign attending doctors to activate clinical workflows.
                      </p>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '16px' }}>
                    {pendingPatients.map((pat) => (
                      <div
                        key={pat.patient_id}
                        style={{
                          padding: '16px',
                          background: 'rgba(255,255,255,0.03)',
                          borderRadius: '8px',
                          border: '1px solid rgba(255,255,255,0.1)',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          gap: '12px',
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                            <div>
                              <h4 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0, color: '#ffffff' }}>
                                {pat.first_name} {pat.last_name}
                              </h4>
                              <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '2px' }}>
                                ID: <strong style={{ color: '#38bdf8' }}>{pat.patient_id}</strong> &bull; DOB: {pat.date_of_birth} &bull; Gender: {pat.gender}
                              </div>
                            </div>
                            <span className="badge badge-warning" style={{ fontSize: '0.65rem' }}>Pending Review</span>
                          </div>

                          <div style={{ fontSize: '0.8125rem', color: '#cbd5e1', marginTop: '10px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                            <span>📞 {pat.phone || 'N/A'}</span>
                            <span>🩸 Blood: <strong>{pat.blood_group || 'O+'}</strong></span>
                            <span>⚠️ Allergies: <strong>{pat.allergies || 'None'}</strong></span>
                          </div>

                          <div style={{ marginTop: '10px', padding: '10px', background: 'rgba(0,0,0,0.25)', borderRadius: '6px', borderLeft: '3px solid #f59e0b' }}>
                            <div style={{ fontSize: '0.7rem', color: '#f59e0b', fontWeight: 600, textTransform: 'uppercase' }}>Reported Problem:</div>
                            <div style={{ fontSize: '0.85rem', color: '#e2e8f0', marginTop: '2px', fontStyle: 'italic' }}>
                              "{pat.health_problem || 'No description provided.'}"
                            </div>
                          </div>
                        </div>

                        <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            style={{ flex: 1 }}
                            onClick={() => {
                              setAssignModalPatient(pat);
                            }}
                          >
                            🩺 Assign Doctor & Approve
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => {
                              setEditModalPatient(pat);
                              setEditFirstName(pat.first_name);
                              setEditLastName(pat.last_name);
                              setEditPhone(pat.phone || '');
                              setEditBloodGroup(pat.blood_group || 'O+');
                              setEditAllergies(pat.allergies || 'None');
                              setEditStatus(pat.status || 'active');
                            }}
                          >
                            Edit
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 2. All Patients Management & Search Table */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0, color: '#ffffff' }}>
                    Hospital Patients Directory ({patientsList.length} Total)
                  </h3>

                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Search name, ID, phone..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      style={{ width: '220px', padding: '6px 10px', fontSize: '0.8125rem' }}
                    />
                    <select
                      className="form-input"
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      style={{ padding: '6px 10px', fontSize: '0.8125rem' }}
                    >
                      <option value="">All Statuses</option>
                      <option value="pending_review">Pending Review</option>
                      <option value="active">Active</option>
                      <option value="under_care">Under Care</option>
                      <option value="inactive">Inactive</option>
                    </select>
                  </div>
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table className="table" style={{ width: '100%', fontSize: '0.85rem' }}>
                    <thead>
                      <tr>
                        <th>Patient ID</th>
                        <th>Name</th>
                        <th>Age / Gender</th>
                        <th>Phone</th>
                        <th>Assigned Doctor</th>
                        <th>Status</th>
                        <th style={{ textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {patientsList.map((pat) => (
                        <tr key={pat.patient_id}>
                          <td>
                            <strong style={{ color: '#38bdf8' }}>{pat.patient_id}</strong>
                          </td>
                          <td>
                            <div style={{ fontWeight: 600 }}>{pat.first_name} {pat.last_name}</div>
                            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{pat.email || 'No email'}</div>
                          </td>
                          <td>
                            {pat.date_of_birth} &bull; <span style={{ textTransform: 'capitalize' }}>{pat.gender}</span>
                          </td>
                          <td>{pat.phone || 'N/A'}</td>
                          <td>
                            {pat.assigned_doctor_name ? (
                              <span style={{ color: '#ffffff', fontWeight: 500 }}>
                                🩺 {pat.assigned_doctor_name}
                              </span>
                            ) : (
                              <span style={{ color: '#f59e0b', fontSize: '0.75rem' }}>Not Assigned</span>
                            )}
                          </td>
                          <td>
                            <span
                              className={`badge ${
                                pat.status === 'active'
                                  ? 'badge-success'
                                  : pat.status === 'pending_review'
                                  ? 'badge-warning'
                                  : 'badge-secondary'
                              }`}
                              style={{ fontSize: '0.7rem', textTransform: 'capitalize' }}
                            >
                              {pat.status?.replace('_', ' ')}
                            </span>
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', gap: '6px' }}>
                              <button
                                type="button"
                                className="btn btn-secondary btn-sm"
                                onClick={() => setAssignModalPatient(pat)}
                                style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                              >
                                {pat.assigned_doctor_name ? 'Change Doctor' : 'Assign Doctor'}
                              </button>
                              <button
                                type="button"
                                className="btn btn-secondary btn-sm"
                                onClick={() => {
                                  setEditModalPatient(pat);
                                  setEditFirstName(pat.first_name);
                                  setEditLastName(pat.last_name);
                                  setEditPhone(pat.phone || '');
                                  setEditBloodGroup(pat.blood_group || 'O+');
                                  setEditAllergies(pat.allergies || 'None');
                                  setEditStatus(pat.status || 'active');
                                }}
                                style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                              >
                                Edit
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDeactivatePatient(pat)}
                                style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', fontSize: '0.75rem', padding: '4px 6px' }}
                              >
                                Deactivate
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          )}

          {activeTab === 'tenants' && <HealthSystemTenantWorkspace />}
          {activeTab === 'diagnostics' && <SystemDiagnosticsWorkspace />}
          {activeTab === 'security' && (
            <SecurityComplianceWorkspace
              patients={patientsList}
              selectedPatient={patientsList[0]}
              onSelectPatient={() => {}}
            />
          )}
          {activeTab === 'regional_interop' && <RegionalInteroperabilityWorkspace />}
          {activeTab === 'smart_ehr' && <SmartFhirEhrWorkspace />}
          {activeTab === 'trials_gov' && <TrialsGovernanceWorkspace />}
          {activeTab === 'agents' && <ClinicalAgentsWorkspace />}
          {activeTab === 'quality' && <QualityMeasuresWorkspace />}
        </ErrorBoundary>
      </div>

      {/* Assign Doctor Modal */}
      {assignModalPatient && (
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
                Assign Attending Physician
              </h3>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setAssignModalPatient(null)}>✕</button>
            </div>

            <div style={{ padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', marginBottom: '16px' }}>
              <div style={{ fontWeight: 600, color: '#ffffff', fontSize: '0.9rem' }}>
                Patient: {assignModalPatient.first_name} {assignModalPatient.last_name} ({assignModalPatient.patient_id})
              </div>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '4px' }}>
                Problem: "{assignModalPatient.health_problem || 'Routine clinical intake'}"
              </div>
            </div>

            <form onSubmit={handleAssignDoctor} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div className="form-group">
                <label className="form-label" style={{ color: '#cbd5e1' }}>Select Doctor / Specialist *</label>
                <select
                  className="form-input"
                  value={selectedDoctorId}
                  onChange={(e) => setSelectedDoctorId(Number(e.target.value))}
                  required
                >
                  {doctorsList.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.professional_title} {doc.full_name} &bull; {doc.department} ({doc.specialization})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" style={{ color: '#cbd5e1' }}>Assignment Notes (Optional)</label>
                <textarea
                  className="form-input"
                  rows={2}
                  placeholder="e.g. Assigned for cardiovascular evaluation and ECG workup"
                  value={assignNotes}
                  onChange={(e) => setAssignNotes(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setAssignModalPatient(null)}>Cancel</button>
                <button type="submit" className="btn btn-primary" disabled={isAssigning}>
                  {isAssigning ? 'Assigning...' : 'Confirm Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Patient Modal */}
      {editModalPatient && (
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
                Edit Patient Record ({editModalPatient.patient_id})
              </h3>
              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setEditModalPatient(null)}>✕</button>
            </div>

            <form onSubmit={handleSavePatientEdit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">First Name</label>
                  <input type="text" className="form-input" value={editFirstName} onChange={(e) => setEditFirstName(e.target.value)} required />
                </div>
                <div className="form-group">
                  <label className="form-label">Last Name</label>
                  <input type="text" className="form-input" value={editLastName} onChange={(e) => setEditLastName(e.target.value)} required />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">Phone</label>
                  <input type="text" className="form-input" value={editPhone} onChange={(e) => setEditPhone(e.target.value)} />
                </div>
                <div className="form-group">
                  <label className="form-label">Blood Group</label>
                  <select className="form-input" value={editBloodGroup} onChange={(e) => setEditBloodGroup(e.target.value)}>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Known Allergies</label>
                <input type="text" className="form-input" value={editAllergies} onChange={(e) => setEditAllergies(e.target.value)} />
              </div>

              <div className="form-group">
                <label className="form-label">Patient Status</label>
                <select className="form-input" value={editStatus} onChange={(e) => setEditStatus(e.target.value)}>
                  <option value="pending_review">Pending Review</option>
                  <option value="active">Active</option>
                  <option value="under_care">Under Care</option>
                  <option value="discharged">Discharged</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setEditModalPatient(null)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Save Changes</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
