// ==============================================================================
// MediGen AI - Patient Directory Component
// ==============================================================================

import React, { useState } from 'react';
import { usePatient } from '../../context/PatientContext';

export const PatientDirectory: React.FC = () => {
  const { patients, selectedPatient, selectPatient, isLoading, error, refreshPatients } = usePatient();
  const [searchTerm, setSearchTerm] = useState<string>('');

  const filtered = patients.filter((p) => {
    const query = searchTerm.toLowerCase();
    return (
      p.first_name.toLowerCase().includes(query) ||
      p.last_name.toLowerCase().includes(query) ||
      p.patient_id.toLowerCase().includes(query)
    );
  });

  return (
    <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
          Patient Directory ({patients.length})
        </h3>
        <button
          className="btn btn-secondary btn-sm"
          onClick={refreshPatients}
          disabled={isLoading}
          title="Reload patient list"
        >
          ↻
        </button>
      </div>

      <div style={{ marginBottom: '12px' }}>
        <input
          type="text"
          className="form-input"
          placeholder="Search by name or ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ padding: '8px 12px', fontSize: '0.8125rem' }}
        />
      </div>

      {error && (
        <div style={{ color: '#f87171', fontSize: '0.75rem', padding: '8px', background: 'rgba(239,68,68,0.1)', borderRadius: '4px', marginBottom: '8px' }}>
          {error}
        </div>
      )}

      <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {filtered.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8125rem', padding: '24px 0' }}>
            {isLoading ? 'Loading patient records...' : 'No patients found.'}
          </div>
        ) : (
          filtered.map((patient) => {
            const isSelected = selectedPatient?.patient_id === patient.patient_id;
            return (
              <div
                key={patient.patient_id}
                onClick={() => selectPatient(patient)}
                style={{
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-sm)',
                  background: isSelected ? 'rgba(2, 132, 199, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                  border: isSelected ? '1px solid var(--brand-primary)' : '1px solid var(--border-color)',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.875rem', color: isSelected ? '#ffffff' : 'var(--text-primary)' }}>
                    {patient.first_name} {patient.last_name}
                  </span>
                  <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>
                    {patient.patient_id}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span>DOB: {patient.date_of_birth}</span>
                  <span>{patient.gender}</span>
                </div>
                {patient.allergies && (
                  <div style={{ marginTop: '4px', fontSize: '0.7rem', color: '#fb923c' }}>
                    ⚠️ {patient.allergies}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
