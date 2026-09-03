// ==============================================================================
// MediGen AI - Enterprise Hospital AppShell Layout
// Unified container with responsive left sidebar, sticky header, patient ribbon & content
// ==============================================================================

import React from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { PatientRibbon } from './PatientRibbon';
import { usePatient } from '../../context/PatientContext';
import { useAuth } from '../../context/AuthContext';
import { ErrorBoundary } from '../common/ErrorBoundary';

interface AppShellProps {
  activeSection: string;
  activeSectionTitle: string;
  onSelectSection: (id: string) => void;
  pendingReviewsCount?: number;
  onOpenSafetyModal?: () => void;
  onOpenTasksModal?: () => void;
  activeTaskCount?: number;
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({
  activeSection,
  activeSectionTitle,
  onSelectSection,
  pendingReviewsCount = 0,
  onOpenSafetyModal,
  onOpenTasksModal,
  activeTaskCount = 0,
  children,
}) => {
  const { user } = useAuth();
  const { selectedPatient } = usePatient();

  const isPatientRole = user?.role === 'patient';
  const showPatientRibbon = !isPatientRole && selectedPatient !== null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      {/* Top Header Bar */}
      <Header
        onOpenSafetyModal={onOpenSafetyModal || (() => {})}
        onOpenTasksModal={onOpenTasksModal || (() => {})}
        activeTaskCount={activeTaskCount}
      />

      {/* Main App Container with Sidebar & Content Area */}
      <div className="hospital-shell" data-testid="hospital-shell" style={{ flex: 1, minHeight: 0, display: 'flex' }}>
        {/* Unified Enterprise Left Sidebar */}
        <Sidebar
          activeSection={activeSection}
          onSelectSection={onSelectSection}
          pendingReviewsCount={pendingReviewsCount}
        />

        {/* Main Content Area */}
        <div className="hospital-main" style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, height: '100%' }}>
          {/* Selected Patient Context Ribbon (Doctor & Staff view) */}
          {showPatientRibbon && (
            <div style={{ flexShrink: 0, borderBottom: '1px solid var(--border-color)' }}>
              <PatientRibbon />
            </div>
          )}

          {/* Scrollable Viewport */}
          <main className="hospital-content-area" id="hospital-main-content" style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
            <ErrorBoundary fallbackTitle={activeSectionTitle}>
              {children}
            </ErrorBoundary>
          </main>
        </div>
      </div>
    </div>
  );
};
