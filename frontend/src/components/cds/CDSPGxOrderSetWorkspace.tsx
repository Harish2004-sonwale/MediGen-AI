// ==============================================================================
// MediGen AI - Phase 9.0.26: Enterprise CDS, Pharmacogenomics & Order Sets Workspace
// ==============================================================================

import React, { useState, useEffect, useId } from 'react';
import { usePatient } from '../../context/PatientContext';
import { useAuth } from '../../context/AuthContext';
import { cdsPgxApi } from '../../api/client';
import {
  ClinicalOrderSet,
  PGxRuleDefinition,
  CDSEvaluationResponse,
  CDSPGxAlertCard,
  CDSRuleEvaluationAudit,
  OrderSetCategory,
} from '../../types';

export const CDSPGxOrderSetWorkspace: React.FC = () => {
  const { selectedPatient } = usePatient();
  const { user } = useAuth();

  const isClinician = user?.role === 'doctor' || user?.role === 'admin' || user?.role === 'healthcare_staff';

  const [activeTab, setActiveTab] = useState<'order_sets' | 'realtime_cds' | 'cpic_kb' | 'audits'>('order_sets');
  const [orderSets, setOrderSets] = useState<ClinicalOrderSet[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<OrderSetCategory | ''>('');
  const [selectedOrderSet, setSelectedOrderSet] = useState<ClinicalOrderSet | null>(null);
  const [selectedItemIds, setSelectedItemIds] = useState<string[]>([]);
  const [orderSetNotes, setOrderSetNotes] = useState<string>('');

  const [proposedDrugName, setProposedDrugName] = useState<string>('Clopidogrel 75mg daily');
  const [evaluationResult, setEvaluationResult] = useState<CDSEvaluationResponse | null>(null);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);

  const [overrideCard, setOverrideCard] = useState<CDSPGxAlertCard | null>(null);
  const [overrideReason, setOverrideReason] = useState<string>('');
  const [overrideMessage, setOverrideMessage] = useState<string | null>(null);

  const [rules, setRules] = useState<PGxRuleDefinition[]>([]);
  const [geneFilter, setGeneFilter] = useState<string>('');

  const [audits, setAudits] = useState<CDSRuleEvaluationAudit[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const categorySelectId = useId();
  const drugInputId = useId();
  const geneFilterId = useId();
  const notesTextareaId = useId();
  const overrideReasonId = useId();

  useEffect(() => {
    loadOrderSets();
    loadRules();
    if (selectedPatient) {
      loadAudits();
    }
  }, [selectedPatient, selectedCategory]);

  const loadOrderSets = async () => {
    try {
      setIsLoading(true);
      const res = await cdsPgxApi.listOrderSets({
        category: selectedCategory ? selectedCategory : undefined,
      });
      setOrderSets(res.order_sets || []);
      if (res.order_sets && res.order_sets.length > 0 && !selectedOrderSet) {
        handleSelectOrderSet(res.order_sets[0]);
      }
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err?.message || 'Failed to load clinical order sets.' });
    } finally {
      setIsLoading(false);
    }
  };

  const loadRules = async () => {
    try {
      const res = await cdsPgxApi.listRules();
      setRules(res.rules || []);
    } catch (err: any) {
      console.error('Failed to load CPIC rules:', err);
    }
  };

  const loadAudits = async () => {
    if (!selectedPatient) return;
    try {
      const res = await cdsPgxApi.listAudits(selectedPatient.patient_id);
      setAudits(res.audits || []);
    } catch (err: any) {
      console.error('Failed to load CDS audits:', err);
    }
  };

  const handleSelectOrderSet = (os: ClinicalOrderSet) => {
    setSelectedOrderSet(os);
    setSelectedItemIds(os.items ? os.items.map((i) => i.item_id) : []);
  };

  const toggleOrderItem = (itemId: string) => {
    if (selectedItemIds.includes(itemId)) {
      setSelectedItemIds(selectedItemIds.filter((id) => id !== itemId));
    } else {
      setSelectedItemIds([...selectedItemIds, itemId]);
    }
  };

  const handleExecuteOrderSet = async () => {
    if (!selectedPatient || !selectedOrderSet) return;
    try {
      setIsLoading(true);
      setStatusMessage(null);
      const res = await cdsPgxApi.executeOrderSet(selectedOrderSet.order_set_id, {
        patient_id: selectedPatient.patient_id,
        selected_item_ids: selectedItemIds,
        notes: orderSetNotes,
      });
      setStatusMessage({
        type: 'success',
        text: `Order Set Executed! Created ${res.executed_items_count} CPOE orders (Exec ID: ${res.execution_id}).`,
      });
      setOrderSetNotes('');
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err?.message || 'Failed to execute clinical order set.',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleEvaluateProposedMed = async () => {
    if (!selectedPatient || !proposedDrugName.trim()) return;
    try {
      setIsEvaluating(true);
      const res = await cdsPgxApi.evaluateCDS({
        patient_id: selectedPatient.patient_id,
        proposed_drug_name: proposedDrugName.trim(),
      });
      setEvaluationResult(res);
    } catch (err: any) {
      setStatusMessage({
        type: 'error',
        text: err?.message || 'Failed to evaluate CDS & PGx interactions.',
      });
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleRecordOverride = async () => {
    if (!selectedPatient || !overrideCard || !overrideReason.trim()) return;
    try {
      setIsLoading(true);
      const res = await cdsPgxApi.recordOverride({
        patient_id: selectedPatient.patient_id,
        rule_type: overrideCard.rule_type || 'pgx_interaction',
        severity: overrideCard.indicator,
        card_summary: overrideCard.summary,
        card_detail: overrideCard.detail || overrideCard.summary,
        override_reason: overrideReason.trim(),
      });
      setOverrideMessage(`Override recorded under Audit ID: ${res.audit_id}`);
      setOverrideReason('');
      setOverrideCard(null);
      loadAudits();
    } catch (err: any) {
      setOverrideMessage(`Failed to record override: ${err?.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredRules = geneFilter
    ? rules.filter(
        (r) =>
          r.gene_symbol.toLowerCase().includes(geneFilter.toLowerCase()) ||
          r.drug_name.toLowerCase().includes(geneFilter.toLowerCase())
      )
    : rules;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', padding: '16px', gap: '16px', overflowY: 'auto' }}>
      {/* Workspace Header & Patient Context */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Clinical Decision Support & Pharmacogenomics (PGx) Workspace
          </h2>
          <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            CPIC Level A/B evidence guidelines, real-time drug-gene interaction checks, and CPOE multidisciplinary order set automation.
          </p>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', background: 'var(--bg-secondary)', padding: '4px', borderRadius: '8px', gap: '4px' }}>
          <button
            id="tab-btn-order-sets"
            onClick={() => setActiveTab('order_sets')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              background: activeTab === 'order_sets' ? 'var(--primary-color, #2563eb)' : 'transparent',
              color: activeTab === 'order_sets' ? '#fff' : 'var(--text-secondary)',
            }}
          >
            📋 Clinical Order Sets
          </button>
          <button
            id="tab-btn-realtime-cds"
            onClick={() => setActiveTab('realtime_cds')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              background: activeTab === 'realtime_cds' ? 'var(--primary-color, #2563eb)' : 'transparent',
              color: activeTab === 'realtime_cds' ? '#fff' : 'var(--text-secondary)',
            }}
          >
            ⚡ Real-Time CDS & PGx Check
          </button>
          <button
            id="tab-btn-cpic-kb"
            onClick={() => setActiveTab('cpic_kb')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              background: activeTab === 'cpic_kb' ? 'var(--primary-color, #2563eb)' : 'transparent',
              color: activeTab === 'cpic_kb' ? '#fff' : 'var(--text-secondary)',
            }}
          >
            🧬 CPIC Knowledge Base ({rules.length})
          </button>
          <button
            id="tab-btn-audits"
            onClick={() => setActiveTab('audits')}
            style={{
              padding: '6px 14px',
              borderRadius: '6px',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.85rem',
              background: activeTab === 'audits' ? 'var(--primary-color, #2563eb)' : 'transparent',
              color: activeTab === 'audits' ? '#fff' : 'var(--text-secondary)',
            }}
          >
            🛡️ Override Audits ({audits.length})
          </button>
        </div>
      </div>

      {statusMessage && (
        <div
          style={{
            padding: '10px 16px',
            borderRadius: '8px',
            fontSize: '0.9rem',
            background: statusMessage.type === 'success' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            border: `1px solid ${statusMessage.type === 'success' ? '#22c55e' : '#ef4444'}`,
            color: statusMessage.type === 'success' ? '#16a34a' : '#dc2626',
          }}
        >
          {statusMessage.text}
        </div>
      )}

      {/* Patient Banner Alert */}
      {!selectedPatient && (
        <div style={{ padding: '12px 16px', background: 'rgba(234, 179, 8, 0.15)', border: '1px solid #eab308', borderRadius: '8px', color: '#ca8a04', fontSize: '0.9rem' }}>
          ⚠️ Please select a patient from the directory to evaluate individualized genomic profiles, execute order sets, or log clinical overrides.
        </div>
      )}

      {/* TAB 1: Multidisciplinary Clinical Order Sets */}
      {activeTab === 'order_sets' && (
        <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '16px', height: '100%', minHeight: '520px' }}>
          {/* Left Column: Order Sets Catalog */}
          <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '12px', display: 'flex', flexDirection: 'column', gap: '12px', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Order Sets Catalog</span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{orderSets.length} Sets</span>
            </div>

            <div>
              <label htmlFor={categorySelectId} style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '4px' }}>
                Filter by Clinical Category:
              </label>
              <select
                id={categorySelectId}
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value as OrderSetCategory | '')}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  background: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  fontSize: '0.85rem',
                }}
              >
                <option value="">All Categories</option>
                <option value="emergency_trauma">Emergency & Trauma</option>
                <option value="critical_care">Critical Care & Sepsis</option>
                <option value="inpatient_admission">Inpatient Admission</option>
                <option value="cardiovascular">Cardiovascular</option>
                <option value="oncology_precision">Oncology Precision</option>
                <option value="antimicrobial_stewardship">Antimicrobial Stewardship</option>
                <option value="surgical_perioperative">Surgical Perioperative</option>
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflowY: 'auto', flex: 1 }}>
              {orderSets.map((os) => {
                const isSelected = selectedOrderSet?.order_set_id === os.order_set_id;
                return (
                  <div
                    key={os.order_set_id}
                    id={`orderset-item-${os.order_set_id}`}
                    onClick={() => handleSelectOrderSet(os)}
                    style={{
                      padding: '12px',
                      borderRadius: '8px',
                      border: `1px solid ${isSelected ? 'var(--primary-color, #2563eb)' : 'var(--border-color)'}`,
                      background: isSelected ? 'rgba(37, 99, 235, 0.08)' : 'var(--bg-primary)',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 700, fontSize: '0.9rem', color: isSelected ? 'var(--primary-color, #2563eb)' : 'var(--text-primary)' }}>
                        {os.title}
                      </span>
                      <span style={{ fontSize: '0.75rem', padding: '2px 6px', background: 'var(--bg-secondary)', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                        v{os.version}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                      {os.category.replace('_', ' ').toUpperCase()} • {os.items ? os.items.length : 0} items
                    </div>
                    {os.target_icd10 && (
                      <span style={{ fontSize: '0.75rem', color: '#0284c7', background: 'rgba(2, 132, 199, 0.1)', padding: '2px 6px', borderRadius: '4px' }}>
                        ICD-10: {os.target_icd10}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Order Set Item Checklist & Execution Panel */}
          {selectedOrderSet ? (
            <div style={{ background: 'var(--bg-secondary)', padding: '20px', borderRadius: '12px', display: 'flex', flexDirection: 'column', gap: '16px', border: '1px solid var(--border-color)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700 }}>{selectedOrderSet.title}</h3>
                  <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                    {selectedOrderSet.description || 'Standardized clinical order bundle with protocolized interventions.'}
                  </p>
                </div>
                <span style={{ padding: '4px 10px', background: 'rgba(37, 99, 235, 0.1)', color: '#2563eb', borderRadius: '6px', fontWeight: 600, fontSize: '0.8rem' }}>
                  Code: {selectedOrderSet.code}
                </span>
              </div>

              {/* Items Checklist */}
              <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                  Selected Orders for Execution ({selectedItemIds.length} / {selectedOrderSet.items?.length || 0}):
                </div>
                {selectedOrderSet.items?.map((item) => {
                  const isChecked = selectedItemIds.includes(item.item_id);
                  return (
                    <div
                      key={item.item_id}
                      style={{
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '12px',
                        padding: '12px',
                        borderRadius: '8px',
                        background: 'var(--bg-primary)',
                        border: '1px solid var(--border-color)',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleOrderItem(item.item_id)}
                        style={{ marginTop: '3px', cursor: 'pointer' }}
                      />
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                          <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>{item.name}</span>
                          <span
                            style={{
                              fontSize: '0.75rem',
                              padding: '2px 6px',
                              borderRadius: '4px',
                              background:
                                item.item_type === 'medication'
                                  ? 'rgba(168, 85, 247, 0.1)'
                                  : item.item_type === 'laboratory'
                                  ? 'rgba(14, 165, 233, 0.1)'
                                  : 'rgba(234, 179, 8, 0.1)',
                              color:
                                item.item_type === 'medication'
                                  ? '#9333ea'
                                  : item.item_type === 'laboratory'
                                  ? '#0284c7'
                                  : '#ca8a04',
                              fontWeight: 600,
                            }}
                          >
                            {item.item_type.toUpperCase()}
                          </span>
                          {item.default_frequency === 'STAT' && (
                            <span style={{ fontSize: '0.75rem', padding: '2px 6px', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.15)', color: '#dc2626', fontWeight: 700 }}>
                              STAT
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                          {item.default_dosage && `Dosage: ${item.default_dosage} | `}
                          {item.default_route && `Route: ${item.default_route} | `}
                          {item.default_frequency && `Freq: ${item.default_frequency}`}
                        </div>
                        {item.clinical_instructions && (
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted, #64748b)', marginTop: '4px', fontStyle: 'italic' }}>
                            Instructions: {item.clinical_instructions}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Notes & Execution Controls */}
              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <div>
                  <label htmlFor={notesTextareaId} style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', display: 'block', marginBottom: '4px' }}>
                    Clinical Justification & Triage Notes:
                  </label>
                  <textarea
                    id={notesTextareaId}
                    rows={2}
                    value={orderSetNotes}
                    onChange={(e) => setOrderSetNotes(e.target.value)}
                    placeholder="Enter clinical indication or ED triage justification..."
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      fontSize: '0.85rem',
                      fontFamily: 'inherit',
                    }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                  <button
                    id="btn-execute-order-set"
                    onClick={handleExecuteOrderSet}
                    disabled={!selectedPatient || selectedItemIds.length === 0 || isLoading || !isClinician}
                    style={{
                      padding: '10px 20px',
                      borderRadius: '8px',
                      border: 'none',
                      cursor: selectedPatient && isClinician && selectedItemIds.length > 0 ? 'pointer' : 'not-allowed',
                      fontWeight: 700,
                      fontSize: '0.9rem',
                      background: 'var(--primary-color, #2563eb)',
                      color: '#fff',
                      opacity: selectedPatient && isClinician && selectedItemIds.length > 0 ? 1 : 0.6,
                    }}
                  >
                    ⚡ Execute Order Set ({selectedItemIds.length} Orders)
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
              Select an order set to view checklist and execute.
            </div>
          )}
        </div>
      )}

      {/* TAB 2: Real-Time CDS & PGx Pre-flight Check */}
      {activeTab === 'realtime_cds' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ background: 'var(--bg-secondary)', padding: '20px', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
            <h3 style={{ margin: '0 0 12px 0', fontSize: '1.1rem', fontWeight: 700 }}>
              Pre-Flight Medication Order CDS & PGx Evaluation
            </h3>
            <p style={{ margin: '0 0 16px 0', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              Simulates real-time clinical order-select triggers against patient genomic biomarkers (e.g., CYP2D6, CYP2C19, DPYD, TPMT, HLA-B*5701, SLCO1B1).
            </p>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
              <div style={{ flex: 1, minWidth: '280px' }}>
                <label htmlFor={drugInputId} style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                  Proposed Medication & Dosage:
                </label>
                <input
                  id={drugInputId}
                  type="text"
                  value={proposedDrugName}
                  onChange={(e) => setProposedDrugName(e.target.value)}
                  placeholder="e.g. Clopidogrel 75mg daily, Codeine 30mg, Capecitabine 1000mg/m2"
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    background: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.9rem',
                  }}
                />
              </div>

              <div style={{ alignSelf: 'flex-end' }}>
                <button
                  id="btn-evaluate-cds"
                  onClick={handleEvaluateProposedMed}
                  disabled={!selectedPatient || isEvaluating}
                  style={{
                    padding: '9px 18px',
                    borderRadius: '6px',
                    border: 'none',
                    background: '#2563eb',
                    color: '#fff',
                    fontWeight: 700,
                    fontSize: '0.85rem',
                    cursor: selectedPatient ? 'pointer' : 'not-allowed',
                  }}
                >
                  {isEvaluating ? 'Evaluating...' : '🔍 Evaluate CDS & PGx'}
                </button>
              </div>
            </div>
          </div>

          {/* Evaluation Results */}
          {evaluationResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: 700, fontSize: '1rem' }}>
                  CDS Evaluation Output ({evaluationResult.cards.length} Cards)
                </span>
                <span
                  style={{
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontWeight: 700,
                    fontSize: '0.8rem',
                    background:
                      evaluationResult.highest_severity === 'critical'
                        ? 'rgba(239, 68, 68, 0.15)'
                        : evaluationResult.highest_severity === 'warning'
                        ? 'rgba(234, 179, 8, 0.15)'
                        : 'rgba(34, 197, 94, 0.15)',
                    color:
                      evaluationResult.highest_severity === 'critical'
                        ? '#dc2626'
                        : evaluationResult.highest_severity === 'warning'
                        ? '#ca8a04'
                        : '#16a34a',
                  }}
                >
                  Status: {evaluationResult.highest_severity.toUpperCase()}
                </span>
              </div>

              {/* Patient Detected Genotype Summary */}
              {Object.keys(evaluationResult.patient_genotype_summary || {}).length > 0 && (
                <div style={{ background: 'var(--bg-secondary)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>🧬 Patient Genotype Profile:</span>
                  {Object.entries(evaluationResult.patient_genotype_summary).map(([gene, pheno]) => (
                    <span key={gene} style={{ background: 'var(--bg-primary)', padding: '3px 8px', borderRadius: '4px', fontSize: '0.8rem', border: '1px solid var(--border-color)' }}>
                      <strong>{gene}:</strong> {pheno}
                    </span>
                  ))}
                </div>
              )}

              {/* CDS Alert Cards */}
              {evaluationResult.cards.length === 0 ? (
                <div style={{ padding: '24px', background: 'rgba(34, 197, 94, 0.1)', border: '1px solid #22c55e', borderRadius: '8px', color: '#15803d', textAlign: 'center', fontWeight: 600 }}>
                  ✅ No Contraindications or Pharmacogenomic Drug-Gene Alerts Detected for "{proposedDrugName}". Safe to proceed.
                </div>
              ) : (
                evaluationResult.cards.map((card) => (
                  <div
                    key={card.card_id}
                    id={`cds-card-${card.card_id}`}
                    style={{
                      background: 'var(--bg-secondary)',
                      padding: '16px',
                      borderRadius: '10px',
                      borderLeft: `5px solid ${card.indicator === 'critical' ? '#dc2626' : '#eab308'}`,
                      border: '1px solid var(--border-color)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '1.2rem' }}>{card.indicator === 'critical' ? '🛑' : '⚠️'}</span>
                        <span style={{ fontWeight: 700, fontSize: '0.95rem', color: card.indicator === 'critical' ? '#dc2626' : '#ca8a04' }}>
                          {card.summary}
                        </span>
                      </div>
                      {card.cpic_level && (
                        <span style={{ background: '#7c3aed', color: '#fff', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700 }}>
                          CPIC Level {card.cpic_level}
                        </span>
                      )}
                    </div>

                    <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                      {card.detail}
                    </p>

                    {card.alternative_drugs && card.alternative_drugs.length > 0 && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#16a34a' }}>💡 Recommended Alternatives:</span>
                        {card.alternative_drugs.map((alt) => (
                          <span key={alt} style={{ background: 'rgba(22, 163, 74, 0.1)', color: '#16a34a', padding: '2px 8px', borderRadius: '4px', fontSize: '0.8rem', fontWeight: 600 }}>
                            {alt}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Override Action */}
                    {isClinician && (
                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
                        <button
                          id={`btn-override-${card.card_id}`}
                          onClick={() => setOverrideCard(card)}
                          style={{
                            padding: '6px 12px',
                            borderRadius: '6px',
                            border: '1px solid #dc2626',
                            background: 'transparent',
                            color: '#dc2626',
                            fontWeight: 600,
                            fontSize: '0.8rem',
                            cursor: 'pointer',
                          }}
                        >
                          ✍️ Override with Justification
                        </button>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* Override Modal */}
          {overrideCard && (
            <div
              style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(0,0,0,0.6)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 1000,
              }}
            >
              <div
                style={{
                  background: 'var(--bg-primary)',
                  padding: '24px',
                  borderRadius: '12px',
                  maxWidth: '540px',
                  width: '90%',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px',
                }}
              >
                <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 700, color: '#dc2626' }}>
                  Clinician Alert Override & Audit Justification
                </h3>
                <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  You are overriding: <strong>{overrideCard.summary}</strong>. An immutable audit record with your justification will be recorded in compliance with 21 CFR Part 11 and HIPAA.
                </p>

                <div>
                  <label htmlFor={overrideReasonId} style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '6px' }}>
                    Clinical Override Justification (Mandatory):
                  </label>
                  <textarea
                    id={overrideReasonId}
                    rows={3}
                    value={overrideReason}
                    onChange={(e) => setOverrideReason(e.target.value)}
                    placeholder="Enter detailed clinical rationale (e.g. patient previously tolerated therapy; intensive monitoring protocol active)..."
                    style={{
                      width: '100%',
                      padding: '8px 12px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)',
                      fontSize: '0.85rem',
                      fontFamily: 'inherit',
                    }}
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                  <button
                    onClick={() => {
                      setOverrideCard(null);
                      setOverrideReason('');
                    }}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-color)',
                      background: 'transparent',
                      color: 'var(--text-secondary)',
                      cursor: 'pointer',
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    id="btn-confirm-override"
                    onClick={handleRecordOverride}
                    disabled={overrideReason.trim().length < 5 || isLoading}
                    style={{
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: 'none',
                      background: '#dc2626',
                      color: '#fff',
                      fontWeight: 700,
                      cursor: overrideReason.trim().length >= 5 ? 'pointer' : 'not-allowed',
                      opacity: overrideReason.trim().length >= 5 ? 1 : 0.6,
                    }}
                  >
                    Confirm Override & Sign
                  </button>
                </div>
              </div>
            </div>
          )}

          {overrideMessage && (
            <div style={{ padding: '10px 16px', background: 'rgba(34, 197, 94, 0.15)', border: '1px solid #22c55e', borderRadius: '8px', color: '#16a34a', fontSize: '0.9rem' }}>
              {overrideMessage}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: CPIC Pharmacogenomics Knowledge Base */}
      {activeTab === 'cpic_kb' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>CPIC Clinical Pharmacogenetics Guidelines Knowledge Base</span>
            <input
              id={geneFilterId}
              type="text"
              value={geneFilter}
              onChange={(e) => setGeneFilter(e.target.value)}
              placeholder="Search gene (CYP2D6, DPYD) or drug..."
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                fontSize: '0.85rem',
                minWidth: '260px',
              }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '16px' }}>
            {filteredRules.map((rule) => (
              <div
                key={rule.rule_id}
                style={{
                  background: 'var(--bg-secondary)',
                  padding: '16px',
                  borderRadius: '10px',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 700, fontSize: '1rem', color: '#2563eb' }}>
                    {rule.gene_symbol} • {rule.phenotype}
                  </span>
                  <span style={{ background: '#7c3aed', color: '#fff', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700 }}>
                    CPIC {rule.cpic_level}
                  </span>
                </div>

                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Medication: {rule.drug_name} ({rule.drug_code})
                </div>

                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  <strong>Implication:</strong> {rule.clinical_implication}
                </div>

                <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)', background: 'var(--bg-primary)', padding: '8px', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                  <strong>Recommendation:</strong> {rule.recommendation_text}
                </div>

                {rule.alternative_drugs && rule.alternative_drugs.length > 0 && (
                  <div style={{ fontSize: '0.75rem', color: '#16a34a' }}>
                    <strong>Alternatives:</strong> {rule.alternative_drugs.join(', ')}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: CDS Override Audits */}
      {activeTab === 'audits' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>
            Patient CDS & PGx Alert Override Audit Trail ({audits.length} Records)
          </span>

          {audits.length === 0 ? (
            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
              No clinician CDS alert overrides recorded for the current patient context.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {audits.map((audit) => (
                <div
                  key={audit.audit_id}
                  style={{
                    background: 'var(--bg-secondary)',
                    padding: '14px',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.9rem', color: '#dc2626' }}>
                      🛑 {audit.card_summary}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      Audit ID: {audit.audit_id} • {new Date(audit.created_at).toLocaleString()}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                    <strong>Clinician Override Justification:</strong> {audit.override_reason}
                  </div>

                  <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    Trigger: {audit.trigger_event} • Severity: {audit.severity} • Overridden by Provider #{audit.clinician_id}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
