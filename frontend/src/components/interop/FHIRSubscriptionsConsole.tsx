import React, { useState, useEffect } from 'react';
import { fhirSubscriptionsApi } from '../../api/client';
import { FHIRSubscription } from '../../types';

export const FHIRSubscriptionsConsole: React.FC = () => {
  const [subscriptions, setSubscriptions] = useState<FHIRSubscription[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Form State
  const [topic, setTopic] = useState('order-created');
  const [criteria, setCriteria] = useState('ServiceRequest?status=active');
  const [channelType, setChannelType] = useState<'REST_HOOK' | 'WEBSOCKET' | 'EMAIL'>('REST_HOOK');
  const [endpointUrl, setEndpointUrl] = useState('https://ehr-gateway.metrohealth.org/webhooks/orders');
  const [secretToken, setSecretToken] = useState('');

  useEffect(() => {
    loadSubscriptions();
  }, []);

  const loadSubscriptions = async () => {
    try {
      setLoading(true);
      setError(null);
      const list = await fhirSubscriptionsApi.listSubscriptions();
      setSubscriptions(list);
    } catch (err: any) {
      setError(err.message || 'Failed to load FHIR subscriptions');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      await fhirSubscriptionsApi.createSubscription({
        topic,
        criteria,
        channel_type: channelType,
        endpoint_url: endpointUrl,
        secret_token: secretToken || undefined,
      });
      setShowCreateModal(false);
      await loadSubscriptions();
    } catch (err: any) {
      setError(err.message || 'Failed to create subscription');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (subId: string) => {
    if (!window.confirm(`Delete subscription ${subId}?`)) return;
    try {
      setLoading(true);
      await fhirSubscriptionsApi.deleteSubscription(subId);
      await loadSubscriptions();
    } catch (err: any) {
      setError(err.message || 'Failed to delete subscription');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-blue-50 dark:bg-blue-900/30 rounded-xl text-blue-600 dark:text-blue-400 font-bold text-xl">
            📡
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">FHIR R4 Topic Subscriptions</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">Event-driven webhooks and WebSocket notifications for EHR integrations</p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadSubscriptions}
            disabled={loading}
            className="p-2 text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition text-sm"
            title="Refresh"
          >
            🔄
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-xl transition flex items-center gap-2"
          >
            ➕ New Subscription
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl text-xs text-red-600 dark:text-red-400 flex items-center gap-2">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Subscriptions Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 dark:bg-slate-900/50 text-slate-500 dark:text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="py-3 px-4">Subscription ID</th>
              <th className="py-3 px-4">Topic / Criteria</th>
              <th className="py-3 px-4">Channel</th>
              <th className="py-3 px-4">Endpoint</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60 font-sans">
            {subscriptions.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-400">
                  No active FHIR subscriptions registered.
                </td>
              </tr>
            ) : (
              subscriptions.map((sub) => (
                <tr key={sub.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-700/30 transition">
                  <td className="py-3 px-4 font-mono font-medium text-slate-900 dark:text-white">
                    {sub.subscription_id}
                  </td>
                  <td className="py-3 px-4">
                    <span className="font-semibold text-slate-800 dark:text-slate-200">{sub.topic}</span>
                    <span className="block text-[11px] text-slate-400 font-mono">{sub.criteria}</span>
                  </td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium">
                      {sub.channel_type}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-600 dark:text-slate-300 max-w-xs truncate font-mono text-[11px]">
                    {sub.endpoint_url}
                  </td>
                  <td className="py-3 px-4">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                      ✓ {sub.status}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <button
                      onClick={() => handleDelete(sub.subscription_id)}
                      className="p-1.5 text-slate-400 hover:text-red-600 dark:hover:text-red-400 rounded-lg transition text-xs"
                      title="Delete Subscription"
                    >
                      🗑️
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 max-w-md w-full p-6">
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-4">Register FHIR R4 Subscription</h3>
            <form onSubmit={handleCreate} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Topic Event</label>
                <select
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white"
                >
                  <option value="order-created">order-created (New CPOE order)</option>
                  <option value="encounter-start">encounter-start (Patient check-in)</option>
                  <option value="alert-critical">alert-critical (Emergency vitals / hypoxia)</option>
                  <option value="lab-result-ready">lab-result-ready (Diagnostic result released)</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Filter Criteria (FHIR URL)</label>
                <input
                  type="text"
                  value={criteria}
                  onChange={(e) => setCriteria(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-xl font-mono text-slate-900 dark:text-white"
                  placeholder="ServiceRequest?status=active"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Channel Type</label>
                <select
                  value={channelType}
                  onChange={(e) => setChannelType(e.target.value as any)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white"
                >
                  <option value="REST_HOOK">REST-Hook (HTTPS POST Webhook)</option>
                  <option value="WEBSOCKET">WebSocket (Live Channel)</option>
                  <option value="EMAIL">Email Alert</option>
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Endpoint URL</label>
                <input
                  type="url"
                  value={endpointUrl}
                  onChange={(e) => setEndpointUrl(e.target.value)}
                  required
                  className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-xl font-mono text-slate-900 dark:text-white"
                  placeholder="https://ehr-gateway.metrohealth.org/webhooks/orders"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Secret Token (Optional HMAC)</label>
                <input
                  type="password"
                  value={secretToken}
                  onChange={(e) => setSecretToken(e.target.value)}
                  className="w-full px-3 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-600 rounded-xl text-slate-900 dark:text-white"
                  placeholder="Shared webhook authorization token"
                />
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition"
                >
                  {loading ? 'Registering...' : 'Register Subscription'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
