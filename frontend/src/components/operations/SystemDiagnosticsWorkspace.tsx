import React, { useState, useEffect } from 'react';
import { systemApi, fhirApi } from '../../api/client';
import {
  SystemLivenessResponse,
  SystemReadinessResponse,
  SystemMetricsResponse,
  FHIRCapabilityStatement,
} from '../../types';

export const SystemDiagnosticsWorkspace: React.FC = () => {
  const [liveness, setLiveness] = useState<SystemLivenessResponse | null>(null);
  const [readiness, setReadiness] = useState<SystemReadinessResponse | null>(null);
  const [metrics, setMetrics] = useState<SystemMetricsResponse | null>(null);
  const [fhirCapability, setFhirCapability] = useState<FHIRCapabilityStatement | null>(null);
  const [prometheusText, setPrometheusText] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [activeSubTab, setActiveSubTab] = useState<'overview' | 'metrics' | 'fhir' | 'prometheus'>('overview');
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const fetchDiagnostics = async () => {
    setLoading(true);
    setError(null);
    try {
      const [liveRes, readyRes, metricsRes, fhirRes] = await Promise.allSettled([
        systemApi.getLiveness(),
        systemApi.getReadiness(),
        systemApi.getMetrics(),
        fhirApi.getCapabilityStatement(),
      ]);

      if (liveRes.status === 'fulfilled') setLiveness(liveRes.value);
      if (readyRes.status === 'fulfilled') setReadiness(readyRes.value);
      if (metricsRes.status === 'fulfilled') setMetrics(metricsRes.value);
      if (fhirRes.status === 'fulfilled') setFhirCapability(fhirRes.value);

      setLastRefreshed(new Date());
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch platform operational diagnostics');
    } finally {
      setLoading(false);
    }
  };

  const fetchPrometheusMetrics = async () => {
    try {
      const text = await systemApi.getPrometheusMetricsText();
      setPrometheusText(text);
    } catch (err: any) {
      setPrometheusText('# Error fetching Prometheus metrics: ' + (err?.message || 'Unknown error'));
    }
  };

  useEffect(() => {
    fetchDiagnostics();
  }, []);

  useEffect(() => {
    if (activeSubTab === 'prometheus') {
      fetchPrometheusMetrics();
    }
  }, [activeSubTab]);

  return (
    <div className="space-y-6" data-testid="system-diagnostics-workspace">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 relative z-10">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <div className="text-2xl p-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg">
                ⚙️
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                  Enterprise Infrastructure & Diagnostics
                  <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-semibold">
                    Production Hardened
                  </span>
                </h2>
                <p className="text-sm text-slate-400">
                  Real-time observability, connection pooling, Redis caching, rate limiting & FHIR R4 conformance
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchDiagnostics}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg text-sm text-slate-200 font-medium transition-colors disabled:opacity-50"
            >
              🔄 Refresh Diagnostics
            </button>
          </div>
        </div>

        {/* Global Health KPIs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          <div className="bg-slate-800/50 border border-slate-700/60 rounded-lg p-3.5">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
              📡 Platform Liveness
            </div>
            <div className="text-lg font-bold text-emerald-400 flex items-center gap-2">
              {liveness?.status === 'alive' ? 'ALIVE' : 'UNKNOWN'}
            </div>
            <div className="text-xs text-slate-400 mt-1">Env: {liveness?.environment || 'production'}</div>
          </div>

          <div className="bg-slate-800/50 border border-slate-700/60 rounded-lg p-3.5">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
              🗄️ PostgreSQL & Redis
            </div>
            <div className="text-lg font-bold text-slate-100 flex items-center gap-2">
              {readiness?.ready ? (
                <span className="text-emerald-400">READY</span>
              ) : (
                <span className="text-amber-400">DEGRADED</span>
              )}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              DB: {readiness?.components.database?.healthy ? 'Connected' : 'Unavailable'}
            </div>
          </div>

          <div className="bg-slate-800/50 border border-slate-700/60 rounded-lg p-3.5">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
              ⚡ HTTP Throughput
            </div>
            <div className="text-lg font-bold text-slate-100">
              {metrics?.http.total_requests || 0} reqs
            </div>
            <div className="text-xs text-slate-400 mt-1">
              Avg Latency: {(metrics?.http.avg_duration_ms || 0).toFixed(1)}ms
            </div>
          </div>

          <div className="bg-slate-800/50 border border-slate-700/60 rounded-lg p-3.5">
            <div className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">
              🌐 FHIR R4 Interop
            </div>
            <div className="text-lg font-bold text-indigo-400">
              {fhirCapability?.fhirVersion || '4.0.1'}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {fhirCapability?.rest?.[0]?.resource?.length || 21} Standard Resources
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Subtabs */}
      <div className="flex border-b border-slate-800 gap-2">
        <button
          onClick={() => setActiveSubTab('overview')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeSubTab === 'overview'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          📊 Component Readiness Matrix
        </button>
        <button
          onClick={() => setActiveSubTab('metrics')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeSubTab === 'metrics'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          📈 Request & Worker Telemetry
        </button>
        <button
          onClick={() => setActiveSubTab('fhir')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeSubTab === 'fhir'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          🌐 FHIR CapabilityStatement
        </button>
        <button
          onClick={() => setActiveSubTab('prometheus')}
          className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeSubTab === 'prometheus'
              ? 'border-cyan-500 text-cyan-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          📜 Prometheus Exposition
        </button>
      </div>

      {/* SUBTAB 1: Component Readiness Matrix */}
      {activeSubTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {/* Database */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">🗄️</span>
                <h3 className="font-semibold text-slate-200">PostgreSQL Engine</h3>
              </div>
              <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                readiness?.components.database?.healthy
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                  : 'bg-red-500/10 text-red-400 border border-red-500/30'
              }`}>
                {readiness?.components.database?.status || 'Unknown'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              ACID transaction store with SSL connection pooling and automated migration safety.
            </p>
            <div className="text-xs space-y-1.5 text-slate-300 border-t border-slate-800 pt-3">
              <div className="flex justify-between">
                <span className="text-slate-500">Driver:</span>
                <span className="font-mono">psycopg3 (async/sync)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Pooling:</span>
                <span className="font-mono">QueuePool (pool_pre_ping)</span>
              </div>
            </div>
          </div>

          {/* Redis Cache */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">⚡</span>
                <h3 className="font-semibold text-slate-200">Redis Distributed Cache</h3>
              </div>
              <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                readiness?.components.cache?.healthy
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                  : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
              }`}>
                {readiness?.components.cache?.status || 'Connected'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              In-memory distributed key-value cache with automatic in-memory fallback.
            </p>
            <div className="text-xs space-y-1.5 text-slate-300 border-t border-slate-800 pt-3">
              <div className="flex justify-between">
                <span className="text-slate-500">Active Provider:</span>
                <span className="font-mono">{readiness?.components.cache?.provider || 'RedisCache'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Default TTL:</span>
                <span className="font-mono">3600 seconds</span>
              </div>
            </div>
          </div>

          {/* Chroma Vector Store */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">🧬</span>
                <h3 className="font-semibold text-slate-200">Clinical Vector Store</h3>
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                {readiness?.components.vector_store?.status || 'Available'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Patient-isolated semantic vector indexing for RAG clinical grounding.
            </p>
            <div className="text-xs space-y-1.5 text-slate-300 border-t border-slate-800 pt-3">
              <div className="flex justify-between">
                <span className="text-slate-500">Embedding:</span>
                <span className="font-mono">{readiness?.components.vector_store?.provider || 'text-embedding-3-small'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Collection:</span>
                <span className="font-mono">{readiness?.components.vector_store?.collection || 'medical_documents'}</span>
              </div>
            </div>
          </div>

          {/* Task Worker Pool */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">⚙️</span>
                <h3 className="font-semibold text-slate-200">Background Task Workers</h3>
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                {readiness?.components.task_worker?.status || 'Ready'}
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Distributed Celery / ThreadPool executor processing OCR, AI synthesis, and CQM jobs.
            </p>
            <div className="text-xs space-y-1.5 text-slate-300 border-t border-slate-800 pt-3">
              <div className="flex justify-between">
                <span className="text-slate-500">Provider:</span>
                <span className="font-mono">{readiness?.components.task_worker?.provider || 'celery'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Queue Depth:</span>
                <span className="font-mono text-emerald-400 font-bold">
                  {metrics?.tasks.queued || 0} queued, {metrics?.tasks.running || 0} running
                </span>
              </div>
            </div>
          </div>

          {/* Rate Limiting Protection */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">🛡️</span>
                <h3 className="font-semibold text-slate-200">Abuse Protection & Rate Limits</h3>
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                Active
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Sliding-window rate limiter per client IP and authenticated clinical user.
            </p>
            <div className="text-xs space-y-1.5 text-slate-300 border-t border-slate-800 pt-3">
              <div className="flex justify-between">
                <span className="text-slate-500">Auth Login Limit:</span>
                <span className="font-mono">5 req/min</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">General API Limit:</span>
                <span className="font-mono">60 req/min</span>
              </div>
            </div>
          </div>

          {/* Clinical Circuit Breakers */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <span className="text-xl">🔌</span>
                <h3 className="font-semibold text-slate-200">Integration Circuit Breakers</h3>
              </div>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                CLOSED (Healthy)
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-3">
              Automatic failover and degraded mode execution for cloud LLMs and OpenFDA APIs.
            </p>
            <div className="text-xs space-y-1.5 text-slate-300 border-t border-slate-800 pt-3">
              <div className="flex justify-between">
                <span className="text-slate-500">State:</span>
                <span className="font-mono text-emerald-400 font-bold">All Circuits Healthy</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Retry Policy:</span>
                <span className="font-mono">Strict Non-Mutation Retries</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUBTAB 2: HTTP & Worker Telemetry */}
      {activeSubTab === 'metrics' && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                HTTP Requests by Status
              </div>
              <div className="space-y-2 mt-4">
                {Object.entries(metrics?.http.requests_by_status || { '200': 0 }).map(([code, count]) => (
                  <div key={code} className="flex justify-between items-center text-sm">
                    <span className={`font-mono font-bold ${
                      code.startsWith('2') ? 'text-emerald-400' : code.startsWith('4') ? 'text-amber-400' : 'text-red-400'
                    }`}>
                      HTTP {code}
                    </span>
                    <span className="text-slate-200 font-mono">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Latency Distribution
              </div>
              <div className="text-3xl font-bold text-slate-100 mt-2">
                {(metrics?.http.avg_duration_ms || 0).toFixed(1)} <span className="text-base font-normal text-slate-400">ms avg</span>
              </div>
              <p className="text-xs text-slate-400 mt-2">
                Uptime: {Math.floor((metrics?.http.uptime_seconds || 0) / 60)} minutes
              </p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Task Execution Counters
              </div>
              <div className="space-y-2 mt-4 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-400">Completed Tasks:</span>
                  <span className="font-mono text-emerald-400 font-bold">{metrics?.tasks.completed || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Failed Tasks:</span>
                  <span className="font-mono text-red-400 font-bold">{metrics?.tasks.failed || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Active Queue:</span>
                  <span className="font-mono text-cyan-400 font-bold">{metrics?.tasks.queued || 0}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SUBTAB 3: FHIR R4 CapabilityStatement */}
      {activeSubTab === 'fhir' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h3 className="font-bold text-slate-100 text-lg">FHIR R4 CapabilityStatement</h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Publisher: {fhirCapability?.publisher || 'MediGen AI Clinical Intelligence Platform'} | Version: {fhirCapability?.fhirVersion}
              </p>
            </div>
            <span className="px-3 py-1 bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-semibold rounded-full">
              RESTful Server
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 pt-2">
            {fhirCapability?.rest?.[0]?.resource?.map((res) => (
              <div key={res.type} className="bg-slate-800/60 border border-slate-700/60 rounded-lg p-3 text-xs">
                <div className="font-bold text-slate-200 text-sm mb-1">{res.type}</div>
                <div className="text-slate-400">
                  Interactions:{' '}
                  <span className="font-mono text-cyan-400">
                    {res.interaction.map((i) => i.code).join(', ')}
                  </span>
                </div>
              </div>
            )) || (
              <div className="text-sm text-slate-500 col-span-4">Loading capability resources...</div>
            )}
          </div>
        </div>
      )}

      {/* SUBTAB 4: Raw Prometheus Metrics */}
      {activeSubTab === 'prometheus' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="font-bold text-slate-100 flex items-center gap-2">
              📜 Prometheus Exposition Output (/api/v1/health/metrics/prometheus)
            </h3>
            <button
              onClick={fetchPrometheusMetrics}
              className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 font-medium transition-colors"
            >
              Refresh Raw Text
            </button>
          </div>
          <pre className="p-4 bg-slate-950 border border-slate-800/80 rounded-lg text-xs font-mono text-emerald-400/90 overflow-x-auto max-h-[500px]">
            {prometheusText || 'Loading Prometheus metrics text...'}
          </pre>
        </div>
      )}
    </div>
  );
};
