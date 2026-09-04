// ==============================================================================
// MediGen AI - Dedicated System Administrator Control Center & Patient Intake
// Hospital Operations, Patient Intake, Doctor Assignments, Facilities & Governance
// ==============================================================================

import React, { useState, useEffect, useMemo } from 'react';
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

  // Doctor Staff Management State
  const [doctorSearchQuery, setDoctorSearchQuery] = useState<string>('');
  const [doctorDeptFilter, setDoctorDeptFilter] = useState<string>('');
  const [doctorSpecFilter, setDoctorSpecFilter] = useState<string>('');
  const [doctorStatusFilter, setDoctorStatusFilter] = useState<string>('all');

  const [addDoctorModalOpen, setAddDoctorModalOpen] = useState<boolean>(false);
  const [isSubmittingDoctor, setIsSubmittingDoctor] = useState<boolean>(false);
  const [addDocFullName, setAddDocFullName] = useState<string>('');
  const [addDocEmail, setAddDocEmail] = useState<string>('');
  const [addDocPhone, setAddDocPhone] = useState<string>('');
  const [addDocSpecialization, setAddDocSpecialization] = useState<string>('');
  const [addDocDepartment, setAddDocDepartment] = useState<string>('General Medicine');
  const [addDocLicense, setAddDocLicense] = useState<string>('');
  const [addDocExperience, setAddDocExperience] = useState<number>(5);
  const [addDocQualifications, setAddDocQualifications] = useState<string>('MBBS, MD');
  const [addDocConsultationMode, setAddDocConsultationMode] = useState<string>('both');
  const [createdDocCredentials, setCreatedDocCredentials] = useState<{ email: string; password?: string } | null>(null);

  const [viewDoctorModal, setViewDoctorModal] = useState<Doctor | null>(null);

  const [editDoctorModal, setEditDoctorModal] = useState<Doctor | null>(null);
  const [editDocFullName, setEditDocFullName] = useState<string>('');
  const [editDocPhone, setEditDocPhone] = useState<string>('');
  const [editDocSpecialization, setEditDocSpecialization] = useState<string>('');
  const [editDocDepartment, setEditDocDepartment] = useState<string>('');
  const [editDocLicense, setEditDocLicense] = useState<string>('');
  const [editDocExperience, setEditDocExperience] = useState<number>(0);
  const [editDocQualifications, setEditDocQualifications] = useState<string>('');
  const [editDocConsultationMode, setEditDocConsultationMode] = useState<string>('both');

  const [deactivateConfirmDoctor, setDeactivateConfirmDoctor] = useState<Doctor | null>(null);
  const [reactivateConfirmDoctor, setReactivateConfirmDoctor] = useState<Doctor | null>(null);
  const [deleteConfirmDoctor, setDeleteConfirmDoctor] = useState<Doctor | null>(null);

  const availableDepartments = useMemo(() => {
    return Array.from(new Set(doctorsList.map((d) => d.department).filter(Boolean))).sort();
  }, [doctorsList]);

  const availableSpecializations = useMemo(() => {
    return Array.from(new Set(doctorsList.map((d) => d.specialization).filter(Boolean))).sort();
  }, [doctorsList]);

  const filteredDoctors = useMemo(() => {
    return doctorsList.filter((doc) => {
      const q = doctorSearchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        doc.full_name?.toLowerCase().includes(q) ||
        doc.specialization?.toLowerCase().includes(q) ||
        doc.department?.toLowerCase().includes(q) ||
        doc.email?.toLowerCase().includes(q) ||
        doc.medical_registration_number?.toLowerCase().includes(q);

      const matchesDept = !doctorDeptFilter || doc.department === doctorDeptFilter;
      const matchesSpec = !doctorSpecFilter || doc.specialization === doctorSpecFilter;
      const matchesStatus =
        doctorStatusFilter === 'all' ||
        (doctorStatusFilter === 'active' && doc.verification_status !== 'inactive') ||
        (doctorStatusFilter === 'inactive' && doc.verification_status === 'inactive') ||
        doc.verification_status === doctorStatusFilter;

      return matchesSearch && matchesDept && matchesSpec && matchesStatus;
    });
  }, [doctorsList, doctorSearchQuery, doctorDeptFilter, doctorSpecFilter, doctorStatusFilter]);

  const handleOpenAddDoctor = () => {
    setAddDocFullName('');
    setAddDocEmail('');
    setAddDocPhone('');
    setAddDocSpecialization('');
    setAddDocDepartment('General Medicine');
    setAddDocLicense('');
    setAddDocExperience(5);
    setAddDocQualifications('MBBS, MD');
    setAddDocConsultationMode('both');
    setCreatedDocCredentials(null);
    setAddDoctorModalOpen(true);
  };

  const handleAddDoctorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmittingDoctor(true);
    try {
      const res = await doctorsApi.adminCreate({
        full_name: addDocFullName.trim(),
        email: addDocEmail.trim(),
        phone: addDocPhone.trim() || undefined,
        specialization: addDocSpecialization.trim(),
        department: addDocDepartment.trim(),
        medical_registration_number: addDocLicense.trim(),
        years_of_experience: Number(addDocExperience) || 0,
        qualifications: addDocQualifications.trim() || undefined,
        consultation_mode: addDocConsultationMode,
      });
      setCreatedDocCredentials({
        email: addDocEmail.trim(),
        password: res.temporary_password,
      });
      setActionAlert("Doctor account created successfully.");
      setTimeout(() => setActionAlert(null), 6000);
      loadAllAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to create doctor account');
    } finally {
      setIsSubmittingDoctor(false);
    }
  };

  const handleOpenEditDoctor = (doc: Doctor) => {
    setEditDoctorModal(doc);
    setEditDocFullName(doc.full_name || '');
    setEditDocPhone(doc.phone || '');
    setEditDocSpecialization(doc.specialization || '');
    setEditDocDepartment(doc.department || '');
    setEditDocLicense(doc.medical_registration_number || '');
    setEditDocExperience(doc.years_of_experience || 0);
    setEditDocQualifications(doc.qualifications || '');
    setEditDocConsultationMode(doc.consultation_mode || 'both');
  };

  const handleEditDoctorSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editDoctorModal) return;
    setIsSubmittingDoctor(true);
    try {
      await doctorsApi.update(editDoctorModal.doctor_id || editDoctorModal.id, {
        full_name: editDocFullName.trim(),
        phone: editDocPhone.trim() || undefined,
        specialization: editDocSpecialization.trim(),
        department: editDocDepartment.trim(),
        medical_registration_number: editDocLicense.trim(),
        years_of_experience: Number(editDocExperience) || 0,
        qualifications: editDocQualifications.trim() || undefined,
        consultation_mode: editDocConsultationMode,
      });
      setActionAlert(`Doctor profile for ${editDocFullName} updated successfully.`);
      setTimeout(() => setActionAlert(null), 4000);
      setEditDoctorModal(null);
      loadAllAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to update doctor profile');
    } finally {
      setIsSubmittingDoctor(false);
    }
  };

  const handleDeactivateDoctorConfirm = async () => {
    if (!deactivateConfirmDoctor) return;
    try {
      await doctorsApi.deactivate(deactivateConfirmDoctor.doctor_id || deactivateConfirmDoctor.id);
      setActionAlert(`Doctor ${deactivateConfirmDoctor.full_name} has been deactivated. Historical clinical records remain preserved.`);
      setTimeout(() => setActionAlert(null), 5000);
      setDeactivateConfirmDoctor(null);
      loadAllAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to deactivate doctor');
    }
  };

  const handleReactivateDoctorConfirm = async () => {
    if (!reactivateConfirmDoctor) return;
    try {
      await doctorsApi.activate(reactivateConfirmDoctor.doctor_id || reactivateConfirmDoctor.id);
      setActionAlert(`Doctor ${reactivateConfirmDoctor.full_name} has been reactivated.`);
      setTimeout(() => setActionAlert(null), 4000);
      setReactivateConfirmDoctor(null);
      loadAllAdminData();
    } catch (err: any) {
      alert(err.message || 'Failed to reactivate doctor');
    }
  };

  const handleDeleteDoctorConfirm = async () => {
    if (!deleteConfirmDoctor) return;
    try {
      await doctorsApi.deleteDoctor(deleteConfirmDoctor.doctor_id || deleteConfirmDoctor.id, true);
      setActionAlert(`Doctor profile for ${deleteConfirmDoctor.full_name} deleted.`);
      setTimeout(() => setActionAlert(null), 4000);
      setDeleteConfirmDoctor(null);
      loadAllAdminData();
    } catch (err: any) {
      alert(err.message || 'Doctor has clinical history and cannot be deleted. Deactivation has been applied instead.');
    }
  };


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

            <div className="stat-card" style={{ borderLeft: '3px solid #8b5cf6' }}>
              <span className="stat-card-title">Active Clinical Units</span>
              <span className="stat-card-value" style={{ color: '#a78bfa' }}>
                {Array.from(new Set(doctorsList.map((d) => d.department).filter(Boolean))).length || 1}
              </span>
              <span className="stat-card-subtitle">Specialized Inpatient & Outpatient Units</span>
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
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>No patients found.</div>
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
          {/* Section Header with Add Doctor Action */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>
                Doctors & Clinical Staff
              </h2>
              <p style={{ fontSize: '0.8125rem', color: 'var(--text-secondary)', margin: '4px 0 0' }}>
                Manage specialist physicians, credentials, department assignments, and clinical accounts.
              </p>
            </div>
            <button
              onClick={handleOpenAddDoctor}
              className="btn btn-primary"
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '9px 18px', fontWeight: 600 }}
              data-testid="admin-add-doctor-btn"
            >
              <span>➕</span>
              <span>Add Doctor</span>
            </button>
          </div>

          {/* Search & Filter Ribbon */}
          <div
            className="glass-panel"
            style={{
              padding: '14px 18px',
              display: 'flex',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            {/* Search Doctor */}
            <div style={{ flex: '1 1 240px', minWidth: '220px' }}>
              <input
                type="text"
                placeholder="Search doctor by name, email, license, specialization..."
                value={doctorSearchQuery}
                onChange={(e) => setDoctorSearchQuery(e.target.value)}
                className="form-input"
                style={{ width: '100%', fontSize: '0.85rem' }}
                data-testid="admin-doctor-search-input"
              />
            </div>

            {/* Department Filter */}
            <div style={{ flex: '0 1 180px' }}>
              <select
                value={doctorDeptFilter}
                onChange={(e) => setDoctorDeptFilter(e.target.value)}
                className="form-select"
                style={{ width: '100%', fontSize: '0.85rem' }}
                data-testid="admin-doctor-dept-filter"
              >
                <option value="">All Departments</option>
                {availableDepartments.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>
            </div>

            {/* Specialization Filter */}
            <div style={{ flex: '0 1 180px' }}>
              <select
                value={doctorSpecFilter}
                onChange={(e) => setDoctorSpecFilter(e.target.value)}
                className="form-select"
                style={{ width: '100%', fontSize: '0.85rem' }}
                data-testid="admin-doctor-spec-filter"
              >
                <option value="">All Specializations</option>
                {availableSpecializations.map((spec) => (
                  <option key={spec} value={spec}>
                    {spec}
                  </option>
                ))}
              </select>
            </div>

            {/* Status Filter */}
            <div style={{ flex: '0 1 140px' }}>
              <select
                value={doctorStatusFilter}
                onChange={(e) => setDoctorStatusFilter(e.target.value)}
                className="form-select"
                style={{ width: '100%', fontSize: '0.85rem' }}
                data-testid="admin-doctor-status-filter"
              >
                <option value="all">All Statuses</option>
                <option value="active">Active Only</option>
                <option value="inactive">Inactive Only</option>
              </select>
            </div>

            {/* Reset Filters */}
            {(doctorSearchQuery || doctorDeptFilter || doctorSpecFilter || doctorStatusFilter !== 'all') && (
              <button
                onClick={() => {
                  setDoctorSearchQuery('');
                  setDoctorDeptFilter('');
                  setDoctorSpecFilter('');
                  setDoctorStatusFilter('all');
                }}
                className="btn btn-secondary btn-sm"
                style={{ fontSize: '0.75rem' }}
              >
                Reset
              </button>
            )}
          </div>

          {/* Doctors Table & Roster */}
          <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
            <div
              style={{
                padding: '12px 18px',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                Showing {filteredDoctors.length} of {doctorsList.length} registered clinicians
              </span>
            </div>

            {filteredDoctors.length === 0 ? (
              <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <span style={{ fontSize: '2rem', display: 'block', marginBottom: '8px' }}>🩺</span>
                <p style={{ margin: 0, fontSize: '0.9rem' }}>No doctors found matching the current search and filter criteria.</p>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.75rem' }}>Doctor</th>
                      <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.75rem' }}>Department & Specialization</th>
                      <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.75rem' }}>License Number</th>
                      <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.75rem' }}>Experience</th>
                      <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.75rem' }}>Contact</th>
                      <th style={{ padding: '12px 16px', textAlign: 'center', fontSize: '0.75rem' }}>Status</th>
                      <th style={{ padding: '12px 16px', textAlign: 'right', fontSize: '0.75rem' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDoctors.map((doc) => {
                      const isInactive = doc.verification_status === 'inactive';
                      return (
                        <tr
                          key={doc.id || doc.doctor_id}
                          style={{
                            borderBottom: '1px solid var(--border-color)',
                            opacity: isInactive ? 0.65 : 1,
                          }}
                        >
                          {/* Doctor Name & Avatar */}
                          <td style={{ padding: '12px 16px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <div
                                style={{
                                  width: '36px',
                                  height: '36px',
                                  borderRadius: '50%',
                                  background: isInactive ? 'rgba(148, 163, 184, 0.15)' : 'rgba(2, 132, 199, 0.2)',
                                  color: isInactive ? '#94a3b8' : '#38bdf8',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  fontSize: '1rem',
                                  fontWeight: 700,
                                  flexShrink: 0,
                                }}
                              >
                                🩺
                              </div>
                              <div>
                                <div style={{ fontWeight: 600, color: '#ffffff', fontSize: '0.875rem' }}>
                                  {doc.full_name}
                                </div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                  ID: {doc.doctor_id || `DOC-${doc.id}`}
                                </div>
                              </div>
                            </div>
                          </td>

                          {/* Department & Specialization */}
                          <td style={{ padding: '12px 16px' }}>
                            <div style={{ fontWeight: 600, color: '#38bdf8', fontSize: '0.8125rem' }}>
                              {doc.specialization}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              {doc.department}
                            </div>
                          </td>

                          {/* License */}
                          <td style={{ padding: '12px 16px' }}>
                            <code style={{ fontSize: '0.8rem', color: '#f8fafc', background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: '4px' }}>
                              {doc.medical_registration_number || 'N/A'}
                            </code>
                          </td>

                          {/* Experience */}
                          <td style={{ padding: '12px 16px', fontSize: '0.8125rem', color: '#e2e8f0' }}>
                            {doc.years_of_experience} yrs
                          </td>

                          {/* Contact */}
                          <td style={{ padding: '12px 16px' }}>
                            <div style={{ fontSize: '0.8rem', color: '#f8fafc' }}>{doc.email}</div>
                            {doc.phone && <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{doc.phone}</div>}
                          </td>

                          {/* Status */}
                          <td style={{ padding: '12px 16px', textAlign: 'center' }}>
                            {isInactive ? (
                              <span className="badge badge-danger" style={{ fontSize: '0.7rem' }}>
                                Inactive
                              </span>
                            ) : (
                              <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
                                Verified
                              </span>
                            )}
                          </td>

                          {/* Actions */}
                          <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }}>
                              <button
                                onClick={() => setViewDoctorModal(doc)}
                                className="btn btn-secondary btn-sm"
                                style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                                title="View Doctor Details"
                                data-testid={`view-doctor-btn-${doc.id || doc.doctor_id}`}
                              >
                                👁️ View
                              </button>

                              <button
                                onClick={() => handleOpenEditDoctor(doc)}
                                className="btn btn-secondary btn-sm"
                                style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                                title="Edit Doctor Profile"
                                data-testid={`edit-doctor-btn-${doc.id || doc.doctor_id}`}
                              >
                                ✏️ Edit
                              </button>

                              {isInactive ? (
                                <button
                                  onClick={() => setReactivateConfirmDoctor(doc)}
                                  className="btn btn-secondary btn-sm"
                                  style={{ padding: '4px 8px', fontSize: '0.75rem', color: '#34d399', borderColor: 'rgba(16, 185, 129, 0.4)' }}
                                  title="Reactivate Doctor"
                                  data-testid={`reactivate-doctor-btn-${doc.id || doc.doctor_id}`}
                                >
                                  ▶️ Activate
                                </button>
                              ) : (
                                <button
                                  onClick={() => setDeactivateConfirmDoctor(doc)}
                                  className="btn btn-secondary btn-sm"
                                  style={{ padding: '4px 8px', fontSize: '0.75rem', color: '#fbbf24', borderColor: 'rgba(245, 158, 11, 0.4)' }}
                                  title="Deactivate Doctor (Preserve Medical Records)"
                                  data-testid={`deactivate-doctor-btn-${doc.id || doc.doctor_id}`}
                                >
                                  ⏸️ Deactivate
                                </button>
                              )}

                              <button
                                onClick={() => setDeleteConfirmDoctor(doc)}
                                className="btn btn-danger btn-sm"
                                style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                                title="Remove Doctor Record"
                                data-testid={`delete-doctor-btn-${doc.id || doc.doctor_id}`}
                              >
                                🗑️ Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
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
              <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>No appointments scheduled.</div>
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
                  {doctorsList
                    .filter((d) => d.verification_status !== 'inactive')
                    .map((doc) => (
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

      {/* 5. ADD DOCTOR MODAL */}
      {addDoctorModalOpen && (
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
          data-testid="add-doctor-modal-overlay"
        >
          <div
            className="glass-panel"
            style={{
              width: '100%',
              maxWidth: '620px',
              padding: '24px',
              maxHeight: '90vh',
              overflowY: 'auto',
              background: '#0d1527',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.15)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1.4rem' }}>🩺</span>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>
                  Add Doctor & Clinical Specialist
                </h3>
              </div>
              <button
                onClick={() => setAddDoctorModalOpen(false)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            {createdDocCredentials ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '12px 0' }}>
                <div style={{ padding: '16px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid #10b981', borderRadius: '10px' }}>
                  <h4 style={{ margin: '0 0 6px', color: '#6ee7b7', fontSize: '0.95rem', fontWeight: 700 }}>
                    Doctor Account Provisioned Successfully
                  </h4>
                  <p style={{ margin: '0 0 12px', fontSize: '0.8rem', color: '#d1fae5' }}>
                    Share these temporary login credentials with the physician securely. The doctor will be prompted to manage credentials upon login.
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', background: '#090d16', padding: '12px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                    <div style={{ fontSize: '0.85rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Email: </span>
                      <strong style={{ color: '#ffffff' }}>{createdDocCredentials.email}</strong>
                    </div>
                    <div style={{ fontSize: '0.85rem' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Temporary Password: </span>
                      <code style={{ color: '#38bdf8', fontWeight: 700, fontSize: '0.9rem' }}>{createdDocCredentials.password}</code>
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(`MediGen AI Doctor Login\nEmail: ${createdDocCredentials.email}\nPassword: ${createdDocCredentials.password}`);
                      alert("Credentials copied to clipboard!");
                    }}
                    className="btn btn-secondary"
                  >
                    📋 Copy Credentials
                  </button>
                  <button
                    onClick={() => {
                      setCreatedDocCredentials(null);
                      setAddDoctorModalOpen(false);
                    }}
                    className="btn btn-primary"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleAddDoctorSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label">Full Name *</label>
                    <input
                      type="text"
                      required
                      placeholder="Dr. Jane Doe"
                      value={addDocFullName}
                      onChange={(e) => setAddDocFullName(e.target.value)}
                      className="form-input"
                      data-testid="input-doc-fullname"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Email Address *</label>
                    <input
                      type="email"
                      required
                      placeholder="dr.jane@hospital.org"
                      value={addDocEmail}
                      onChange={(e) => setAddDocEmail(e.target.value)}
                      className="form-input"
                      data-testid="input-doc-email"
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label">Phone / Mobile</label>
                    <input
                      type="tel"
                      placeholder="+1-555-0199"
                      value={addDocPhone}
                      onChange={(e) => setAddDocPhone(e.target.value)}
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Medical Registration / License *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. MED-849201"
                      value={addDocLicense}
                      onChange={(e) => setAddDocLicense(e.target.value)}
                      className="form-input"
                      data-testid="input-doc-license"
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label">Department *</label>
                    <select
                      value={addDocDepartment}
                      onChange={(e) => setAddDocDepartment(e.target.value)}
                      className="form-select"
                      required
                    >
                      <option value="General Medicine">General Medicine</option>
                      <option value="Cardiology">Cardiology</option>
                      <option value="Neurology">Neurology</option>
                      <option value="Pulmonology">Pulmonology</option>
                      <option value="Pediatrics">Pediatrics</option>
                      <option value="Endocrinology">Endocrinology</option>
                      <option value="Oncology">Oncology</option>
                      <option value="Orthopedics">Orthopedics</option>
                      <option value="Emergency Medicine">Emergency Medicine</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Specialization *</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. Interventional Cardiology"
                      value={addDocSpecialization}
                      onChange={(e) => setAddDocSpecialization(e.target.value)}
                      className="form-input"
                      data-testid="input-doc-specialization"
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label">Years of Experience *</label>
                    <input
                      type="number"
                      required
                      min={0}
                      max={60}
                      value={addDocExperience}
                      onChange={(e) => setAddDocExperience(Number(e.target.value))}
                      className="form-input"
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Consultation Mode</label>
                    <select
                      value={addDocConsultationMode}
                      onChange={(e) => setAddDocConsultationMode(e.target.value)}
                      className="form-select"
                    >
                      <option value="both">Both (In-Person & Telehealth)</option>
                      <option value="in_person">In-Person Only</option>
                      <option value="telehealth">Telehealth Only</option>
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Degrees & Qualifications</label>
                  <input
                    type="text"
                    placeholder="e.g. MBBS, MD, FACC"
                    value={addDocQualifications}
                    onChange={(e) => setAddDocQualifications(e.target.value)}
                    className="form-input"
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '14px' }}>
                  <button
                    type="button"
                    onClick={() => setAddDoctorModalOpen(false)}
                    className="btn btn-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmittingDoctor}
                    className="btn btn-primary"
                    data-testid="submit-add-doctor-btn"
                  >
                    {isSubmittingDoctor ? 'Creating Account...' : 'Add Doctor'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* 6. EDIT DOCTOR MODAL */}
      {editDoctorModal && (
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
          data-testid="edit-doctor-modal-overlay"
        >
          <div
            className="glass-panel"
            style={{
              width: '100%',
              maxWidth: '600px',
              padding: '24px',
              maxHeight: '90vh',
              overflowY: 'auto',
              background: '#0d1527',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.15)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>
                Edit Doctor Profile
              </h3>
              <button
                onClick={() => setEditDoctorModal(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleEditDoctorSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">Full Name</label>
                  <input
                    type="text"
                    required
                    value={editDocFullName}
                    onChange={(e) => setEditDocFullName(e.target.value)}
                    className="form-input"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Phone</label>
                  <input
                    type="tel"
                    value={editDocPhone}
                    onChange={(e) => setEditDocPhone(e.target.value)}
                    className="form-input"
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">Department</label>
                  <input
                    type="text"
                    required
                    value={editDocDepartment}
                    onChange={(e) => setEditDocDepartment(e.target.value)}
                    className="form-input"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Specialization</label>
                  <input
                    type="text"
                    required
                    value={editDocSpecialization}
                    onChange={(e) => setEditDocSpecialization(e.target.value)}
                    className="form-input"
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">License / Registration</label>
                  <input
                    type="text"
                    required
                    value={editDocLicense}
                    onChange={(e) => setEditDocLicense(e.target.value)}
                    className="form-input"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Experience (Years)</label>
                  <input
                    type="number"
                    min={0}
                    value={editDocExperience}
                    onChange={(e) => setEditDocExperience(Number(e.target.value))}
                    className="form-input"
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Qualifications</label>
                <input
                  type="text"
                  value={editDocQualifications}
                  onChange={(e) => setEditDocQualifications(e.target.value)}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Consultation Mode</label>
                <select
                  value={editDocConsultationMode}
                  onChange={(e) => setEditDocConsultationMode(e.target.value)}
                  className="form-select"
                >
                  <option value="both">Both (In-Person & Telehealth)</option>
                  <option value="in_person">In-Person Only</option>
                  <option value="telehealth">Telehealth Only</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '14px' }}>
                <button
                  type="button"
                  onClick={() => setEditDoctorModal(null)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingDoctor}
                  className="btn btn-primary"
                >
                  {isSubmittingDoctor ? 'Saving...' : 'Save Profile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 7. VIEW DOCTOR MODAL */}
      {viewDoctorModal && (
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
          data-testid="view-doctor-modal-overlay"
        >
          <div
            className="glass-panel"
            style={{
              width: '100%',
              maxWidth: '540px',
              padding: '24px',
              background: '#0d1527',
              borderRadius: '16px',
              border: '1px solid rgba(255, 255, 255, 0.15)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '1.4rem' }}>🩺</span>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ffffff', margin: 0 }}>
                  {viewDoctorModal.full_name}
                </h3>
              </div>
              <button
                onClick={() => setViewDoctorModal(null)}
                style={{ background: 'none', border: 'none', color: 'var(--text-muted)', fontSize: '1.2rem', cursor: 'pointer' }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '0.85rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Specialization:</span>
                <span style={{ color: '#38bdf8', fontWeight: 600 }}>{viewDoctorModal.specialization}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Department:</span>
                <span style={{ color: '#f8fafc' }}>{viewDoctorModal.department}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Medical Registration:</span>
                <code style={{ color: '#34d399' }}>{viewDoctorModal.medical_registration_number}</code>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Experience:</span>
                <span style={{ color: '#f8fafc' }}>{viewDoctorModal.years_of_experience} Years</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Email:</span>
                <span style={{ color: '#f8fafc' }}>{viewDoctorModal.email}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Qualifications:</span>
                <span style={{ color: '#f8fafc' }}>{viewDoctorModal.qualifications || 'MBBS, MD'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Consultation Mode:</span>
                <span style={{ color: '#f8fafc', textTransform: 'capitalize' }}>
                  {viewDoctorModal.consultation_mode?.replace('_', ' ') || 'In-Person & Telehealth'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}>
                <span style={{ color: 'var(--text-muted)' }}>Account Status:</span>
                <span className={viewDoctorModal.verification_status === 'inactive' ? 'badge badge-danger' : 'badge badge-success'}>
                  {viewDoctorModal.verification_status === 'inactive' ? 'Inactive' : 'Verified / Active'}
                </span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '18px' }}>
              <button
                onClick={() => setViewDoctorModal(null)}
                className="btn btn-primary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 8. DEACTIVATE CONFIRMATION MODAL */}
      {deactivateConfirmDoctor && (
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
          data-testid="deactivate-confirm-modal"
        >
          <div
            className="glass-panel"
            style={{
              width: '100%',
              maxWidth: '480px',
              padding: '24px',
              background: '#0d1527',
              borderRadius: '16px',
              border: '1px solid rgba(245, 158, 11, 0.4)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <span style={{ fontSize: '1.5rem' }}>⏸️</span>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fbbf24', margin: 0 }}>
                Deactivate Doctor
              </h3>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '18px' }}>
              Are you sure you want to deactivate <strong>{deactivateConfirmDoctor.full_name}</strong>?
              <br /><br />
              • The doctor will be prevented from logging into the portal.<br />
              • The doctor will no longer appear for new patient assignments.<br />
              • <strong>All clinical consultation history, notes, and prescriptions remain preserved.</strong>
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => setDeactivateConfirmDoctor(null)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleDeactivateDoctorConfirm}
                className="btn btn-danger"
                style={{ background: '#d97706', borderColor: '#d97706' }}
              >
                Confirm Deactivation
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 9. REACTIVATE CONFIRMATION MODAL */}
      {reactivateConfirmDoctor && (
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
          data-testid="reactivate-confirm-modal"
        >
          <div
            className="glass-panel"
            style={{
              width: '100%',
              maxWidth: '480px',
              padding: '24px',
              background: '#0d1527',
              borderRadius: '16px',
              border: '1px solid rgba(16, 185, 129, 0.4)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <span style={{ fontSize: '1.5rem' }}>▶️</span>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#34d399', margin: 0 }}>
                Reactivate Doctor
              </h3>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '18px' }}>
              Reactivate <strong>{reactivateConfirmDoctor.full_name}</strong> to restore login privileges and allow new patient consultations.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => setReactivateConfirmDoctor(null)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleReactivateDoctorConfirm}
                className="btn btn-primary"
              >
                Reactivate Doctor
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 10. SAFE DELETE CONFIRMATION MODAL */}
      {deleteConfirmDoctor && (
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
          data-testid="delete-confirm-modal"
        >
          <div
            className="glass-panel"
            style={{
              width: '100%',
              maxWidth: '480px',
              padding: '24px',
              background: '#0d1527',
              borderRadius: '16px',
              border: '1px solid rgba(239, 68, 68, 0.4)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
              <span style={{ fontSize: '1.5rem' }}>⚠️</span>
              <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#f87171', margin: 0 }}>
                Delete Doctor Record
              </h3>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '18px' }}>
              Attempt permanent deletion of <strong>{deleteConfirmDoctor.full_name}</strong>.
              <br /><br />
              <strong style={{ color: '#fca5a5' }}>Notice:</strong> If this doctor has any existing appointments or clinical encounters, permanent deletion will be blocked by medical audit compliance rules. Consider deactivation instead.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button
                onClick={() => setDeleteConfirmDoctor(null)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteDoctorConfirm}
                className="btn btn-danger"
              >
                Delete Record
              </button>
            </div>
          </div>
        </div>
      )}
    </AppShell>
  );
};
