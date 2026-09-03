// ==============================================================================
// MediGen AI - Enterprise Hospital Sidebar Navigation
// Role-aware, categorized navigation with badges, active states, and icons
// ==============================================================================

import React from 'react';
import { useAuth } from '../../context/AuthContext';

export interface NavItemDef {
  id: string;
  label: string;
  icon: string;
  badge?: string | number;
  testId?: string;
}

export interface NavSectionDef {
  title: string;
  items: NavItemDef[];
}

interface SidebarProps {
  activeSection: string;
  onSelectSection: (id: string) => void;
  pendingReviewsCount?: number;
  patientCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeSection,
  onSelectSection,
  pendingReviewsCount = 0,
  patientCount = 0,
}) => {
  const { user } = useAuth();
  const role = user?.role || 'doctor';

  // Build role-specific navigation menu
  const getNavSections = (): NavSectionDef[] => {
    if (role === 'admin') {
      return [
        {
          title: 'Administration',
          items: [
            { id: 'overview', label: 'Hospital Overview', icon: '📊', testId: 'nav-admin-overview' },
            { id: 'patients', label: 'Patient Intake & Review', icon: '👥', badge: pendingReviewsCount > 0 ? `${pendingReviewsCount} Pending` : undefined, testId: 'nav-admin-patients' },
            { id: 'doctors', label: 'Doctors & Clinical Staff', icon: '🩺', testId: 'nav-admin-doctors' },
            { id: 'appointments', label: 'Hospital Appointments', icon: '📅', testId: 'nav-admin-appointments' },
          ],
        },
        {
          title: 'Governance & Infrastructure',
          items: [
            { id: 'tenants', label: 'Multi-Tenant Facilities', icon: '🏥', testId: 'nav-admin-tenants' },
            { id: 'smart_ehr', label: 'SMART on FHIR Hub', icon: '🌐', testId: 'nav-admin-fhir' },
            { id: 'regional_interop', label: 'Regional Health Exchange', icon: '🔗', testId: 'nav-admin-interop' },
            { id: 'security', label: 'Security & Audit Logs', icon: '🛡️', testId: 'nav-admin-security' },
            { id: 'trials_gov', label: 'Clinical Trials Governance', icon: '🔬', testId: 'nav-admin-trials' },
            { id: 'agents', label: 'Autonomous AI Agents', icon: '🤖', testId: 'nav-admin-agents' },
            { id: 'quality', label: 'Quality Measures & KPIs', icon: '📈', testId: 'nav-admin-quality' },
            { id: 'diagnostics', label: 'System Health & Metrics', icon: '⚙️', testId: 'nav-admin-diagnostics' },
          ],
        },
      ];
    }

    if (role === 'patient') {
      return [
        {
          title: 'My Health Portal',
          items: [
            { id: 'overview', label: 'Health Overview', icon: '🏠', testId: 'nav-patient-overview' },
            { id: 'appointments', label: 'My Appointments', icon: '📅', testId: 'nav-patient-apts' },
            { id: 'reports', label: 'My Medical Reports', icon: '📁', testId: 'nav-patient-reports' },
            { id: 'medications', label: 'My Prescribed Medicines', icon: '💊', testId: 'nav-patient-meds' },
            { id: 'vitals', label: 'My Vitals & Telemetry', icon: '💓', testId: 'nav-patient-vitals' },
            { id: 'care_plan', label: 'My Care Plan & Tasks', icon: '📋', testId: 'nav-patient-care' },
            { id: 'profile', label: 'Personal Information', icon: '👤', testId: 'nav-patient-profile' },
          ],
        },
      ];
    }

    // Doctor & Healthcare Staff
    return [
      {
        title: 'Clinical Workspace',
        items: [
          { id: 'overview', label: 'Clinical Overview', icon: '📊', testId: 'nav-doc-overview' },
          { id: 'chat', label: 'AI Copilot & Scribe', icon: '💬', testId: 'nav-doc-chat' },
          { id: 'timeline', label: 'Longitudinal Timeline', icon: '📅', testId: 'nav-doc-timeline' },
          { id: 'notes', label: 'Clinical Notes & EHR', icon: '📝', testId: 'nav-doc-notes' },
          { id: 'vitals', label: 'Vitals & CDS Alerts', icon: '💓', testId: 'nav-doc-vitals' },
          { id: 'care_plans', label: 'Care Plans & Tasks', icon: '📋', testId: 'nav-doc-care' },
          { id: 'transitions', label: 'Transitions & Discharge', icon: '🔄', testId: 'nav-doc-transitions' },
        ],
      },
      {
        title: 'Medications & Orders',
        items: [
          { id: 'orders', label: 'Orders & Prescriptions', icon: '📦', testId: 'nav-doc-orders' },
          { id: 'emar', label: 'Closed-Loop eMAR & BCMA', icon: '💊', testId: 'tab-btn-emar' },
          { id: 'cds_pgx', label: 'CDS, PGx & Order Sets', icon: '🧬', testId: 'tab-btn-cds-pgx' },
        ],
      },
      {
        title: 'Diagnostics & Imaging',
        items: [
          { id: 'documents', label: 'Medical Documents & OCR', icon: '📁', testId: 'nav-doc-docs' },
          { id: 'media', label: 'Diagnostics & Media Hub', icon: '🖼️', testId: 'nav-doc-media' },
          { id: 'imaging', label: 'Radiology & AI Heatmaps', icon: '🩻', testId: 'tab-btn-imaging' },
          { id: 'pacs_waveforms', label: 'DICOM PACS & ECG Waveforms', icon: '🫀', testId: 'tab-btn-pacs-waveforms' },
        ],
      },
      {
        title: 'Intelligence & Research',
        items: [
          { id: 'collaboration', label: 'Live Telehealth & Room', icon: '📡', testId: 'tab-btn-collaboration' },
          { id: 'cohorts', label: 'Cohort Population Search', icon: '👥', testId: 'nav-doc-cohorts' },
          { id: 'rpm', label: 'Remote Patient Monitoring', icon: '📡', testId: 'tab-btn-rpm' },
          { id: 'trials', label: 'Precision Clinical Trials', icon: '🧪', testId: 'tab-btn-trials' },
          { id: 'trials_governance', label: 'Trials Governance & GCP', icon: '🏛️', testId: 'tab-btn-trials-governance' },
          { id: 'agents', label: 'Autonomous AI Agents', icon: '🤖', testId: 'tab-btn-agents' },
          { id: 'quality', label: 'Quality Measures & MIPS', icon: '📈', testId: 'nav-doc-quality' },
          { id: 'smart_ehr', label: 'SMART on FHIR Gateway', icon: '🔌', testId: 'tab-btn-smart-ehr' },
          { id: 'regional_interop', label: 'Regional Interoperability & EMPI', icon: '🌐', testId: 'tab-btn-regional-interop' },
          { id: 'security', label: 'Security & Compliance', icon: '🛡️', testId: 'tab-btn-security' },
          { id: 'diagnostics', label: 'System Diagnostics', icon: '⚙️', testId: 'tab-btn-diagnostics' },
          { id: 'tenants', label: 'Facilities & Tenants', icon: '🏥', testId: 'tab-btn-tenants' },
        ],
      },
    ];
  };

  const sections = getNavSections();

  return (
    <aside className="hospital-sidebar" data-testid="hospital-sidebar">
      {/* Sidebar Header / Brand */}
      <div className="hospital-sidebar-header">
        <a href="/" className="brand-logo" style={{ textDecoration: 'none' }}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
            <path d="M12 5v14" />
            <path d="M5 12h14" />
          </svg>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '1.05rem', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
              MediGen <span style={{ color: 'var(--brand-primary)' }}>AI</span>
            </span>
            <span style={{ fontSize: '0.625rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Hospital System
            </span>
          </div>
        </a>
      </div>

      {/* Navigation Sections */}
      <nav className="hospital-sidebar-nav">
        {sections.map((sec, idx) => (
          <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            <div className="nav-section-title">{sec.title}</div>
            {sec.items.map((item) => {
              const isActive = activeSection === item.id;
              return (
                <button
                  key={item.id}
                  data-testid={item.testId}
                  className={`nav-item ${isActive ? 'active' : ''}`}
                  onClick={() => onSelectSection(item.id)}
                  title={item.label}
                >
                  <span className="nav-item-icon">{item.icon}</span>
                  <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.label}
                  </span>
                  {item.badge && <span className="nav-badge">{item.badge}</span>}
                </button>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Sidebar Footer User Info */}
      <div
        style={{
          padding: '12px 14px',
          borderTop: '1px solid var(--border-color)',
          background: 'rgba(9, 13, 24, 0.95)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
        }}
      >
        <div
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            background: role === 'admin' ? 'rgba(239, 68, 68, 0.2)' : role === 'doctor' ? 'rgba(56, 189, 248, 0.2)' : 'rgba(52, 211, 153, 0.2)',
            color: role === 'admin' ? '#f87171' : role === 'doctor' ? '#38bdf8' : '#34d399',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 700,
            fontSize: '0.85rem',
            border: `1px solid ${role === 'admin' ? 'rgba(239, 68, 68, 0.4)' : role === 'doctor' ? 'rgba(56, 189, 248, 0.4)' : 'rgba(52, 211, 153, 0.4)'}`,
          }}
        >
          {user?.name?.charAt(0).toUpperCase() || user?.first_name?.charAt(0).toUpperCase() || 'U'}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', flex: 1 }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#ffffff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {role === 'admin' ? 'System Administrator' : role === 'doctor' ? 'Clinical Physician' : 'Patient Workspace'}
          </span>
          <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            {role === 'doctor' ? 'Clinical Staff' : role === 'admin' ? 'Hospital Governance' : 'Health Portal'}
          </span>
        </div>
      </div>
    </aside>
  );
};
