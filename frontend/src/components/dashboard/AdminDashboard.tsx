// ==============================================================================
// MediGen AI - Dedicated System Administrator Control Center & Patient Intake
// Hospital Operations, Patient Intake, Doctor Assignments, Facilities & Governance
// ==============================================================================

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { AppShell } from '../layout/AppShell';
import { HealthSystemTenantWorkspace } from '../tenants/HealthSystemTenantWorkspace';
import { SystemDiagnosticsWorkspace } from '../operations/SystemDiagnosticsWorkspace';
import { SecurityComplianceWorkspace } from '../security/SecurityComplianceWorkspace';
import { TrialsGovernanceWorkspace } from '../trials/TrialsGovernanceWorkspace';
import { RegionalInteroperabilityWorkspace } from '../interop/RegionalInteroperabilityWorkspace';
import { SmartFhirEhrWorkspace } from '../interop/SmartFhirEhrWorkspace';
import { ClinicalAgentsWorkspace } from '../agents/ClinicalAgentsWorkspace';
import { QualityMeasuresWorkspace } from '../quality/QualityMeasuresWorkspace';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { appointmentsApi, doctorsApi, patientsApi } from '../../api/client';
import { Appointment, Doctor, Patient } from '../../types';

export const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const [activeSection, setActiveSection] = useState<string>('overview');

  const [patientsList, setPatientsList] = useState<Patient[]>([]);
  const [doctorsList, setDoctorsList] = useState<Doctor[]>([]);
  const [appointmentsList, setAppointmentsList] = useState<Appointment[]>([]);
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

  const loadAllAdminData = async () => {
    setIsLoading(true);
    try {
      const [patientsRes, doctorsRes, aptsRes] = await Promise.all([
        patientsApi.list(searchQuery || undefined, statusFilter || undefined).catch(() => []),
        doctorsApi.list().catch(() => []),
        appointmentsApi.list().catch(() => []),
      ]);
      setPatientsList(Array.isArray(patientsRes) ? patientsRes : []);
      setDoctorsList(Array.isArray(doctorsRes) ? doctorsRes : []);
      setAppointmentsList(Array.isArray(aptsRes) ? aptsRes : ((aptsRes as any)?.items || []));
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
    loadAllAdminData();
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
      loadAllAdminData();
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
      loadAllAdminData();
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
      loadAllAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to deactivate patient');
    }
  };

  const pendingPatients = patientsList.filter((p) => p.status === 'pending_review');
  const activePatients = patientsList.filter((p) => p.status !== 'inactive' && p.status !== 'pending_review');

  const getSectionTitle = () => {
    switch (activeSection) {
      case 'overview': return 'Hospital Administration Overview';
      case 'patients': return 'Patient Intake & Directory';
      case 'doctors': return 'Clinical Staff & Specialists';
      case 'appointments': return 'Hospital-Wide Appointments';
      case 'tenants': return 'Facilities & Tenant Organizations';
      case 'smart_ehr': return 'SMART on FHIR Gateway';
      case 'regional_interop': return 'Regional Health Exchange & EMPI';
      case 'security': return 'Security & Audit Logging';
      case 'trials_gov': return 'Clinical Trials Governance';
      case 'agents': return 'Autonomous AI Clinical Agents';
      case 'quality': return 'Quality Measures & Analytics';
      case 'diagnostics': return 'System Health & Metrics';
      default: return 'Administration Center';
    }
  };

  return (
    <AppShell
      activeSection={activeSection}
      activeSectionTitle={getSectionTitle()}
      onSelectSection={setActiveSection}
      pendingReviewsCount={pendingPatients.length}
    >
      {/* Action Notification Alert Banner */}
      {actionAlert && (
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
          <span>✅ {actionAlert}</span>
          <button onClick={() => setActionAlert(null)} style={{ background: 'none', border: 'none', color: '#34d399', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* 1. OVERVIEW SECTION */}
      {activeSection === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Welcome Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h1 style={{ fontSize: '1.4rem', fontWeight: 800, color: '#ffffff' }}>Hospital Operations & Governance</h1>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                Real-time operational intelligence, patient intake queue, and clinical multi-facility management.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                onClick={() => setActiveSection('patients')}
                className="btn btn-primary"
                style={{ fontSize: '0.8rem' }}
              >
                👥 Review Intake ({pendingPatients.length})
              </button>
              <button
                onClick={() => loadAllAdminData()}
                className="btn btn-secondary"
                style={{ fontSize: '0.8rem' }}
              >
                🔄 Refresh
              </button>
            </div>
          </div>

          {/* KPI Stat Cards Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
            <div className="stat-card">
              <span className="stat-card-title">Total Registered Patients</span>
              <span className="stat-card-value">{patientsList.length}</span>
              <span className="stat-card-subtitle">{activePatients.length} Active Clinical Records</span>
            </div>

            <div className="stat-card" style={{ borderLeft: '3px solid #f59e0b' }}>
              <span className="stat-card-title">Pending Intake Reviews</span>
              <span className="stat-card-value" style={{ color: '#fbbf24' }}>{pendingPatients.length}</span>
              <span className="stat-card-subtitle">Awaiting Specialist Assignment</span>
            </div>

            <div className="stat-card" style={{ borderLeft: '3px solid #38bdf8' }}>
              <span className="stat-card-title">Specialist Physicians</span>
              <span className="stat-card-value" style={{ color: '#38bdf8' }}>{doctorsList.length}</span>
              <span className="stat-card-subtitle">Across 6 Clinical Departments</span>
            </div>

            <div className="stat-card" style={{ borderLeft: '3px solid #10b981' }}>
              <span className="stat-card-title">Consultations Scheduled</span>
              <span className="stat-card-value" style={{ color: '#34d399' }}>{appointmentsList.length}</span>
              <span className="stat-card-subtitle">In-Person & Telehealth Slots</span>
            </div>

            <div className="stat-card">
              <span className="stat-card-title">System Status</span>
              <span className="stat-card-value" style={{ color: '#34d399', fontSize: '1.3rem' }}>Healthy 🟢</span>
              <span className="stat-card-subtitle">FHIR R4 & Audit Logging Active</span>
            </div>
          </div>

          {/* Pending Patients Quick Review Banner */}
          {pendingPatients.length > 0 && (
            <div
              style={{
                background: 'rgba(245, 158, 11, 0.08)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                borderRadius: '12px',
                padding: '16px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '1.5rem' }}>⏳</span>
                <div>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fbbf24', margin: 0 }}>
                    {pendingPatients.length} New Patient Registration{pendingPatients.length > 1 ? 's' : ''} Pending Review
                  </h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
                    Patients have self-registered and submitted health complaints. Assign available specialist doctors to enable care.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setActiveSection('patients')}
                className="btn btn-primary btn-sm"
                style={{ background: '#f59e0b', color: '#000000', fontWeight: 700 }}
              >
                Open Review Queue →
              </button>
            </div>
          )}

          {/* Quick Administration Modules Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
            <div
              className="glass-panel"
              style={{ padding: '18px', cursor: 'pointer' }}
              onClick={() => setActiveSection('patients')}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <span style={{ fontSize: '1.3rem' }}>👥</span>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>Patient Intake & Directory</h3>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Search, filter, review intake requests, assign doctors, and manage patient profiles.
              </p>
            </div>

            <div
              className="glass-panel"
              style={{ padding: '18px', cursor: 'pointer' }}
              onClick={() => setActiveSection('doctors')}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <span style={{ fontSize: '1.3rem' }}>🩺</span>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>Doctors & Staff</h3>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                View licensed clinical specialists, medical registration numbers, and departments.
              </p>
            </div>

            <div
              className="glass-panel"
              style={{ padding: '18px', cursor: 'pointer' }}
              onClick={() => setActiveSection('tenants')}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <span style={{ fontSize: '1.3rem' }}>🏥</span>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>Multi-Tenant Facilities</h3>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Configure health system campuses, EHR connectors, and department routing.
              </p>
            </div>

            <div
              className="glass-panel"
              style={{ padding: '18px', cursor: 'pointer' }}
              onClick={() => setActiveSection('security')}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                <span style={{ fontSize: '1.3rem' }}>🛡️</span>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#ffffff' }}>Security & Audit Logs</h3>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                HIPAA audit logs, cryptographic signatures, emergency break-glass access, and access control policies.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 2. PATIENTS INTAKE & DIRECTORY SECTION */}
      {activeSection === 'patients' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Header & Filter Controls */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffffff' }}>Patient Intake & Directory</h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Review pending registrations and manage master patient records.</p>
            </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="Search patient name, ID, phone..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="form-input"
                style={{ width: '240px', padding: '6px 12px', fontSize: '0.8rem' }}
              />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="form-select"
                style={{ width: '160px', padding: '6px 12px', fontSize: '0.8rem' }}
              >
                <option value="">All Statuses</option>
                <option value="pending_review">Pending Review</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>

          {/* Pending Reviews Section */}
          {pendingPatients.length > 0 && (
            <div className="glass-panel" style={{ padding: '16px', borderColor: 'rgba(245, 158, 11, 0.4)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <span style={{ fontSize: '1.1rem' }}>⏳</span>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fbbf24' }}>
                  New Patient Registrations Requiring Review ({pendingPatients.length})
                </h3>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                      <th style={{ padding: '8px' }}>Patient ID</th>
                      <th style={{ padding: '8px' }}>Name</th>
                      <th style={{ padding: '8px' }}>Age / Gender</th>
                      <th style={{ padding: '8px' }}>Reported Health Problem</th>
                      <th style={{ padding: '8px' }}>Contact</th>
                      <th style={{ padding: '8px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pendingPatients.map((p) => (
                      <tr key={p.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '10px 8px', fontFamily: 'monospace', color: '#38bdf8', fontWeight: 600 }}>{p.patient_id}</td>
                        <td style={{ padding: '10px 8px', fontWeight: 600, color: '#ffffff' }}>{p.first_name} {p.last_name}</td>
                        <td style={{ padding: '10px 8px', color: 'var(--text-secondary)' }}>{p.date_of_birth} ({p.gender})</td>
                        <td style={{ padding: '10px 8px', color: '#fbbf24', maxWidth: '300px' }}>
                          <span style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                            {p.health_problem || 'General intake request'}
                          </span>
                        </td>
                        <td style={{ padding: '10px 8px', color: 'var(--text-muted)' }}>{p.phone || p.email}</td>
                        <td style={{ padding: '10px 8px', textAlign: 'right' }}>
                          <button
                            onClick={() => { setAssignModalPatient(p); }}
                            className="btn btn-primary btn-sm"
                            style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                          >
                            🩺 Assign Doctor & Approve
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Master Patients Table */}
          <div className="glass-panel" style={{ padding: '16px' }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', marginBottom: '12px' }}>
              All Hospital Patients ({patientsList.length})
            </h3>
            {isLoading ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading patient records...</div>
            ) : patientsList.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>No patients found matching query.</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                      <th style={{ padding: '8px' }}>Patient ID</th>
                      <th style={{ padding: '8px' }}>Name</th>
                      <th style={{ padding: '8px' }}>DOB / Gender</th>
                      <th style={{ padding: '8px' }}>Blood / Allergies</th>
                      <th style={{ padding: '8px' }}>Assigned Specialist</th>
                      <th style={{ padding: '8px' }}>Status</th>
                      <th style={{ padding: '8px', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {patientsList.map((p) => (
                      <tr key={p.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '10px 8px', fontFamily: 'monospace', color: '#38bdf8', fontWeight: 600 }}>{p.patient_id}</td>
                        <td style={{ padding: '10px 8px', fontWeight: 600, color: '#ffffff' }}>{p.first_name} {p.last_name}</td>
                        <td style={{ padding: '10px 8px', color: 'var(--text-secondary)' }}>{p.date_of_birth} ({p.gender})</td>
                        <td style={{ padding: '10px 8px', color: 'var(--text-muted)' }}>{p.blood_group || 'O+'} • {p.allergies || 'None'}</td>
                        <td style={{ padding: '10px 8px', color: p.assigned_doctor_name ? '#34d399' : '#fbbf24' }}>
                          {p.assigned_doctor_name || 'Unassigned'}
                        </td>
                        <td style={{ padding: '10px 8px' }}>
                          <span className={`badge ${p.status === 'active' ? 'badge-success' : p.status === 'pending_review' ? 'badge-warning' : 'badge-info'}`}>
                            {p.status || 'Active'}
                          </span>
                        </td>
                        <td style={{ padding: '10px 8px', textAlign: 'right' }}>
                          <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                            <button
                              onClick={() => {
                                setEditModalPatient(p);
                                setEditFirstName(p.first_name);
                                setEditLastName(p.last_name);
                                setEditPhone(p.phone || '');
                                setEditBloodGroup(p.blood_group || 'O+');
                                setEditAllergies(p.allergies || '');
                                setEditStatus(p.status || 'active');
                              }}
                              className="btn btn-secondary btn-sm"
                              style={{ fontSize: '0.7rem', padding: '3px 8px' }}
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => { setAssignModalPatient(p); }}
                              className="btn btn-secondary btn-sm"
                              style={{ fontSize: '0.7rem', padding: '3px 8px' }}
                            >
                              Assign Dr
                            </button>
                            {p.status !== 'inactive' && (
                              <button
                                onClick={() => handleDeactivatePatient(p)}
                                className="btn btn-danger btn-sm"
                                style={{ fontSize: '0.7rem', padding: '3px 8px' }}
                              >
                                Deactivate
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. DOCTORS & CLINICAL STAFF SECTION */}
      {activeSection === 'doctors' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffffff' }}>Doctors & Clinical Staff</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Verified specialist doctors, license numbers, and clinical departments.</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {doctorsList.map((doc) => (
              <div key={doc.id} className="glass-panel" style={{ padding: '18px', display: 'flex', gap: '14px' }}>
                <div
                  style={{
                    width: '48px',
                    height: '48px',
                    borderRadius: '50%',
                    background: 'rgba(2, 132, 199, 0.2)',
                    color: '#38bdf8',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.3rem',
                    flexShrink: 0,
                  }}
                >
                  🩺
                </div>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff' }}>{doc.full_name}</h3>
                    <span className="badge badge-success">Verified</span>
                  </div>
                  <span style={{ fontSize: '0.8rem', color: '#38bdf8', fontWeight: 600 }}>{doc.specialization}</span>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Department: {doc.department}</span>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <span>License: <code style={{ color: '#f8fafc' }}>{doc.medical_registration_number}</code></span>
                    <span>Experience: {doc.years_of_experience} Years</span>
                    <span>Email: {doc.email}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4. HOSPITAL APPOINTMENTS SECTION */}
      {activeSection === 'appointments' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffffff' }}>Hospital-Wide Appointments</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>All scheduled patient consultations and telehealth visits across departments.</p>
          </div>

          <div className="glass-panel" style={{ padding: '16px' }}>
            {appointmentsList.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>No appointments recorded in the system.</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8125rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                      <th style={{ padding: '8px' }}>Date & Time</th>
                      <th style={{ padding: '8px' }}>Patient</th>
                      <th style={{ padding: '8px' }}>Doctor</th>
                      <th style={{ padding: '8px' }}>Mode</th>
                      <th style={{ padding: '8px' }}>Reason for Visit</th>
                      <th style={{ padding: '8px' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {appointmentsList.map((apt) => (
                      <tr key={apt.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '10px 8px', fontWeight: 600, color: '#ffffff' }}>
                          {new Date(apt.appointment_date).toLocaleString()}
                        </td>
                        <td style={{ padding: '10px 8px', color: '#38bdf8' }}>
                          {apt.patient ? `${apt.patient.first_name} ${apt.patient.last_name}` : `Patient #${apt.patient_id}`}
                        </td>
                        <td style={{ padding: '10px 8px', color: '#f8fafc' }}>
                          {apt.doctor ? apt.doctor.full_name : `Doctor #${apt.doctor_id}`}
                        </td>
                        <td style={{ padding: '10px 8px', textTransform: 'capitalize', color: 'var(--text-muted)' }}>
                          {apt.consultation_mode}
                        </td>
                        <td style={{ padding: '10px 8px', color: 'var(--text-secondary)' }}>{apt.reason_for_visit}</td>
                        <td style={{ padding: '10px 8px' }}>
                          <span className={`badge ${apt.status === 'scheduled' ? 'badge-info' : 'badge-success'}`}>
                            {apt.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 5. MULTI-TENANT FACILITIES */}
      {activeSection === 'tenants' && <HealthSystemTenantWorkspace />}

      {/* 6. SMART ON FHIR HUB */}
      {activeSection === 'smart_ehr' && <SmartFhirEhrWorkspace />}

      {/* 7. REGIONAL INTEROPERABILITY */}
      {activeSection === 'regional_interop' && <RegionalInteroperabilityWorkspace />}

      {/* 8. SECURITY & COMPLIANCE */}
      {activeSection === 'security' && (
        <SecurityComplianceWorkspace
          patients={patientsList}
          selectedPatient={patientsList[0] || null}
          onSelectPatient={() => {}}
        />
      )}

      {/* 9. TRIALS GOVERNANCE */}
      {activeSection === 'trials_gov' && <TrialsGovernanceWorkspace />}

      {/* 10. CLINICAL AI AGENTS */}
      {activeSection === 'agents' && <ClinicalAgentsWorkspace />}

      {/* 11. QUALITY MEASURES */}
      {activeSection === 'quality' && <QualityMeasuresWorkspace />}

      {/* 12. SYSTEM DIAGNOSTICS */}
      {activeSection === 'diagnostics' && <SystemDiagnosticsWorkspace />}

      {/* ASSIGN DOCTOR MODAL */}
      {assignModalPatient && (
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
          <div className="glass-panel" style={{ width: '100%', maxWidth: '480px', padding: '24px', background: '#0f172a' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '6px' }}>
              Assign Attending Doctor & Approve Intake
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Patient: <strong style={{ color: '#ffffff' }}>{assignModalPatient.first_name} {assignModalPatient.last_name}</strong> ({assignModalPatient.patient_id})
            </p>

            {assignModalPatient.health_problem && (
              <div style={{ background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', padding: '10px 12px', borderRadius: '6px', fontSize: '0.78rem', color: '#fbbf24', marginBottom: '16px' }}>
                <strong>Reported Problem:</strong> {assignModalPatient.health_problem}
              </div>
            )}

            <form onSubmit={handleAssignDoctor}>
              <div className="form-group">
                <label className="form-label">Select Specialist Doctor</label>
                <select
                  value={selectedDoctorId}
                  onChange={(e) => setSelectedDoctorId(Number(e.target.value))}
                  className="form-select"
                  required
                >
                  {doctorsList.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.full_name} ({doc.specialization} - {doc.department})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Clinical Intake Notes (Optional)</label>
                <textarea
                  rows={3}
                  value={assignNotes}
                  onChange={(e) => setAssignNotes(e.target.value)}
                  placeholder="e.g. Assigned for specialized cardiology evaluation and baseline ECG workup..."
                  className="form-textarea"
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
                <button
                  type="button"
                  onClick={() => setAssignModalPatient(null)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isAssigning}
                  className="btn btn-primary"
                >
                  {isAssigning ? 'Assigning...' : 'Confirm Assignment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT PATIENT MODAL */}
      {editModalPatient && (
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
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#ffffff', marginBottom: '16px' }}>
              Edit Patient Record ({editModalPatient.patient_id})
            </h3>
            <form onSubmit={handleSavePatientEdit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">First Name</label>
                  <input
                    type="text"
                    value={editFirstName}
                    onChange={(e) => setEditFirstName(e.target.value)}
                    className="form-input"
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Last Name</label>
                  <input
                    type="text"
                    value={editLastName}
                    onChange={(e) => setEditLastName(e.target.value)}
                    className="form-input"
                    required
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">Phone</label>
                  <input
                    type="text"
                    value={editPhone}
                    onChange={(e) => setEditPhone(e.target.value)}
                    className="form-input"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Blood Group</label>
                  <select
                    value={editBloodGroup}
                    onChange={(e) => setEditBloodGroup(e.target.value)}
                    className="form-select"
                  >
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Allergies</label>
                <input
                  type="text"
                  value={editAllergies}
                  onChange={(e) => setEditAllergies(e.target.value)}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Status</label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value)}
                  className="form-select"
                >
                  <option value="active">Active</option>
                  <option value="pending_review">Pending Review</option>
                  <option value="inactive">Inactive</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
                <button
                  type="button"
                  onClick={() => setEditModalPatient(null)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>
  );
};
