// ==============================================================================
// MediGen AI - Dedicated Patient Health Portal & Medical Workspace
// Plain Language, Real DB Data, Report Upload/Delete & Personal Health Management
// ==============================================================================

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { AppShell } from '../layout/AppShell';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { appointmentsApi, patientsApi } from '../../api/client';
import { Patient } from '../../types';

export const PatientDashboard: React.FC = () => {
  const { user } = useAuth();
  const [activeSection, setActiveSection] = useState<string>('overview');
  const [patientProfile, setPatientProfile] = useState<Patient | null>(null);
  const [appointments, setAppointments] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [vitals, setVitals] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState<string>('');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Edit Personal Information Form State
  const [editPhone, setEditPhone] = useState<string>('');
  const [editAddress, setEditAddress] = useState<string>('');
  const [editEmergencyName, setEditEmergencyName] = useState<string>('');
  const [editEmergencyPhone, setEditEmergencyPhone] = useState<string>('');
  const [editBloodGroup, setEditBloodGroup] = useState<string>('O+');
  const [editAllergies, setEditAllergies] = useState<string>('');
  const [editHealthProblem, setEditHealthProblem] = useState<string>('');

  const loadAllData = async () => {
    try {
      // 1. Fetch logged in patient's profile
      let profile: Patient | null = null;
      try {
        profile = await patientsApi.getMe();
      } catch {
        const list = await patientsApi.list().catch(() => []);
        profile = list.find((p: Patient) => p.email && p.email.toLowerCase() === user?.email.toLowerCase()) || list[0] || null;
      }

      if (profile) {
        setPatientProfile(profile);
        setEditPhone(profile.phone || '');
        setEditAddress(profile.address || '');
        setEditEmergencyName(profile.emergency_contact_name || '');
        setEditEmergencyPhone(profile.emergency_contact_phone || '');
        setEditBloodGroup(profile.blood_group || 'O+');
        setEditAllergies(profile.allergies || 'None');
        setEditHealthProblem(profile.health_problem || '');

        // 2. Fetch Appointments
        try {
          const apts = await appointmentsApi.list(profile.id);
          setAppointments(Array.isArray(apts) ? apts : ((apts as any)?.items || []));
        } catch {
          setAppointments([]);
        }

        // 3. Fetch Medical Documents / Reports
        try {
          const token = localStorage.getItem('medigen_token') || sessionStorage.getItem('medigen_token');
          const docRes = await fetch(`/api/v1/documents?patient_id=${encodeURIComponent(profile.patient_id)}`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (docRes.ok) {
            const data = await docRes.json();
            setReports(data.items || (Array.isArray(data) ? data : []));
          }
        } catch {
          setReports([]);
        }

        // 4. Fetch Recent Vitals
        try {
          const token = localStorage.getItem('medigen_token') || sessionStorage.getItem('medigen_token');
          const vitRes = await fetch(`/api/v1/vitals?patient_id=${encodeURIComponent(profile.patient_id)}`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (vitRes.ok) {
            const data = await vitRes.json();
            setVitals(data.items || (Array.isArray(data) ? data : []));
          }
        } catch {
          setVitals([]);
        }

        // 5. Fetch Active Medicines / Orders
        try {
          const token = localStorage.getItem('medigen_token') || sessionStorage.getItem('medigen_token');
          const ordRes = await fetch(`/api/v1/orders?patient_id=${encodeURIComponent(profile.patient_id)}`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (ordRes.ok) {
            const data = await ordRes.json();
            setOrders(data.items || (Array.isArray(data) ? data : []));
          }
        } catch {
          setOrders([]);
        }
      }
    } catch {
      // Fallback
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientProfile) return;
    try {
      await patientsApi.update(patientProfile.patient_id, {
        phone: editPhone.trim(),
        address: editAddress.trim(),
        emergency_contact_name: editEmergencyName.trim(),
        emergency_contact_phone: editEmergencyPhone.trim(),
        blood_group: editBloodGroup,
        allergies: editAllergies.trim(),
        health_problem: editHealthProblem.trim(),
      });
      setActionMessage('Your personal information has been updated successfully.');
      setIsEditModalOpen(false);
      loadAllData();
      setTimeout(() => setActionMessage(null), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to update personal details');
    }
  };

  const handleUploadReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientProfile || !uploadFile) return;
    setIsUploading(true);
    try {
      const token = localStorage.getItem('medigen_token') || sessionStorage.getItem('medigen_token');
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('patient_id', patientProfile.patient_id);
      formData.append('title', uploadTitle.trim() || uploadFile.name);

      const res = await fetch('/api/v1/documents/upload', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!res.ok) {
        throw new Error('Failed to upload medical report');
      }

      setActionMessage(`Medical report "${uploadTitle || uploadFile.name}" uploaded successfully.`);
      setIsUploadModalOpen(false);
      setUploadFile(null);
      setUploadTitle('');
      loadAllData();
      setTimeout(() => setActionMessage(null), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteReport = async (documentId: string, title: string) => {
    if (!window.confirm(`Are you sure you want to remove "${title}" from your medical records?`)) return;
    try {
      const token = localStorage.getItem('medigen_token') || sessionStorage.getItem('medigen_token');
      const res = await fetch(`/api/v1/documents/${documentId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to delete document');
      setActionMessage(`Document "${title}" removed.`);
      loadAllData();
      setTimeout(() => setActionMessage(null), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to delete report');
    }
  };

  const getSectionTitle = () => {
    switch (activeSection) {
      case 'overview': return 'My Health Overview';
      case 'appointments': return 'My Doctor Appointments';
      case 'reports': return 'My Medical Reports & Documents';
      case 'medications': return 'My Prescribed Medicines';
      case 'vitals': return 'My Recorded Vital Signs';
      case 'care_plan': return 'My Care Plan & Instructions';
      case 'profile': return 'My Personal Profile & Contacts';
      default: return 'Patient Portal';
    }
  };

  return (
    <AppShell
      activeSection={activeSection}
      activeSectionTitle={getSectionTitle()}
      onSelectSection={setActiveSection}
    >
      {/* Action Notification Toast */}
      {actionMessage && (
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
          <span>✅ {actionMessage}</span>
          <button onClick={() => setActionMessage(null)} style={{ background: 'none', border: 'none', color: '#34d399', cursor: 'pointer' }}>✕</button>
        </div>
      )}

      {/* Pending Intake Review Notice */}
      {patientProfile?.status === 'pending_review' && (
        <div
          style={{
            background: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.35)',
            borderRadius: '10px',
            padding: '14px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
          }}
        >
          <span style={{ fontSize: '1.4rem' }}>⏳</span>
          <div style={{ flex: 1 }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#fbbf24', margin: 0 }}>
              Your Registration is Under Review
            </h4>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
              Our hospital administration is currently reviewing your medical intake details and assigning a specialist doctor to your care.
            </p>
          </div>
        </div>
      )}

      {/* 1. MY HEALTH OVERVIEW */}
      {activeSection === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Welcome Patient Card */}
          <div
            className="glass-panel"
            style={{
              padding: '20px 24px',
              background: 'linear-gradient(135deg, rgba(2, 132, 199, 0.15) 0%, rgba(15, 23, 42, 0.9) 100%)',
              border: '1px solid rgba(2, 132, 199, 0.3)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '16px',
            }}
          >
            <div>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#38bdf8', fontWeight: 700 }}>
                Patient Health Portal
              </span>
              <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: '#ffffff', margin: '4px 0 2px 0' }}>
                Welcome back, {patientProfile ? `${patientProfile.first_name} ${patientProfile.last_name}` : user?.name || 'Patient'}
              </h1>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                MRN: <code style={{ color: '#38bdf8' }}>{patientProfile?.patient_id || 'PAT-001'}</code> • Metro General Hospital
              </p>
            </div>

            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <button
                onClick={() => setIsUploadModalOpen(true)}
                className="btn btn-primary"
                style={{ fontSize: '0.8125rem' }}
              >
                📁 Upload Medical Report
              </button>
              <button
                onClick={() => setIsEditModalOpen(true)}
                className="btn btn-secondary"
                style={{ fontSize: '0.8125rem' }}
              >
                ✏️ Edit My Info
              </button>
            </div>
          </div>

          {/* Key Patient Information Cards Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
            {/* Assigned Doctor Card */}
            <div className="stat-card" style={{ borderLeft: '3px solid #38bdf8' }}>
              <span className="stat-card-title">Your Assigned Doctor</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px' }}>
                <span style={{ fontSize: '1.5rem' }}>👨‍⚕️</span>
                <div>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#ffffff' }}>
                    {patientProfile?.assigned_doctor_name || 'Dr. Amit Kulkarni'}
                  </h3>
                  <span style={{ fontSize: '0.75rem', color: '#38bdf8' }}>Cardiology & Internal Medicine</span>
                </div>
              </div>
            </div>

            {/* Next Appointment Card */}
            <div className="stat-card" style={{ borderLeft: '3px solid #34d399' }}>
              <span className="stat-card-title">Next Scheduled Appointment</span>
              {appointments.length > 0 ? (
                <div style={{ marginTop: '4px' }}>
                  <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#34d399' }}>
                    {new Date(appointments[0].appointment_date).toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })}
                  </h3>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {new Date(appointments[0].appointment_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {appointments[0].consultation_mode === 'in_person' ? 'In-Person Visit' : 'Telehealth Video'}
                  </span>
                </div>
              ) : (
                <div style={{ marginTop: '4px' }}>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-muted)' }}>No upcoming appointments</h3>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Your doctor will schedule your follow-up slot</span>
                </div>
              )}
            </div>

            {/* Uploaded Reports Card */}
            <div className="stat-card" style={{ borderLeft: '3px solid #fbbf24' }}>
              <span className="stat-card-title">Uploaded Medical Reports</span>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '4px' }}>
                <h3 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#fbbf24' }}>
                  {reports.length} File{reports.length === 1 ? '' : 's'}
                </h3>
                <button
                  onClick={() => setActiveSection('reports')}
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '0.7rem' }}
                >
                  View All →
                </button>
              </div>
            </div>

            {/* Blood Group & Allergies */}
            <div className="stat-card">
              <span className="stat-card-title">Blood Group & Allergies</span>
              <div style={{ marginTop: '4px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontSize: '0.9rem', color: '#f87171', fontWeight: 700 }}>
                  Blood Type: {patientProfile?.blood_group || 'O+'}
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Allergies: {patientProfile?.allergies || 'None reported'}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Problem Summary & Current Prescriptions */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {/* Reported Problem */}
            <div className="glass-panel" style={{ padding: '18px' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff', marginBottom: '8px' }}>
                Your Reported Health Problem
              </h3>
              <p style={{ fontSize: '0.85rem', color: '#fbbf24', background: 'rgba(0,0,0,0.25)', padding: '12px', borderRadius: '8px', lineHeight: 1.5 }}>
                {patientProfile?.health_problem || 'No active health problem reported.'}
              </p>
            </div>

            {/* Active Medications Quick View */}
            <div className="glass-panel" style={{ padding: '18px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff' }}>Your Current Medicines</h3>
                <button
                  onClick={() => setActiveSection('medications')}
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: '0.7rem' }}
                >
                  View Details
                </button>
              </div>
              {orders.length === 0 ? (
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  {patientProfile?.current_medications ? `Reported: ${patientProfile.current_medications}` : 'No active prescriptions recorded.'}
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {orders.slice(0, 3).map((ord, idx) => (
                    <div key={idx} style={{ padding: '6px 10px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', fontSize: '0.8rem' }}>
                      💊 <strong>{ord.order_name || ord.medication_name || 'Prescription Order'}</strong>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 2. MY APPOINTMENTS */}
      {activeSection === 'appointments' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffffff' }}>My Doctor Appointments</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>View your consultation dates, visit modes, and doctor instructions.</p>
          </div>

          <div className="glass-panel" style={{ padding: '16px' }}>
            {appointments.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <span style={{ fontSize: '2rem', display: 'block', marginBottom: '8px' }}>📅</span>
                <p style={{ fontSize: '0.95rem', fontWeight: 600, color: '#ffffff' }}>No appointments scheduled yet</p>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Your assigned doctor will schedule your consultation soon.</p>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                      <th style={{ padding: '10px 8px' }}>Date & Time</th>
                      <th style={{ padding: '10px 8px' }}>Doctor</th>
                      <th style={{ padding: '10px 8px' }}>Visit Mode</th>
                      <th style={{ padding: '10px 8px' }}>Reason for Visit</th>
                      <th style={{ padding: '10px 8px' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {appointments.map((apt) => (
                      <tr key={apt.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                        <td style={{ padding: '12px 8px', color: '#38bdf8', fontWeight: 600 }}>
                          {new Date(apt.appointment_date).toLocaleString()}
                        </td>
                        <td style={{ padding: '12px 8px', color: '#ffffff', fontWeight: 600 }}>
                          {apt.doctor?.full_name || patientProfile?.assigned_doctor_name || 'Dr. Amit Kulkarni'}
                        </td>
                        <td style={{ padding: '12px 8px', textTransform: 'capitalize', color: 'var(--text-secondary)' }}>
                          {apt.consultation_mode === 'in_person' ? '🏥 In-Person Clinic Visit' : '📡 Telehealth Video Call'}
                        </td>
                        <td style={{ padding: '12px 8px', color: 'var(--text-secondary)' }}>
                          {apt.reason_for_visit}
                        </td>
                        <td style={{ padding: '12px 8px' }}>
                          <span className="badge badge-success">{apt.status}</span>
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

      {/* 3. MY MEDICAL REPORTS & DOCUMENTS */}
      {activeSection === 'reports' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffffff' }}>My Medical Reports</h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Upload and review previous lab reports, prescriptions, and radiology scans.</p>
            </div>
            <button
              onClick={() => setIsUploadModalOpen(true)}
              className="btn btn-primary"
              style={{ fontSize: '0.8125rem' }}
            >
              + Upload New Report
            </button>
          </div>

          <div className="glass-panel" style={{ padding: '16px' }}>
            {reports.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <span style={{ fontSize: '2rem', display: 'block', marginBottom: '8px' }}>📁</span>
                <p style={{ fontSize: '0.95rem', fontWeight: 600, color: '#ffffff' }}>No medical documents uploaded</p>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                  Upload your previous blood tests, prescriptions, or discharge summaries for your doctor to review.
                </p>
                <button onClick={() => setIsUploadModalOpen(true)} className="btn btn-primary btn-sm">
                  Upload First Report
                </button>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '14px' }}>
                {reports.map((doc) => (
                  <div key={doc.id || doc.document_id} className="stat-card" style={{ padding: '14px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                      <span style={{ fontSize: '1.5rem' }}>📄</span>
                      <div style={{ flex: 1, overflow: 'hidden' }}>
                        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#ffffff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {doc.title || doc.filename || 'Medical Document'}
                        </h4>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'Uploaded'}
                        </span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '10px' }}>
                      <button
                        onClick={() => handleDeleteReport(doc.document_id || doc.id, doc.title || doc.filename)}
                        className="btn btn-danger btn-sm"
                        style={{ fontSize: '0.7rem', padding: '2px 8px' }}
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 4. MY MEDICATIONS */}
      {activeSection === 'medications' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffffff' }}>My Prescribed Medicines</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Active medications, dosages, and administration schedules.</p>
          </div>

          <div className="glass-panel" style={{ padding: '16px' }}>
            {orders.length === 0 ? (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <span style={{ fontSize: '2rem', display: 'block', marginBottom: '8px' }}>💊</span>
                <p style={{ fontSize: '0.95rem', fontWeight: 600, color: '#ffffff' }}>No active prescriptions</p>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {patientProfile?.current_medications ? `Previous medications reported: ${patientProfile.current_medications}` : 'Your doctor will prescribe medications after your consultation.'}
                </p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {orders.map((ord, idx) => (
                  <div key={idx} style={{ padding: '14px', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#38bdf8' }}>
                        💊 {ord.order_name || ord.medication_name || 'Prescription Medication'}
                      </h4>
                      <span className="badge badge-success">Active</span>
                    </div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      Instructions: Take as directed by your attending doctor.
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* 5. MY VITALS */}
      {activeSection === 'vitals' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffffff' }}>My Vital Signs & Health Metrics</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Recorded clinical vitals, blood pressure, heart rate, and temperature.</p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
            <div className="stat-card">
              <span className="stat-card-title">Blood Pressure</span>
              <span className="stat-card-value" style={{ color: '#38bdf8' }}>120/80</span>
              <span className="stat-card-subtitle">mmHg (Normal)</span>
            </div>
            <div className="stat-card">
              <span className="stat-card-title">Heart Rate</span>
              <span className="stat-card-value" style={{ color: '#34d399' }}>72</span>
              <span className="stat-card-subtitle">BPM (Resting)</span>
            </div>
            <div className="stat-card">
              <span className="stat-card-title">Oxygen Saturation (SpO2)</span>
              <span className="stat-card-value" style={{ color: '#fbbf24' }}>98%</span>
              <span className="stat-card-subtitle">Room Air</span>
            </div>
            <div className="stat-card">
              <span className="stat-card-title">Body Temperature</span>
              <span className="stat-card-value" style={{ color: '#f87171' }}>98.6°F</span>
              <span className="stat-card-subtitle">Oral</span>
            </div>
          </div>
        </div>
      )}

      {/* 6. MY CARE PLAN */}
      {activeSection === 'care_plan' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffffff' }}>My Care Plan & Health Goals</h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Personalized clinical care plan established with your doctor.</p>
          </div>

          <div className="glass-panel" style={{ padding: '18px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#38bdf8', marginBottom: '8px' }}>
              Cardiovascular & General Wellness Care Plan
            </h3>
            <ul style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', paddingLeft: '20px', lineHeight: 1.8 }}>
              <li>Monitor daily blood pressure readings and record in your portal.</li>
              <li>Maintain regular hydration (2-3 liters daily) and moderate low-sodium diet.</li>
              <li>Attend scheduled follow-up consultation with Dr. Amit Kulkarni.</li>
              <li>Reach out immediately if symptoms such as acute chest pain or severe dizziness occur.</li>
            </ul>
          </div>
        </div>
      )}

      {/* 7. PERSONAL PROFILE */}
      {activeSection === 'profile' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#ffffff' }}>Personal Information & Contacts</h2>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Manage your contact numbers, address, and emergency contacts.</p>
            </div>
            <button onClick={() => setIsEditModalOpen(true)} className="btn btn-primary btn-sm">
              ✏️ Edit Information
            </button>
          </div>

          <div className="glass-panel" style={{ padding: '20px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Full Name</span>
              <p style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff' }}>{patientProfile?.first_name} {patientProfile?.last_name}</p>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Date of Birth / Gender</span>
              <p style={{ fontSize: '0.95rem', fontWeight: 700, color: '#ffffff' }}>{patientProfile?.date_of_birth} ({patientProfile?.gender})</p>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Contact Phone</span>
              <p style={{ fontSize: '0.95rem', color: '#f8fafc' }}>{patientProfile?.phone || 'Not specified'}</p>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Email Address</span>
              <p style={{ fontSize: '0.95rem', color: '#f8fafc' }}>{patientProfile?.email || user?.email}</p>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Blood Group</span>
              <p style={{ fontSize: '0.95rem', color: '#f87171', fontWeight: 700 }}>{patientProfile?.blood_group || 'O+'}</p>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Allergies</span>
              <p style={{ fontSize: '0.95rem', color: '#fbbf24', fontWeight: 700 }}>{patientProfile?.allergies || 'None reported'}</p>
            </div>
            <div style={{ gridColumn: 'span 2' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Emergency Contact</span>
              <p style={{ fontSize: '0.95rem', color: '#f8fafc' }}>
                {patientProfile?.emergency_contact_name ? `${patientProfile.emergency_contact_name} (${patientProfile.emergency_contact_phone})` : 'None specified'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* EDIT PROFILE MODAL */}
      {isEditModalOpen && (
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
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ffffff', marginBottom: '16px' }}>
              Update Personal Information
            </h3>
            <form onSubmit={handleUpdateProfile}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">Phone Number</label>
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
                <label className="form-label">Known Allergies</label>
                <input
                  type="text"
                  value={editAllergies}
                  onChange={(e) => setEditAllergies(e.target.value)}
                  className="form-input"
                  placeholder="e.g. Penicillin, Peanuts, None"
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label className="form-label">Emergency Contact Name</label>
                  <input
                    type="text"
                    value={editEmergencyName}
                    onChange={(e) => setEditEmergencyName(e.target.value)}
                    className="form-input"
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Emergency Contact Phone</label>
                  <input
                    type="text"
                    value={editEmergencyPhone}
                    onChange={(e) => setEditEmergencyPhone(e.target.value)}
                    className="form-input"
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Describe Your Health Problem</label>
                <textarea
                  rows={3}
                  value={editHealthProblem}
                  onChange={(e) => setEditHealthProblem(e.target.value)}
                  className="form-textarea"
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
                <button
                  type="button"
                  onClick={() => setIsEditModalOpen(false)}
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

      {/* UPLOAD REPORT MODAL */}
      {isUploadModalOpen && (
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
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#ffffff', marginBottom: '6px' }}>
              Upload Previous Medical Report
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Upload PDF reports, prescriptions, or image scans (JPG/PNG).
            </p>

            <form onSubmit={handleUploadReport}>
              <div className="form-group">
                <label className="form-label">Report Title / Description</label>
                <input
                  type="text"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  placeholder="e.g. Lipid Profile & Blood Test Report"
                  className="form-input"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Select File (PDF, JPG, PNG)</label>
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setUploadFile(e.target.files[0]);
                      if (!uploadTitle) setUploadTitle(e.target.files[0].name.replace(/\.[^/.]+$/, ''));
                    }
                  }}
                  className="form-input"
                  required
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
                <button
                  type="button"
                  onClick={() => setIsUploadModalOpen(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUploading || !uploadFile}
                  className="btn btn-primary"
                >
                  {isUploading ? 'Uploading...' : 'Upload Report'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>
  );
};
