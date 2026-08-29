// ==============================================================================
// MediGen AI - Active Patient Context Ribbon
// ==============================================================================

import React from 'react';
import { usePatient } from '../../context/PatientContext';

export const PatientRibbon: React.FC = () => {
  const { selectedPatient, patients, selectPatient } = usePatient();

  if (!selectedPatient) {
    return (
      <div className="patient-context-ribbon" style={{ background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)' }}>
        <span style={{ color: '#fca5a5' }}>⚠️ No active patient context selected. Please choose a patient from the directory.</span>
      </div>
    );
  }

  return (
    <div className="patient-context-ribbon">
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', textTransform: 'uppercase', fontWeight: 600 }}>
            Active Patient:
          </span>
          <span style={{ fontWeight: 700, color: '#ffffff', fontSize: '0.95rem' }}>
            {selectedPatient.first_name} {selectedPatient.last_name}
          </span>
          <span className="badge badge-info">{selectedPatient.patient_id}</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text-secondary)', fontSize: '0.8125rem' }}>
          <span>DOB: <strong style={{ color: 'var(--text-primary)' }}>{selectedPatient.date_of_birth}</strong></span>
          <span>Gender: <strong style={{ color: 'var(--text-primary)' }}>{selectedPatient.gender}</strong></span>
          {selectedPatient.blood_group && (
            <span>Blood: <strong style={{ color: 'var(--text-primary)' }}>{selectedPatient.blood_group}</strong></span>
          )}
          {selectedPatient.allergies && (
            <span style={{ color: '#fca5a5', background: 'rgba(239, 68, 68, 0.15)', padding: '1px 6px', borderRadius: '4px' }}>
              Allergies: {selectedPatient.allergies}
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <select
          className="form-select"
          style={{ width: 'auto', padding: '4px 10px', fontSize: '0.75rem' }}
          value={selectedPatient.patient_id}
          onChange={(e) => {
            const found = patients.find((p) => p.patient_id === e.target.value);
            if (found) selectPatient(found);
          }}
        >
          {patients.map((p) => (
            <option key={p.patient_id} value={p.patient_id}>
              Switch: {p.first_name} {p.last_name} ({p.patient_id})
            </option>
          ))}
        </select>
      </div>
    </div>
  );
};
