// ==============================================================================
// MediGen AI - Patient Context & Multi-Patient Switching
// ==============================================================================

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { patientsApi } from '../api/client';
import { Patient } from '../types';
import { useAuth } from './AuthContext';

interface PatientContextType {
  patients: Patient[];
  selectedPatient: Patient | null;
  isLoading: boolean;
  error: string | null;
  selectPatient: (patient: Patient | null) => void;
  selectPatientById: (patientId: string) => Promise<void>;
  refreshPatients: () => Promise<void>;
}

const PatientContext = createContext<PatientContextType | undefined>(undefined);

export const PatientProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const refreshPatients = useCallback(async () => {
    if (!user) {
      setPatients([]);
      setSelectedPatient(null);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const data = await patientsApi.list();
      const list = Array.isArray(data) ? data : (data as any)?.items || (data as any)?.patients || [];
      setPatients(list);

      // Auto-select first patient if none is selected
      if (list.length > 0 && !selectedPatient) {
        setSelectedPatient(list[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load patients.');
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      refreshPatients();
    }
  }, [user, refreshPatients]);

  const selectPatient = (patient: Patient | null) => {
    setSelectedPatient(patient);
  };

  const selectPatientById = async (patientId: string) => {
    setIsLoading(true);
    try {
      const p = await patientsApi.get(patientId);
      setSelectedPatient(p);
    } catch (err: any) {
      setError(err.message || `Failed to select patient ${patientId}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <PatientContext.Provider
      value={{
        patients,
        selectedPatient,
        isLoading,
        error,
        selectPatient,
        selectPatientById,
        refreshPatients,
      }}
    >
      {children}
    </PatientContext.Provider>
  );
};

export const usePatient = (): PatientContextType => {
  const context = useContext(PatientContext);
  if (!context) {
    throw new Error('usePatient must be used within a PatientProvider');
  }
  return context;
};
