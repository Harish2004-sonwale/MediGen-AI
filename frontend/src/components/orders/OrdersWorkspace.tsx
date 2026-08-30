import React, { useEffect, useState } from 'react';
import {
  AbnormalFlag,
  ClinicalOrder,
  DiagnosticResult,
  OrderBundleItem,
  OrderCategory,
  OrderPriority,
  OrderStatus,
  Patient,
} from '../../types';
import { ordersApi, patientsApi } from '../../api/client';

export const OrdersWorkspace: React.FC = () => {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);

  const [activeTab, setActiveTab] = useState<'orders' | 'results'>('orders');
  const [orders, setOrders] = useState<ClinicalOrder[]>([]);
  const [results, setResults] = useState<DiagnosticResult[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [flagFilter, setFlagFilter] = useState<string>('all');

  // Modals
  const [showPlaceOrderModal, setShowPlaceOrderModal] = useState<boolean>(false);
  const [showBundleModal, setShowBundleModal] = useState<boolean>(false);
  const [showRecordResultModal, setShowRecordResultModal] = useState<boolean>(false);
  const [showSignoffModal, setShowSignoffModal] = useState<boolean>(false);
  const [selectedOrderForResult, setSelectedOrderForResult] = useState<ClinicalOrder | null>(null);
  const [selectedResultForSignoff, setSelectedResultForSignoff] = useState<DiagnosticResult | null>(null);

  // Place Order Form
  const [orderCategory, setOrderCategory] = useState<OrderCategory>('laboratory');
  const [orderType, setOrderType] = useState<string>('complete_blood_count');
  const [orderPriority, setOrderPriority] = useState<OrderPriority>('routine');
  const [clinicalIndication, setClinicalIndication] = useState<string>('');
  const [specimenSource, setSpecimenSource] = useState<string>('Venous blood');

  // Bundle Synthesis Form
  const [bundleProtocol, setBundleProtocol] = useState<string>('chest_pain_acs');
  const [customBundleIndication, setCustomBundleIndication] = useState<string>('');
  const [suggestedBundleName, setSuggestedBundleName] = useState<string>('');
  const [suggestedBundleRationale, setSuggestedBundleRationale] = useState<string>('');
  const [suggestedBundleItems, setSuggestedBundleItems] = useState<OrderBundleItem[]>([]);
  const [bundleSafetyWarnings, setBundleSafetyWarnings] = useState<string[]>([]);
  const [bundleSynthesizing, setBundleSynthesizing] = useState<boolean>(false);

  // Record Result Form
  const [resultTestName, setResultTestName] = useState<string>('');
  const [resultLoinc, setResultLoinc] = useState<string>('');
  const [resultNumericValue, setResultNumericValue] = useState<string>('');
  const [resultUnit, setResultUnit] = useState<string>('');
  const [resultRefLow, setResultRefLow] = useState<string>('');
  const [resultRefHigh, setResultRefHigh] = useState<string>('');
  const [resultFindings, setResultFindings] = useState<string>('');

  // Signoff Form
  const [signoffNotes, setSignoffNotes] = useState<string>('');

  // Load patients
  useEffect(() => {
    loadPatients();
  }, []);

  // Reload orders & results when selected patient changes
  useEffect(() => {
    if (selectedPatientId) {
      loadData(selectedPatientId);
    }
  }, [selectedPatientId]);

  const loadPatients = async () => {
    try {
      setLoading(true);
      const items = await patientsApi.list();
      setPatients(items);
      if (items.length > 0 && !selectedPatientId) {
        setSelectedPatientId(items[0].patient_id);
        setSelectedPatient(items[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load patients list.');
    } finally {
      setLoading(false);
    }
  };


  const loadData = async (patientId: string) => {
    try {
      setLoading(true);
      setError(null);
      const found = patients.find((p) => p.patient_id === patientId);
      if (found) setSelectedPatient(found);

      const [ordersRes, resultsRes] = await Promise.all([
        ordersApi.listOrders(patientId),
        ordersApi.listResults(patientId),
      ]);
      setOrders(ordersRes.items);
      setResults(resultsRes.items);
    } catch (err: any) {
      setError(err.message || 'Failed to load clinical orders or results.');
    } finally {
      setLoading(false);
    }
  };

  const handlePlaceOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatientId || !clinicalIndication.trim()) return;

    try {
      setLoading(true);
      setError(null);
      const newOrder = await ordersApi.placeOrder(selectedPatientId, {
        order_category: orderCategory,
        order_type: orderType,
        priority: orderPriority,
        clinical_indication: clinicalIndication,
        specimen_source: specimenSource,
      });

      setSuccessMessage(`Clinical order ${newOrder.order_id} successfully placed.`);
      setShowPlaceOrderModal(false);
      setClinicalIndication('');
      await loadData(selectedPatientId);
    } catch (err: any) {
      setError(err.message || 'Failed to place clinical order.');
    } finally {
      setLoading(false);
    }
  };

  const handleFetchBundleSuggestion = async () => {
    if (!selectedPatientId) return;
    try {
      setBundleSynthesizing(true);
      setError(null);
      const bundle = await ordersApi.suggestBundle(selectedPatientId, {
        clinical_protocol: bundleProtocol,
        custom_indication: customBundleIndication || undefined,
      });

      setSuggestedBundleName(bundle.protocol_name);
      setSuggestedBundleRationale(bundle.clinical_rationale);
      setSuggestedBundleItems(bundle.suggested_orders);
      setBundleSafetyWarnings(bundle.pre_order_safety_warnings);
    } catch (err: any) {
      setError(err.message || 'Failed to generate order bundle.');
    } finally {
      setBundleSynthesizing(false);
    }
  };

  const handleApplyBundleOrders = async () => {
    if (!selectedPatientId || suggestedBundleItems.length === 0) return;
    try {
      setLoading(true);
      setError(null);

      for (const item of suggestedBundleItems) {
        await ordersApi.placeOrder(selectedPatientId, {
          order_category: item.order_category,
          order_type: item.order_type,
          priority: item.priority,
          clinical_indication: item.clinical_indication,
          specimen_source: item.specimen_source,
        });
      }

      setSuccessMessage(`Successfully placed ${suggestedBundleItems.length} orders from bundle.`);
      setShowBundleModal(false);
      setSuggestedBundleItems([]);
      await loadData(selectedPatientId);
    } catch (err: any) {
      setError(err.message || 'Failed to apply order bundle.');
    } finally {
      setLoading(false);
    }
  };

  const handleRecordResult = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrderForResult || !resultTestName.trim() || !resultFindings.trim()) return;

    try {
      setLoading(true);
      setError(null);
      const res = await ordersApi.recordResult(selectedOrderForResult.order_id, {
        test_name: resultTestName,
        test_code_loinc: resultLoinc || undefined,
        findings_summary: resultFindings,
        numeric_value: resultNumericValue ? parseFloat(resultNumericValue) : undefined,
        unit_of_measure: resultUnit || undefined,
        reference_range_low: resultRefLow ? parseFloat(resultRefLow) : undefined,
        reference_range_high: resultRefHigh ? parseFloat(resultRefHigh) : undefined,
      });

      setSuccessMessage(`Result ${res.result_id} recorded (${res.abnormal_flag.toUpperCase()}).`);
      setShowRecordResultModal(false);
      setSelectedOrderForResult(null);
      setResultTestName('');
      setResultNumericValue('');
      setResultUnit('');
      setResultFindings('');
      await loadData(selectedPatientId);
    } catch (err: any) {
      setError(err.message || 'Failed to record diagnostic result.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignoffResult = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedResultForSignoff) return;

    try {
      setLoading(true);
      setError(null);
      await ordersApi.reviewResult(selectedResultForSignoff.result_id, {
        review_notes: signoffNotes || undefined,
      });

      setSuccessMessage(`Diagnostic result ${selectedResultForSignoff.result_id} signed off.`);
      setShowSignoffModal(false);
      setSelectedResultForSignoff(null);
      setSignoffNotes('');
      await loadData(selectedPatientId);
    } catch (err: any) {
      setError(err.message || 'Failed to sign off diagnostic result.');
    } finally {
      setLoading(false);
    }
  };

  // Filtered orders and results
  const filteredOrders = orders.filter((o) => {
    const matchesStatus = statusFilter === 'all' || o.status === statusFilter;
    const matchesCat = categoryFilter === 'all' || o.order_category === categoryFilter;
    return matchesStatus && matchesCat;
  });

  const filteredResults = results.filter((r) => {
    return flagFilter === 'all' || r.abnormal_flag === flagFilter;
  });

  const getPriorityBadgeClass = (p: OrderPriority) => {
    switch (p) {
      case 'stat':
        return 'bg-red-500/20 text-red-400 border-red-500/40 font-bold animate-pulse';
      case 'urgent':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      default:
        return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
    }
  };

  const getAbnormalBadgeClass = (f: AbnormalFlag) => {
    switch (f) {
      case 'panic_critical':
        return 'bg-red-600 text-white font-bold animate-pulse border-red-400';
      case 'abnormal_high':
      case 'abnormal_low':
        return 'bg-amber-500/30 text-amber-300 border-amber-500/50 font-semibold';
      default:
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
    }
  };

  const getCategoryIcon = (c: OrderCategory) => {
    switch (c) {
      case 'laboratory':
        return '🧪';
      case 'imaging':
        return '🩻';
      case 'medication':
        return '💊';
      case 'nursing':
        return '🩺';
      case 'consultation':
        return '👨‍⚕️';
      default:
        return '📦';
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header Banner */}
      <div className="bg-slate-900/80 backdrop-blur-md p-6 rounded-2xl border border-slate-800 shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">📦</span>
            <h1 className="text-2xl font-bold text-slate-100">
              Clinical Orders (CPOE) & Closed-Loop Diagnostics
            </h1>
          </div>
          <p className="text-sm text-slate-400">
            Phase 9.0.13 — Computerized order entry, duplicate checking, AI order set bundles & panic result tracking.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedPatientId}
            onChange={(e) => setSelectedPatientId(e.target.value)}
            className="bg-slate-800 text-slate-100 border border-slate-700 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            {patients.map((p) => (
              <option key={p.patient_id} value={p.patient_id}>
                {p.first_name} {p.last_name} ({p.patient_id})
              </option>
            ))}
          </select>

          <button
            onClick={() => {
              setShowBundleModal(true);
              handleFetchBundleSuggestion();
            }}
            className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-sm font-semibold px-4 py-2 rounded-xl transition-all shadow-lg flex items-center gap-1.5"
          >
            <span>✨</span> AI Order Bundle
          </button>

          <button
            onClick={() => setShowPlaceOrderModal(true)}
            className="bg-gradient-to-r from-sky-600 to-cyan-600 hover:from-sky-500 hover:to-cyan-500 text-white text-sm font-semibold px-4 py-2 rounded-xl transition-all shadow-lg flex items-center gap-1.5"
          >
            <span>➕</span> Place Order
          </button>
        </div>
      </div>

      {/* Patient Summary Card */}
      {selectedPatient && (
        <div className="bg-slate-800/40 p-4 rounded-xl border border-slate-700/60 flex flex-wrap gap-6 text-sm text-slate-300">
          <div>
            <span className="text-slate-500 block text-xs">Patient Name</span>
            <span className="font-semibold text-slate-100">
              {selectedPatient.first_name} {selectedPatient.last_name}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-xs">Gender / DOB</span>
            <span>{selectedPatient.gender.toUpperCase()} / {selectedPatient.date_of_birth}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-xs">Status</span>
            <span className="inline-block px-2 py-0.5 rounded text-xs bg-emerald-500/20 text-emerald-300 font-medium">
              {selectedPatient.is_active ? 'ACTIVE' : 'INACTIVE'}
            </span>
          </div>

          <div>
            <span className="text-slate-500 block text-xs">Total Orders / Results</span>
            <span className="font-semibold text-sky-400">{orders.length} orders</span> /{' '}
            <span className="font-semibold text-amber-400">{results.length} results</span>
          </div>
        </div>
      )}

      {/* Feedback Alerts */}
      {error && (
        <div className="p-4 rounded-xl bg-red-900/30 border border-red-800 text-red-300 text-sm flex items-center justify-between">
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200">✕</button>
        </div>
      )}
      {successMessage && (
        <div className="p-4 rounded-xl bg-emerald-900/30 border border-emerald-800 text-emerald-300 text-sm flex items-center justify-between">
          <span>✅ {successMessage}</span>
          <button onClick={() => setSuccessMessage(null)} className="text-emerald-400 hover:text-emerald-200">✕</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-4">
        <button
          onClick={() => setActiveTab('orders')}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'orders'
              ? 'border-sky-500 text-sky-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>📋</span> Clinical Orders (CPOE) ({filteredOrders.length})
        </button>

        <button
          onClick={() => setActiveTab('results')}
          className={`pb-3 text-sm font-semibold flex items-center gap-2 border-b-2 transition-all ${
            activeTab === 'results'
              ? 'border-amber-500 text-amber-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>🔬</span> Diagnostic Results & Panic Lab Feed ({filteredResults.length})
        </button>
      </div>

      {/* =========================================================================
          TAB 1: CLINICAL ORDERS (CPOE)
      ========================================================================== */}
      {activeTab === 'orders' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-wrap gap-4 items-center bg-slate-900/50 p-3 rounded-xl border border-slate-800 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Category:</span>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="bg-slate-800 text-slate-200 border border-slate-700 rounded px-2.5 py-1 text-xs"
              >
                <option value="all">All Categories</option>
                <option value="laboratory">Laboratory 🧪</option>
                <option value="imaging">Imaging 🩻</option>
                <option value="medication">Medication 💊</option>
                <option value="nursing">Nursing 🩺</option>
                <option value="consultation">Consultation 👨‍⚕️</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-slate-400">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-800 text-slate-200 border border-slate-700 rounded px-2.5 py-1 text-xs"
              >
                <option value="all">All Statuses</option>
                <option value="draft">Draft</option>
                <option value="placed">Placed / Active</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>

          {/* Orders Grid */}
          {loading && orders.length === 0 ? (
            <div className="p-12 text-center text-slate-400 text-sm">Loading clinical orders...</div>
          ) : filteredOrders.length === 0 ? (
            <div className="p-12 text-center text-slate-500 border border-dashed border-slate-800 rounded-2xl">
              No clinical orders found matching criteria. Click <strong>Place Order</strong> or <strong>AI Order Bundle</strong> above.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredOrders.map((ord) => (
                <div
                  key={ord.order_id}
                  className="bg-slate-900/60 p-5 rounded-2xl border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xl">{getCategoryIcon(ord.order_category)}</span>
                        <div>
                          <h3 className="font-semibold text-slate-100 text-sm">
                            {ord.order_type.replace(/_/g, ' ').toUpperCase()}
                          </h3>
                          <span className="text-xs font-mono text-slate-500">{ord.order_id}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full border ${getPriorityBadgeClass(
                            ord.priority
                          )}`}
                        >
                          {ord.priority.toUpperCase()}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                          {ord.status.toUpperCase()}
                        </span>
                      </div>
                    </div>

                    <div className="bg-slate-800/50 p-2.5 rounded-lg text-xs space-y-1">
                      <p className="text-slate-300">
                        <strong className="text-slate-400">Indication:</strong> {ord.clinical_indication}
                      </p>
                      {ord.specimen_source && (
                        <p className="text-slate-400 text-[11px]">
                          <strong>Specimen:</strong> {ord.specimen_source}
                        </p>
                      )}
                    </div>

                    {/* Safety Warnings */}
                    {ord.ai_safety_flags_json && ord.ai_safety_flags_json.length > 0 && (
                      <div className="space-y-1">
                        {ord.ai_safety_flags_json.map((flag, idx) => (
                          <div
                            key={idx}
                            className="bg-amber-950/30 border border-amber-700/50 p-2 rounded text-xs text-amber-300 flex items-start gap-1.5"
                          >
                            <span>⚠️</span>
                            <div>
                              <strong className="font-semibold">{flag.code}:</strong> {flag.message}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
                    <span>Placed: {new Date(ord.created_at).toLocaleDateString()}</span>
                    {ord.status !== 'completed' && (
                      <button
                        onClick={() => {
                          setSelectedOrderForResult(ord);
                          setResultTestName(ord.order_type.replace(/_/g, ' ').toUpperCase());
                          setShowRecordResultModal(true);
                        }}
                        className="text-xs bg-sky-600/20 hover:bg-sky-600/30 text-sky-300 px-2.5 py-1 rounded border border-sky-500/30 transition-all font-medium"
                      >
                        Ingest Result 🔬
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          TAB 2: DIAGNOSTIC RESULTS & PANIC LAB FEED
      ========================================================================== */}
      {activeTab === 'results' && (
        <div className="space-y-4">
          {/* Filter Bar */}
          <div className="flex flex-wrap gap-4 items-center bg-slate-900/50 p-3 rounded-xl border border-slate-800 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Abnormal / Panic Flag:</span>
              <select
                value={flagFilter}
                onChange={(e) => setFlagFilter(e.target.value)}
                className="bg-slate-800 text-slate-200 border border-slate-700 rounded px-2.5 py-1 text-xs"
              >
                <option value="all">All Results</option>
                <option value="panic_critical">🚨 Panic Critical Only</option>
                <option value="abnormal_high">Abnormal High ⬆️</option>
                <option value="abnormal_low">Abnormal Low ⬇️</option>
                <option value="normal">Normal ✅</option>
              </select>
            </div>
          </div>

          {/* Results List */}
          {loading && results.length === 0 ? (
            <div className="p-12 text-center text-slate-400 text-sm">Loading diagnostic results...</div>
          ) : filteredResults.length === 0 ? (
            <div className="p-12 text-center text-slate-500 border border-dashed border-slate-800 rounded-2xl">
              No diagnostic test results recorded for this patient.
            </div>
          ) : (
            <div className="space-y-3">
              {filteredResults.map((res) => (
                <div
                  key={res.result_id}
                  className={`p-4 rounded-xl border transition-all ${
                    res.abnormal_flag === 'panic_critical'
                      ? 'bg-red-950/20 border-red-600/60 shadow-lg shadow-red-950/50'
                      : 'bg-slate-900/60 border-slate-800'
                  }`}
                >
                  <div className="flex flex-col md:flex-row justify-between md:items-center gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded border uppercase ${getAbnormalBadgeClass(
                            res.abnormal_flag
                          )}`}
                        >
                          {res.abnormal_flag.replace('_', ' ')}
                        </span>
                        <h4 className="font-semibold text-slate-100 text-sm">{res.test_name}</h4>
                        {res.test_code_loinc && (
                          <span className="text-xs text-slate-500 font-mono">LOINC: {res.test_code_loinc}</span>
                        )}
                      </div>

                      <p className="text-xs text-slate-300">{res.findings_summary}</p>
                    </div>

                    <div className="flex items-center gap-6">
                      {res.numeric_value !== undefined && (
                        <div className="text-right">
                          <span className="text-lg font-bold text-slate-100">
                            {res.numeric_value} {res.unit_of_measure}
                          </span>
                          {(res.reference_range_low !== undefined || res.reference_range_high !== undefined) && (
                            <span className="block text-[11px] text-slate-500">
                              Ref: {res.reference_range_low ?? '-'} – {res.reference_range_high ?? '-'} {res.unit_of_measure}
                            </span>
                          )}
                        </div>
                      )}

                      <div>
                        {res.reviewed_at ? (
                          <div className="text-right text-[11px] text-emerald-400 bg-emerald-950/40 px-2.5 py-1 rounded border border-emerald-800/40">
                            ✓ Signed Off ({new Date(res.reviewed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
                          </div>
                        ) : (
                          <button
                            onClick={() => {
                              setSelectedResultForSignoff(res);
                              setShowSignoffModal(true);
                            }}
                            className="text-xs bg-amber-600 hover:bg-amber-500 text-white px-3 py-1.5 rounded-lg font-semibold shadow transition-all"
                          >
                            Sign Off / Review
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          MODAL 1: PLACE CLINICAL ORDER
      ========================================================================== */}
      {showPlaceOrderModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl animate-scaleUp">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <span>➕</span> Place Clinical Order (CPOE)
              </h3>
              <button onClick={() => setShowPlaceOrderModal(false)} className="text-slate-400 hover:text-slate-200">
                ✕
              </button>
            </div>

            <form onSubmit={handlePlaceOrder} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Category</label>
                  <select
                    value={orderCategory}
                    onChange={(e) => setOrderCategory(e.target.value as OrderCategory)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100"
                  >
                    <option value="laboratory">Laboratory 🧪</option>
                    <option value="imaging">Imaging 🩻</option>
                    <option value="medication">Medication 💊</option>
                    <option value="nursing">Nursing 🩺</option>
                    <option value="consultation">Consultation 👨‍⚕️</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Priority</label>
                  <select
                    value={orderPriority}
                    onChange={(e) => setOrderPriority(e.target.value as OrderPriority)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100"
                  >
                    <option value="routine">Routine</option>
                    <option value="urgent">Urgent</option>
                    <option value="stat">STAT 🚨</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Order Type / Code</label>
                <input
                  type="text"
                  value={orderType}
                  onChange={(e) => setOrderType(e.target.value)}
                  placeholder="e.g. complete_blood_count, troponin_i_stat, chest_xray_pa"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Clinical Indication (Medical Rationale)</label>
                <textarea
                  value={clinicalIndication}
                  onChange={(e) => setClinicalIndication(e.target.value)}
                  placeholder="Explain medical necessity for this order..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100 h-20"
                  required
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Specimen Source (if applicable)</label>
                <input
                  type="text"
                  value={specimenSource}
                  onChange={(e) => setSpecimenSource(e.target.value)}
                  placeholder="e.g. Venous blood, Urine clean catch"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowPlaceOrderModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold shadow"
                >
                  {loading ? 'Placing Order...' : 'Confirm Order'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL 2: AI ORDER BUNDLE SYNTHESIS
      ========================================================================== */}
      {showBundleModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl p-6 space-y-4 shadow-2xl animate-scaleUp max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <span>✨</span> AI Order Set Protocol Bundle
              </h3>
              <button onClick={() => setShowBundleModal(false)} className="text-slate-400 hover:text-slate-200">
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Standard Clinical Protocol</label>
                  <select
                    value={bundleProtocol}
                    onChange={(e) => setBundleProtocol(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100"
                  >
                    <option value="chest_pain_acs">Chest Pain / Acute Coronary Syndrome (ACS)</option>
                    <option value="sepsis_bundle">Sepsis Early Intervention Bundle</option>
                    <option value="dka_protocol">Diabetic Ketoacidosis (DKA) Protocol</option>
                    <option value="general_admission">General Inpatient Admission</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Custom Indication (Optional)</label>
                  <input
                    type="text"
                    value={customBundleIndication}
                    onChange={(e) => setCustomBundleIndication(e.target.value)}
                    placeholder="e.g. Acute severe dyspnea"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>
              </div>

              <button
                onClick={handleFetchBundleSuggestion}
                disabled={bundleSynthesizing}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-semibold shadow transition-all"
              >
                {bundleSynthesizing ? 'Synthesizing Protocol...' : 'Generate Bundle Recommendations'}
              </button>

              {suggestedBundleItems.length > 0 && (
                <div className="space-y-3 mt-4 pt-3 border-t border-slate-800">
                  <div>
                    <h4 className="font-bold text-indigo-300 text-sm">{suggestedBundleName}</h4>
                    <p className="text-slate-400 text-xs mt-0.5">{suggestedBundleRationale}</p>
                  </div>

                  {bundleSafetyWarnings.length > 0 && (
                    <div className="bg-amber-950/30 border border-amber-700/50 p-2.5 rounded-lg text-amber-300 space-y-1">
                      {bundleSafetyWarnings.map((w, idx) => (
                        <div key={idx}>⚠️ {w}</div>
                      ))}
                    </div>
                  )}

                  <div className="space-y-2">
                    <h5 className="font-semibold text-slate-300 text-xs">Included Orders ({suggestedBundleItems.length}):</h5>
                    {suggestedBundleItems.map((item, idx) => (
                      <div
                        key={idx}
                        className="bg-slate-800/60 p-2.5 rounded-lg border border-slate-700 flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <span>{getCategoryIcon(item.order_category)}</span>
                          <div>
                            <strong className="text-slate-200">{item.order_type.replace(/_/g, ' ').toUpperCase()}</strong>
                            <p className="text-[11px] text-slate-400">{item.clinical_indication}</p>
                          </div>
                        </div>
                        <span className={`text-[10px] px-2 py-0.5 rounded border uppercase ${getPriorityBadgeClass(item.priority)}`}>
                          {item.priority}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                    <button
                      type="button"
                      onClick={() => setShowBundleModal(false)}
                      className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 font-medium"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleApplyBundleOrders}
                      disabled={loading}
                      className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow"
                    >
                      {loading ? 'Submitting Orders...' : `Place All ${suggestedBundleItems.length} Orders`}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL 3: RECORD DIAGNOSTIC RESULT
      ========================================================================== */}
      {showRecordResultModal && selectedOrderForResult && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl animate-scaleUp">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <span>🔬</span> Record Diagnostic Result ({selectedOrderForResult.order_id})
              </h3>
              <button onClick={() => setShowRecordResultModal(false)} className="text-slate-400 hover:text-slate-200">
                ✕
              </button>
            </div>

            <form onSubmit={handleRecordResult} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Test Name</label>
                  <input
                    type="text"
                    value={resultTestName}
                    onChange={(e) => setResultTestName(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100"
                    required
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">LOINC Code (Optional)</label>
                  <input
                    type="text"
                    value={resultLoinc}
                    onChange={(e) => setResultLoinc(e.target.value)}
                    placeholder="e.g. 2823-3"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Numeric Value</label>
                  <input
                    type="number"
                    step="any"
                    value={resultNumericValue}
                    onChange={(e) => setResultNumericValue(e.target.value)}
                    placeholder="e.g. 6.8"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Unit of Measure</label>
                  <input
                    type="text"
                    value={resultUnit}
                    onChange={(e) => setResultUnit(e.target.value)}
                    placeholder="e.g. mEq/L, mg/dL, ng/mL"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Ref Range Low</label>
                  <input
                    type="number"
                    step="any"
                    value={resultRefLow}
                    onChange={(e) => setResultRefLow(e.target.value)}
                    placeholder="e.g. 3.5"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Ref Range High</label>
                  <input
                    type="number"
                    step="any"
                    value={resultRefHigh}
                    onChange={(e) => setResultRefHigh(e.target.value)}
                    placeholder="e.g. 5.0"
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Findings Summary / Interpretation</label>
                <textarea
                  value={resultFindings}
                  onChange={(e) => setResultFindings(e.target.value)}
                  placeholder="Clinical interpretation of findings..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100 h-20"
                  required
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowRecordResultModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-semibold shadow"
                >
                  {loading ? 'Saving...' : 'Submit Diagnostic Result'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL 4: CLINICIAN SIGNOFF & ACKNOWLEDGMENT
      ========================================================================== */}
      {showSignoffModal && selectedResultForSignoff && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-4 shadow-2xl animate-scaleUp">
            <div className="flex justify-between items-center pb-2 border-b border-slate-800">
              <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <span>✍️</span> Clinician Result Review Signoff
              </h3>
              <button onClick={() => setShowSignoffModal(false)} className="text-slate-400 hover:text-slate-200">
                ✕
              </button>
            </div>

            <form onSubmit={handleSignoffResult} className="space-y-4 text-xs">
              <div className="bg-slate-800/60 p-3 rounded-lg border border-slate-700 space-y-1">
                <strong className="text-slate-200 block">{selectedResultForSignoff.test_name}</strong>
                <p className="text-slate-400">{selectedResultForSignoff.findings_summary}</p>
                {selectedResultForSignoff.numeric_value !== undefined && (
                  <p className="text-sky-400 font-semibold">
                    Value: {selectedResultForSignoff.numeric_value} {selectedResultForSignoff.unit_of_measure}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Review Notes & Action Plan</label>
                <textarea
                  value={signoffNotes}
                  onChange={(e) => setSignoffNotes(e.target.value)}
                  placeholder="e.g. Results reviewed. Adjusting medication dosing accordingly."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-slate-100 h-20"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowSignoffModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold shadow"
                >
                  {loading ? 'Signing Off...' : 'Confirm Signoff'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
