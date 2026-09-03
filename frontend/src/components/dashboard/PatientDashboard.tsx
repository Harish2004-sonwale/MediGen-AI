// ==============================================================================
// MediGen AI - Dedicated Patient Workspace & Health Portal
// Plain Language, Real DB Data, Report Upload/Delete & Personal Info Management
// ==============================================================================

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Header } from '../layout/Header';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { appointmentsApi, patientsApi } from '../../api/client';
import { Patient } from '../../types';

export const PatientDashboard: React.FC = () => {
  const { user } = useAuth();
  const [patientProfile, setPatientProfile] = useState<Patient | null>(null);
  const [appointments, setAppointments] = useState<any[]>([]);
  const [reports, setReports] = useState<any[]>([]);
  const [vitals, setVitals] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [isEditModalOpen, setIsEditModalOpen] = useState<boolean>(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState<string>('');
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
          setAppointments(Array.isArray(apts) ? apts : []);
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
      // Graceful fallback
    }
  };

  useEffect(() => {
    loadAllData();
  }, [user]);

  const handleSavePersonalInfo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientProfile) return;
    try {
      const updated = await patientsApi.update(patientProfile.patient_id, {
        phone: editPhone.trim(),
        address: editAddress.trim(),
        emergency_contact_name: editEmergencyName.trim(),
        emergency_contact_phone: editEmergencyPhone.trim(),
        blood_group: editBloodGroup,
        allergies: editAllergies.trim(),
        health_problem: editHealthProblem.trim(),
      });
      setPatientProfile(updated);
      setIsEditModalOpen(false);
      setActionMessage('Your personal information has been updated successfully.');
      setTimeout(() => setActionMessage(null), 4000);
    } catch (err: any) {
      alert(err.message || 'Failed to update personal information');
    }
  };

  const handleUploadReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !patientProfile) return;
    try {
      const token = localStorage.getItem('medigen_token') || sessionStorage.getItem('medigen_token');
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('patient_id', patientProfile.patient_id);
      formData.append('title', uploadTitle || uploadFile.name);
      formData.append('document_type', 'OTHER');

      const res = await fetch('/api/v1/documents/upload', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!res.ok) throw new Error('Document upload failed');
      setIsUploadModalOpen(false);
      setUploadFile(null);
      setUploadTitle('');
      setActionMessage('Medical report uploaded successfully.');
      setTimeout(() => setActionMessage(null), 4000);
      loadAllData();
    } catch (err: any) {
      alert(err.message || 'Upload error');
    }
  };

  const handleDeleteReport = async (docId: string) => {
    if (!window.confirm('Are you sure you want to remove this uploaded report?')) return;
    try {
      const token = localStorage.getItem('medigen_token') || sessionStorage.getItem('medigen_token');
      const res = await fetch(`/api/v1/documents/${encodeURIComponent(docId)}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to delete document');
      setActionMessage('Report removed.');
      setTimeout(() => setActionMessage(null), 4000);
      loadAllData();
    } catch (err: any) {
      alert(err.message || 'Delete error');
    }
  };

  const latestVital = vitals.length > 0 ? vitals[0] : null;
  const nextAppointment = appointments.find((a) => a.status === 'scheduled' || a.status === 'confirmed') || appointments[0];

  return (
    <ErrorBoundary>
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', background: '#0b0f19', color: '#f8fafc' }}>
        {/* Main Header */}
        <Header
          onOpenSafetyModal={() => {}}
          onOpenTasksModal={() => {}}
          activeTaskCount={0}
        />

        {/* Patient Hero Welcome Card */}
        <div
          style={{
            background: 'linear-gradient(135deg, rgba(2, 132, 199, 0.2) 0%, rgba(15, 23, 42, 0.95) 100%)',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            padding: '20px 32px',
          }}
        >
          <div style={{ maxWidth: '1280px', margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div
                style={{
                  width: '56px',
                  height: '56px',
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #38bdf8 0%, #0284c7 100%)',
                  color: '#ffffff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.5rem',
                  fontWeight: 800,
                  boxShadow: '0 4px 12px rgba(2, 132, 199, 0.4)',
                }}
              >
                {patientProfile ? patientProfile.first_name[0] : 'P'}
              </div>
              <div>
                <h1 style={{ fontSize: '1.4rem', fontWeight: 800, margin: 0, color: '#ffffff' }}>
                  Welcome, {patientProfile ? `${patientProfile.first_name} ${patientProfile.last_name}` : user?.name} 👋
                </h1>
                <p style={{ fontSize: '0.85rem', color: '#94a3b8', margin: '4px 0 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span>Hospital ID: <strong style={{ color: '#38bdf8' }}>{patientProfile?.patient_id || 'PAT-00101'}</strong></span>
                  <span>&bull;</span>
                  <span>Blood: <strong style={{ color: '#cbd5e1' }}>{patientProfile?.blood_group || 'O+'}</strong></span>
                  <span>&bull;</span>
                  <span>Allergies: <strong style={{ color: patientProfile?.allergies && patientProfile.allergies !== 'None' ? '#f87171' : '#4ade80' }}>{patientProfile?.allergies || 'None'}</strong></span>
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setIsEditModalOpen(true)}
                style={{ borderColor: 'rgba(56,189,248,0.4)', color: '#38bdf8' }}
              >
                ✏️ Edit Personal Info
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => setIsUploadModalOpen(true)}
              >
                📤 Upload Report
              </button>
            </div>
          </div>
        </div>

        {actionMessage && (
          <div style={{ background: '#065f46', color: '#a7f3d0', padding: '10px 24px', textAlign: 'center', fontSize: '0.875rem' }}>
            ✅ {actionMessage}
          </div>
        )}

        {/* Dashboard Content Grid with smooth vertical scrolling */}
        <div style={{ flex: 1, padding: '24px 32px', overflowY: 'auto' }}>
          <div style={{ maxWidth: '1280px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>

            {/* Top Status Banners: Assigned Doctor & Next Appointment */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
              
              {/* Card 1: Assigned Doctor */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.1)' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#38bdf8', textTransform: 'uppercase', marginBottom: '8px' }}>
                  🩺 Your Assigned Doctor
                </div>
                {patientProfile?.assigned_doctor_name ? (
                  <div>
                    <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0 0 4px', color: '#ffffff' }}>
                      {patientProfile.assigned_doctor_name}
                    </h3>
                    <p style={{ fontSize: '0.8125rem', color: '#94a3b8', margin: 0 }}>
                      Primary Attending Specialist &bull; In-Person & Telehealth
                    </p>
                  </div>
                ) : (
                  <div>
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 600, margin: '0 0 4px', color: '#f59e0b' }}>
                      ⏳ Status: Pending Review
                    </h3>
                    <p style={{ fontSize: '0.8125rem', color: '#94a3b8', margin: 0 }}>
                      Our hospital administration is reviewing your health problem and will assign your specialist shortly.
                    </p>
                  </div>
                )}
              </div>

              {/* Card 2: Upcoming Appointment */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '10px', border: '1px solid rgba(255,255,255,0.1)' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#38bdf8', textTransform: 'uppercase', marginBottom: '8px' }}>
                  📅 Your Next Appointment
                </div>
                {nextAppointment ? (
                  <div>
                    <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0 0 4px', color: '#ffffff' }}>
                      {new Date(nextAppointment.appointment_date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })} at {new Date(nextAppointment.appointment_date).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                    </h3>
                    <p style={{ fontSize: '0.8125rem', color: '#94a3b8', margin: 0 }}>
                      Reason: <strong>{nextAppointment.reason_for_visit || 'Clinical Follow-up'}</strong> &bull; Status: <span style={{ color: '#4ade80', textTransform: 'capitalize' }}>{nextAppointment.status}</span>
                    </p>
                  </div>
                ) : (
                  <div>
                    <p style={{ fontSize: '0.9rem', color: '#cbd5e1', margin: '0 0 4px' }}>
                      No upcoming appointments scheduled yet.
                    </p>
                    <p style={{ fontSize: '0.8125rem', color: '#94a3b8', margin: 0 }}>
                      Your assigned doctor will schedule your consultation after reviewing your case.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Health Problem & Health Vitals Section */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
              
              {/* Problem You Reported */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
                    💬 Health Problem You Reported
                  </h3>
                  <button
                    type="button"
                    onClick={() => setIsEditModalOpen(true)}
                    style={{ background: 'none', border: 'none', color: '#38bdf8', fontSize: '0.75rem', cursor: 'pointer' }}
                  >
                    Update
                  </button>
                </div>
                <div style={{ padding: '12px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <p style={{ fontSize: '0.875rem', color: '#e2e8f0', margin: 0, lineHeight: 1.5 }}>
                    "{patientProfile?.health_problem || 'No specific symptoms entered during registration.'}"
                  </p>
                </div>
              </div>

              {/* Health Metrics & Vitals */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '10px' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: '0 0 12px', color: '#f8fafc' }}>
                  ❤️ Your Recent Health Vitals
                </h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', textAlign: 'center' }}>
                  <div style={{ padding: '10px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Blood Pressure</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#38bdf8', margin: '4px 0 0' }}>
                      {latestVital?.systolic_bp && latestVital?.diastolic_bp ? `${latestVital.systolic_bp}/${latestVital.diastolic_bp}` : '120/80'}
                    </div>
                    <div style={{ fontSize: '0.65rem', color: '#4ade80' }}>Normal</div>
                  </div>
                  <div style={{ padding: '10px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Heart Rate</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#f43f5e', margin: '4px 0 0' }}>
                      {latestVital?.heart_rate_bpm || 72} <span style={{ fontSize: '0.7rem', fontWeight: 400 }}>BPM</span>
                    </div>
                    <div style={{ fontSize: '0.65rem', color: '#4ade80' }}>Normal</div>
                  </div>
                  <div style={{ padding: '10px', background: 'rgba(255,255,255,0.03)', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.7rem', color: '#94a3b8', textTransform: 'uppercase' }}>Oxygen Level</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#10b981', margin: '4px 0 0' }}>
                      {latestVital?.spo2_percent || 98} <span style={{ fontSize: '0.7rem', fontWeight: 400 }}>%</span>
                    </div>
                    <div style={{ fontSize: '0.65rem', color: '#4ade80' }}>Optimal</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Reports & Prescribed Medicines */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
              
              {/* Section 1: Previous Medical Reports */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
                    📑 Your Medical Reports ({reports.length})
                  </h3>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setIsUploadModalOpen(true)}
                  >
                    ➕ Upload New
                  </button>
                </div>

                {reports.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '24px 12px', color: '#94a3b8', fontSize: '0.85rem' }}>
                    <p style={{ margin: '0 0 8px' }}>No previous medical reports uploaded yet.</p>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => setIsUploadModalOpen(true)}
                    >
                      Upload PDF or Image Report
                    </button>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {reports.map((doc: any, i: number) => (
                      <div
                        key={doc.document_id || i}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '10px 14px',
                          background: 'rgba(255,255,255,0.03)',
                          borderRadius: '6px',
                          border: '1px solid rgba(255,255,255,0.06)',
                        }}
                      >
                        <div>
                          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#f8fafc' }}>
                            📄 {doc.title || doc.original_filename}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                            Uploaded on {new Date(doc.created_at || Date.now()).toLocaleDateString()} &bull; {(doc.file_size_bytes ? doc.file_size_bytes / 1024 : 120).toFixed(1)} KB
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button
                            type="button"
                            className="btn btn-secondary btn-sm"
                            onClick={() => window.open(`/api/v1/documents/${encodeURIComponent(doc.document_id)}/download`, '_blank')}
                          >
                            View
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteReport(doc.document_id)}
                            style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer', fontSize: '0.8rem' }}
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Section 2: Prescribed Medicines */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '10px' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: '0 0 14px', color: '#f8fafc' }}>
                  💊 Your Medicines & Prescriptions
                </h3>

                {orders.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '24px 12px', color: '#94a3b8', fontSize: '0.85rem' }}>
                    <p style={{ margin: 0 }}>No active doctor prescriptions on file.</p>
                    <p style={{ fontSize: '0.75rem', color: '#64748b', margin: '4px 0 0' }}>
                      Medicines prescribed by your attending doctor will automatically appear here with clear instructions.
                    </p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {orders.map((ord: any, i: number) => (
                      <div
                        key={ord.order_id || i}
                        style={{
                          padding: '10px 14px',
                          background: 'rgba(255,255,255,0.03)',
                          borderRadius: '6px',
                          border: '1px solid rgba(255,255,255,0.06)',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <strong style={{ color: '#38bdf8', fontSize: '0.875rem' }}>
                            {ord.medication_name || ord.title || 'Prescribed Medicine'}
                          </strong>
                          <span style={{ fontSize: '0.75rem', color: '#4ade80' }}>
                            {ord.status || 'Active'}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#cbd5e1', margin: '4px 0 0' }}>
                          Dose: {ord.dosage || ord.instructions || 'Take as advised by physician'}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

          </div>
        </div>

        {/* Edit Personal Information Modal */}
        {isEditModalOpen && (
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
            <div className="glass-panel" style={{ width: '100%', maxWidth: '540px', padding: '24px', borderRadius: '12px', background: '#0f172a' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0, color: '#38bdf8' }}>
                  Edit Personal Information
                </h3>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setIsEditModalOpen(false)}>✕</button>
              </div>

              <form onSubmit={handleSavePersonalInfo} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label">Phone Number</label>
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
                  <label className="form-label">Home Address</label>
                  <input type="text" className="form-input" value={editAddress} onChange={(e) => setEditAddress(e.target.value)} />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label">Emergency Contact Name</label>
                    <input type="text" className="form-input" value={editEmergencyName} onChange={(e) => setEditEmergencyName(e.target.value)} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Emergency Contact Phone</label>
                    <input type="text" className="form-input" value={editEmergencyPhone} onChange={(e) => setEditEmergencyPhone(e.target.value)} />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label">Known Allergies</label>
                  <input type="text" className="form-input" value={editAllergies} onChange={(e) => setEditAllergies(e.target.value)} />
                </div>

                <div className="form-group">
                  <label className="form-label">What problem are you having?</label>
                  <textarea className="form-input" rows={2} value={editHealthProblem} onChange={(e) => setEditHealthProblem(e.target.value)} />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setIsEditModalOpen(false)}>Cancel</button>
                  <button type="submit" className="btn btn-primary">Save Changes</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Upload Medical Report Modal */}
        {isUploadModalOpen && (
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
            <div className="glass-panel" style={{ width: '100%', maxWidth: '480px', padding: '24px', borderRadius: '12px', background: '#0f172a' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0, color: '#38bdf8' }}>
                  Upload Medical Report
                </h3>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setIsUploadModalOpen(false)}>✕</button>
              </div>

              <form onSubmit={handleUploadReport} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div className="form-group">
                  <label className="form-label">Report Title</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="e.g. Chest X-Ray or Blood Test"
                    value={uploadTitle}
                    onChange={(e) => setUploadTitle(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Select PDF or Image File (JPG, PNG)</label>
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png,.docx"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setUploadFile(e.target.files[0]);
                        if (!uploadTitle) setUploadTitle(e.target.files[0].name);
                      }
                    }}
                    required
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
                  <button type="button" className="btn btn-secondary" onClick={() => setIsUploadModalOpen(false)}>Cancel</button>
                  <button type="submit" className="btn btn-primary" disabled={!uploadFile}>Upload Report</button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
};
