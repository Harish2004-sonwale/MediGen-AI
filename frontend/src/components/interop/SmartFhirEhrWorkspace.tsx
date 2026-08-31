import React, { useEffect, useState } from 'react';
import * as client from '../../api/client';
import { CDSCard, CDSService, SmartConfiguration, TerminologyConcept } from '../../types';
import { BulkExportModal } from './BulkExportModal';
import { FHIRSubscriptionsConsole } from './FHIRSubscriptionsConsole';

interface Props {
  selectedPatientId?: string;
}

export const SmartFhirEhrWorkspace: React.FC<Props> = ({ selectedPatientId = 'PAT-001' }) => {
  const [activeTab, setActiveTab] = useState<'smart_launch' | 'cds_hooks' | 'terminology' | 'subscriptions' | 'bulk_export'>('cds_hooks');
  const [showBulkExportModal, setShowBulkExportModal] = useState(false);
  const [smartConfig, setSmartConfig] = useState<SmartConfiguration | null>(null);
  const [cdsServices, setCdsServices] = useState<CDSService[]>([]);
  const [cdsCards, setCdsCards] = useState<CDSCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [authCode, setAuthCode] = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  // Terminology state
  const [termQuery, setTermQuery] = useState('Serum Potassium');
  const [normalizedResult, setNormalizedResult] = useState<TerminologyConcept | null>(null);

  useEffect(() => {
    loadDiscovery();
  }, []);

  const loadDiscovery = async () => {
    try {
      setLoading(true);
      const [config, servicesRes] = await Promise.all([
        client.smartApi.getSmartConfig().catch(() => null),
        client.cdsApi.discoverServices().catch(() => ({ services: [] })),
      ]);
      setSmartConfig(config);
      setCdsServices(servicesRes.services || []);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateSmartLaunch = async () => {
    try {
      setLoading(true);
      const authRes = await client.smartApi.authorize({
        client_id: 'epic-smart-client-001',
        redirect_uri: 'https://app.medigen.ai/smart/callback',
        response_type: 'code',
        scope: 'launch/patient patient/Patient.read openid fhirUser',
        patient: selectedPatientId,
        state: `state-${Date.now()}`,
      });
      setAuthCode(authRes.code);

      // Exchange code
      const tokenRes = await client.smartApi.exchangeToken({
        grant_type: 'authorization_code',
        code: authRes.code,
        redirect_uri: 'https://app.medigen.ai/smart/callback',
        client_id: 'epic-smart-client-001',
      });
      setAccessToken(tokenRes.access_token);
    } catch (err: any) {
      alert(`SMART launch error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleInvokePatientViewHook = async () => {
    try {
      setLoading(true);
      const res = await client.cdsApi.invokePatientView(selectedPatientId);
      setCdsCards(res.cards || []);
    } catch (err: any) {
      alert(`CDS Hook error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleInvokeOrderSelectHook = async (medName: string) => {
    try {
      setLoading(true);
      const res = await client.cdsApi.invokeOrderSelect(selectedPatientId, [medName]);
      setCdsCards(res.cards || []);
    } catch (err: any) {
      alert(`CDS Hook error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleNormalizeTerm = async () => {
    try {
      setLoading(true);
      const res = await client.terminologyApi.normalizeConcept(termQuery);
      setNormalizedResult(res.normalized || null);
    } catch (err: any) {
      alert(`Terminology error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card-panel" data-testid="smart-fhir-ehr-workspace" style={{ padding: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700, color: '#1e293b' }}>
            Enterprise EHR Integration & SMART on FHIR 2.0 Hub
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#64748b' }}>
            HL7 SMART App Launch 2.0.0, CDS Hooks 2.0 Card Simulator & Terminology Normalization
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`btn-subtle ${activeTab === 'cds_hooks' ? 'active' : ''}`}
            onClick={() => setActiveTab('cds_hooks')}
            style={{ padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', border: '1px solid #cbd5e1' }}
          >
            CDS Hooks 2.0
          </button>
          <button
            className={`btn-subtle ${activeTab === 'smart_launch' ? 'active' : ''}`}
            onClick={() => setActiveTab('smart_launch')}
            style={{ padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', border: '1px solid #cbd5e1' }}
          >
            SMART Launch
          </button>
          <button
            className={`btn-subtle ${activeTab === 'terminology' ? 'active' : ''}`}
            onClick={() => setActiveTab('terminology')}
            style={{ padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', border: '1px solid #cbd5e1' }}
          >
            Terminology Normalizer
          </button>
          <button
            id="btn-fhir-subscriptions-tab"
            className={`btn-subtle ${activeTab === 'subscriptions' ? 'active' : ''}`}
            onClick={() => setActiveTab('subscriptions')}
            style={{ padding: '8px 16px', borderRadius: '6px', cursor: 'pointer', border: '1px solid #cbd5e1' }}
          >
            Topic Subscriptions
          </button>
          <button
            id="btn-bulk-export"
            onClick={() => setShowBulkExportModal(true)}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              cursor: 'pointer',
              border: 'none',
              backgroundColor: '#0891b2',
              color: '#fff',
              fontWeight: 600,
            }}
          >
            Bulk FHIR Export ($export)
          </button>
        </div>
      </div>

      {/* CDS HOOKS TAB */}
      {activeTab === 'cds_hooks' && (
        <div>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
            <button
              onClick={handleInvokePatientViewHook}
              disabled={loading}
              style={{
                backgroundColor: '#2563eb',
                color: '#fff',
                border: 'none',
                padding: '10px 18px',
                borderRadius: '6px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Simulate 'patient-view' Hook (Patient: {selectedPatientId})
            </button>
            <button
              onClick={() => handleInvokeOrderSelectHook('Aspirin 325mg')}
              disabled={loading}
              style={{
                backgroundColor: '#d97706',
                color: '#fff',
                border: 'none',
                padding: '10px 18px',
                borderRadius: '6px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Simulate 'order-select' (Aspirin draft)
            </button>
          </div>

          {/* Rendered CDS Cards */}
          <div style={{ marginTop: '20px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '12px' }}>
              Active CDS Decision Support Cards ({cdsCards.length})
            </h3>
            {cdsCards.length === 0 ? (
              <div style={{ padding: '24px', textAlign: 'center', background: '#f8fafc', borderRadius: '8px', color: '#94a3b8' }}>
                No active CDS Cards returned. Click a simulation button above to evaluate clinical hooks.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {cdsCards.map((card, idx) => (
                  <div
                    key={card.uuid || idx}
                    data-testid="cds-card-item"
                    style={{
                      borderLeft: `4px solid ${
                        card.indicator === 'critical' ? '#ef4444' : card.indicator === 'warning' ? '#f59e0b' : '#3b82f6'
                      }`,
                      background: card.indicator === 'critical' ? '#fef2f2' : card.indicator === 'warning' ? '#fffbeb' : '#eff6ff',
                      padding: '16px',
                      borderRadius: '6px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '12px', fontWeight: 700, textTransform: 'uppercase', color: '#475569' }}>
                        {card.indicator} • {card.source.label}
                      </span>
                    </div>
                    <h4 data-testid="cds-card-summary" style={{ margin: '6px 0', fontSize: '15px', color: '#0f172a' }}>{card.summary}</h4>
                    {card.detail && <p style={{ margin: '4px 0 12px', fontSize: '13px', color: '#334155' }}>{card.detail}</p>}

                    {/* Suggestions */}
                    {card.suggestions && card.suggestions.length > 0 && (
                      <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
                        {card.suggestions.map((sug, sIdx) => (
                          <button
                            key={sIdx}
                            style={{
                              padding: '6px 12px',
                              background: '#fff',
                              border: '1px solid #cbd5e1',
                              borderRadius: '4px',
                              fontSize: '12px',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            ✓ {sug.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SMART LAUNCH TAB */}
      {activeTab === 'smart_launch' && (
        <div>
          <div style={{ background: '#f8fafc', padding: '16px', borderRadius: '8px', marginBottom: '16px' }}>
            <h4 style={{ margin: '0 0 8px', fontSize: '14px' }}>SMART on FHIR 2.0 Capabilities Discovery</h4>
            <pre style={{ margin: 0, fontSize: '12px', background: '#e2e8f0', padding: '10px', borderRadius: '4px', overflowX: 'auto' }}>
              {JSON.stringify(smartConfig, null, 2)}
            </pre>
          </div>

          <button
            onClick={handleSimulateSmartLaunch}
            disabled={loading}
            style={{
              backgroundColor: '#059669',
              color: '#fff',
              border: 'none',
              padding: '10px 18px',
              borderRadius: '6px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Simulate Full SMART OAuth2 PKCE Launch
          </button>

          {accessToken && (
            <div style={{ marginTop: '16px', padding: '16px', background: '#ecfdf5', borderRadius: '6px', border: '1px solid #a7f3d0' }}>
              <div style={{ color: '#065f46', fontWeight: 600, fontSize: '14px' }}>✓ SMART Access Token Issued:</div>
              <code style={{ fontSize: '11px', wordBreak: 'break-all', display: 'block', marginTop: '6px', color: '#047857' }}>
                {accessToken}
              </code>
            </div>
          )}
        </div>
      )}

      {/* TERMINOLOGY TAB */}
      {activeTab === 'terminology' && (
        <div>
          <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
            <input
              type="text"
              value={termQuery}
              onChange={(e) => setTermQuery(e.target.value)}
              placeholder="e.g. Serum Potassium, Type 2 Diabetes, Lisinopril..."
              style={{ flex: 1, padding: '10px 14px', borderRadius: '6px', border: '1px solid #cbd5e1' }}
            />
            <button
              onClick={handleNormalizeTerm}
              disabled={loading}
              style={{
                backgroundColor: '#6366f1',
                color: '#fff',
                border: 'none',
                padding: '10px 20px',
                borderRadius: '6px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Normalize Concept
            </button>
          </div>

          {normalizedResult && (
            <div style={{ padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <h4 style={{ margin: '0 0 6px', fontSize: '14px', color: '#1e293b' }}>Standardized Clinical Concept</h4>
              <div style={{ fontSize: '13px', color: '#334155' }}>
                <div><strong>Standard System:</strong> <span data-testid="norm-system">{normalizedResult.system}</span></div>
                <div><strong>Code:</strong> <code data-testid="norm-code">{normalizedResult.code}</code></div>
                <div><strong>Display Title:</strong> <span data-testid="norm-display">{normalizedResult.display}</span></div>
                <div><strong>Confidence:</strong> {(normalizedResult.confidence * 100).toFixed(1)}% ({normalizedResult.match_type})</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* FHIR TOPIC SUBSCRIPTIONS TAB */}
      {activeTab === 'subscriptions' && (
        <div data-testid="fhir-subscriptions-tab-panel">
          <FHIRSubscriptionsConsole />
        </div>
      )}

      {/* BULK FHIR EXPORT MODAL */}
      {showBulkExportModal && (
        <BulkExportModal
          facilityId="FAC-001"
          onClose={() => setShowBulkExportModal(false)}
        />
      )}
    </div>
  );
};
