// ==============================================================================
// MediGen AI - Role-Based Dashboard Page Router
// ==============================================================================

import React from 'react';
import { useAuth } from '../context/AuthContext';
import { DoctorDashboard } from '../components/dashboard/DoctorDashboard';
import { AdminDashboard } from '../components/dashboard/AdminDashboard';
import { PatientDashboard } from '../components/dashboard/PatientDashboard';
import { ErrorBoundary } from '../components/common/ErrorBoundary';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();

  if (!user) {
    return null;
  }

  return (
    <ErrorBoundary fallbackTitle="Clinical Dashboard Root">
      {user.role === 'patient' && <PatientDashboard />}
      {user.role === 'admin' && <AdminDashboard />}
      {(user.role === 'doctor' || user.role === 'healthcare_staff' || (user.role !== 'patient' && user.role !== 'admin')) && (
        <DoctorDashboard />
      )}
    </ErrorBoundary>
  );
};
