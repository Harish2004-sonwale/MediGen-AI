// ==============================================================================
// MediGen AI - Patient Registration & Onboarding Modal
// Plain Language, Simple Flow, Upload Reports & Queue for Admin Review
// ==============================================================================

import React, { useState } from 'react';
import { patientsApi } from '../../api/client';
import { useAuth } from '../../context/AuthContext';

interface PatientRegistrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const PatientRegistrationModal: React.FC<PatientRegistrationModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { login } = useAuth();
  const [step, setStep] = useState<number>(1);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Step 1: Basic Information
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [dob, setDob] = useState('1998-05-14');
  const [gender, setGender] = useState('male');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [address, setAddress] = useState('');

  // Step 2: Emergency Contact & Health Info
  const [emergencyName, setEmergencyName] = useState('');
  const [emergencyPhone, setEmergencyPhone] = useState('');
  const [bloodGroup, setBloodGroup] = useState('O+');
  const [allergies, setAllergies] = useState('None');

  // Step 3: Current Problem & Previous Reports
  const [healthProblem, setHealthProblem] = useState('');
  const [hasPreviousReports, setHasPreviousReports] = useState<boolean>(false);
  const [previousHealthProblems, setPreviousHealthProblems] = useState('');
  const [currentMedicines, setCurrentMedicines] = useState('');
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files);
      setUploadedFiles((prev) => [...prev, ...filesArray]);
    }
  };

  const removeFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmitRegistration = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match. Please re-enter your password.');
      return;
    }

    if (password.length < 8) {
      setErrorMessage('Password must be at least 8 characters long.');
      return;
    }

    if (!healthProblem.trim()) {
      setErrorMessage('Please describe the problem or symptom you are having.');
      return;
    }

    setIsSubmitting(true);
    try {
      // 1. Call Backend Self-Registration API
      const registerPayload = {
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        date_of_birth: dob,
        gender: gender,
        phone: phone.trim(),
        email: email.trim(),
        password: password,
        address: address.trim() || undefined,
        emergency_contact_name: emergencyName.trim() || undefined,
        emergency_contact_phone: emergencyPhone.trim() || undefined,
        blood_group: bloodGroup || undefined,
        allergies: allergies.trim() || undefined,
        health_problem: healthProblem.trim(),
        previous_diagnoses: previousHealthProblems.trim() || undefined,
        current_medications: currentMedicines.trim() || undefined,
      };

      await patientsApi.selfRegister(registerPayload);

      // 2. Log in with new credentials
      await login(email.trim(), password);

      if (onSuccess) onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'Unable to complete registration. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
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
        overflowY: 'auto',
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '620px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: 'var(--shadow-xl)',
          border: '1px solid rgba(255,255,255,0.15)',
          borderRadius: '12px',
          background: '#0f172a',
          color: '#f8fafc',
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: '#38bdf8' }}>
              Create Patient Account
            </h2>
            <p style={{ fontSize: '0.8125rem', color: '#94a3b8', margin: '4px 0 0' }}>
              Join MediGen Hospital &bull; Step {step} of 2
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onClose}
            style={{ borderRadius: '50%', width: '32px', height: '32px', padding: 0 }}
          >
            ✕
          </button>
        </div>

        {/* Modal Body with smooth vertical scrolling */}
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1 }}>
          {errorMessage && (
            <div
              style={{
                padding: '12px 16px',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid #ef4444',
                borderRadius: '8px',
                color: '#fca5a5',
                fontSize: '0.875rem',
                marginBottom: '20px',
              }}
            >
              ⚠️ {errorMessage}
            </div>
          )}

          <form onSubmit={handleSubmitRegistration}>
            {step === 1 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label" style={{ color: '#cbd5e1' }}>First Name *</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Rahul"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label" style={{ color: '#cbd5e1' }}>Last Name *</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Patil"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label" style={{ color: '#cbd5e1' }}>Date of Birth *</label>
                    <input
                      type="date"
                      className="form-input"
                      value={dob}
                      onChange={(e) => setDob(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label" style={{ color: '#cbd5e1' }}>Gender *</label>
                    <select
                      className="form-input"
                      value={gender}
                      onChange={(e) => setGender(e.target.value)}
                      required
                    >
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                      <option value="prefer_not_to_say">Prefer not to say</option>
                    </select>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label" style={{ color: '#cbd5e1' }}>Mobile Number *</label>
                    <input
                      type="tel"
                      className="form-input"
                      placeholder="+91-98200-11223"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label" style={{ color: '#cbd5e1' }}>Email Address *</label>
                    <input
                      type="email"
                      className="form-input"
                      placeholder="rahul.patil@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label" style={{ color: '#cbd5e1' }}>Password *</label>
                    <input
                      type="password"
                      className="form-input"
                      placeholder="Minimum 8 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label" style={{ color: '#cbd5e1' }}>Confirm Password *</label>
                    <input
                      type="password"
                      className="form-input"
                      placeholder="Re-type password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ color: '#cbd5e1' }}>Home Address (Optional)</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Shivaji Park, Dadar, Mumbai"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '12px' }}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => {
                      if (!firstName.trim() || !lastName.trim() || !email.trim() || !password) {
                        setErrorMessage('Please fill in all required basic fields before continuing.');
                        return;
                      }
                      setErrorMessage(null);
                      setStep(2);
                    }}
                  >
                    Next: Health Information &rarr;
                  </button>
                </div>
              </div>
            )}

            {step === 2 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label" style={{ color: '#cbd5e1' }}>Blood Group (Optional)</label>
                    <select
                      className="form-input"
                      value={bloodGroup}
                      onChange={(e) => setBloodGroup(e.target.value)}
                    >
                      <option value="O+">O Positive (O+)</option>
                      <option value="O-">O Negative (O-)</option>
                      <option value="A+">A Positive (A+)</option>
                      <option value="A-">A Negative (A-)</option>
                      <option value="B+">B Positive (B+)</option>
                      <option value="B-">B Negative (B-)</option>
                      <option value="AB+">AB Positive (AB+)</option>
                      <option value="AB-">AB Negative (AB-)</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label" style={{ color: '#cbd5e1' }}>Known Allergies (Optional)</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. Penicillin, Peanuts, None"
                      value={allergies}
                      onChange={(e) => setAllergies(e.target.value)}
                    />
                  </div>
                </div>

                <div className="form-group">
                  <label className="form-label" style={{ color: '#cbd5e1', fontWeight: 600 }}>
                    What problem are you having? *
                  </label>
                  <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0 0 6px' }}>
                    Describe your symptoms in your own words so our hospital doctors can review your case.
                  </p>
                  <textarea
                    className="form-input"
                    rows={3}
                    placeholder="e.g. I have chest tightness and mild shortness of breath for 2 days after exertion..."
                    value={healthProblem}
                    onChange={(e) => setHealthProblem(e.target.value)}
                    required
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div className="form-group">
                    <label className="form-label" style={{ color: '#cbd5e1' }}>Emergency Contact Name</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="Pooja Patil"
                      value={emergencyName}
                      onChange={(e) => setEmergencyName(e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label" style={{ color: '#cbd5e1' }}>Emergency Contact Phone</label>
                    <input
                      type="tel"
                      className="form-input"
                      placeholder="+91-98200-11224"
                      value={emergencyPhone}
                      onChange={(e) => setEmergencyPhone(e.target.value)}
                    />
                  </div>
                </div>

                {/* Previous Medical Reports Section */}
                <div
                  style={{
                    padding: '16px',
                    background: 'rgba(255,255,255,0.03)',
                    borderRadius: '8px',
                    border: '1px solid rgba(255,255,255,0.08)',
                  }}
                >
                  <label className="form-label" style={{ color: '#cbd5e1', marginBottom: '8px' }}>
                    Do you have previous medical reports?
                  </label>
                  <div style={{ display: 'flex', gap: '12px', marginBottom: '12px' }}>
                    <button
                      type="button"
                      className={`btn btn-sm ${hasPreviousReports ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => setHasPreviousReports(true)}
                    >
                      Yes
                    </button>
                    <button
                      type="button"
                      className={`btn btn-sm ${!hasPreviousReports ? 'btn-primary' : 'btn-secondary'}`}
                      onClick={() => {
                        setHasPreviousReports(false);
                        setUploadedFiles([]);
                      }}
                    >
                      No
                    </button>
                  </div>

                  {hasPreviousReports && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      <div className="form-group">
                        <label className="form-label" style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                          Upload PDF, JPG, or PNG reports
                        </label>
                        <input
                          type="file"
                          accept=".pdf,.jpg,.jpeg,.png,.docx"
                          multiple
                          onChange={handleFileChange}
                          style={{
                            fontSize: '0.8125rem',
                            color: '#cbd5e1',
                            padding: '6px',
                            background: 'rgba(0,0,0,0.2)',
                            borderRadius: '4px',
                            border: '1px solid rgba(255,255,255,0.1)',
                          }}
                        />
                      </div>

                      {uploadedFiles.length > 0 && (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                          <span style={{ fontSize: '0.75rem', color: '#38bdf8', fontWeight: 600 }}>
                            {uploadedFiles.length} file(s) selected:
                          </span>
                          {uploadedFiles.map((file, idx) => (
                            <div
                              key={idx}
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                padding: '6px 10px',
                                background: 'rgba(255,255,255,0.05)',
                                borderRadius: '4px',
                                fontSize: '0.8rem',
                              }}
                            >
                              <span>📄 {file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
                              <button
                                type="button"
                                onClick={() => removeFile(idx)}
                                style={{ background: 'none', border: 'none', color: '#f87171', cursor: 'pointer' }}
                              >
                                ✕
                              </button>
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="form-group">
                        <label className="form-label" style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                          Previous Health Problems (Optional)
                        </label>
                        <input
                          type="text"
                          className="form-input"
                          placeholder="e.g. Mild hypertension (2024)"
                          value={previousHealthProblems}
                          onChange={(e) => setPreviousHealthProblems(e.target.value)}
                        />
                      </div>

                      <div className="form-group">
                        <label className="form-label" style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                          Current Medicines (Optional)
                        </label>
                        <input
                          type="text"
                          className="form-input"
                          placeholder="e.g. Amlodipine 5mg once daily"
                          value={currentMedicines}
                          onChange={(e) => setCurrentMedicines(e.target.value)}
                        />
                      </div>
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '12px' }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setStep(1)}
                  >
                    &larr; Back
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={isSubmitting}
                    style={{ minWidth: '160px' }}
                  >
                    {isSubmitting ? 'Creating Account...' : 'Submit & Register'}
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>
      </div>
    </div>
  );
};
