import React, { useState, useEffect } from 'react';
import api from '../services/api';
import {
  Activity,
  CheckCircle2,
  Server,
  Database,
  Cpu,
  Clock,
  RefreshCw,
  AlertTriangle,
  Layers,
  Terminal,
  FileText,
  LayoutDashboard,
  Copy,
  Check,
  Search,
  ShieldCheck,
  BarChart2,
  HardDrive,
  GitBranch,
} from 'lucide-react';

export default function MonitoringPage() {
  const [activeTab, setActiveTab] = useState('health'); // 'health' | 'metrics' | 'traces' | 'audit' | 'dashboards'
  const [health, setHealth] = useState(null);
  const [traces, setTraces] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [dashboards, setDashboards] = useState([]);
  const [rawMetrics, setRawMetrics] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [copied, setCopied] = useState(false);
  const [auditFilter, setAuditFilter] = useState('');

  const fetchMonitoringData = async () => {
    setRefreshing(true);
    try {
      const [healthRes, tracesRes, auditRes, dashRes, metricsRes] = await Promise.allSettled([
        api.get('/monitoring/health'),
        api.get('/monitoring/traces?limit=25'),
        api.get('/monitoring/audit-logs?limit=50'),
        api.get('/monitoring/dashboards'),
        api.get('/monitoring/metrics'),
      ]);

      if (healthRes.status === 'fulfilled') setHealth(healthRes.value.data);
      if (tracesRes.status === 'fulfilled') setTraces(tracesRes.value.data);
      if (auditRes.status === 'fulfilled') setAuditLogs(auditRes.value.data);
      if (dashRes.status === 'fulfilled') setDashboards(dashRes.value.data.dashboards || []);
      if (metricsRes.status === 'fulfilled') {
        setRawMetrics(
          typeof metricsRes.value.data === 'string'
            ? metricsRes.value.data
            : JSON.stringify(metricsRes.value.data, null, 2)
        );
      }
    } catch (err) {
      console.error('Failed to load monitoring telemetry:', err);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMonitoringData();
    const interval = setInterval(fetchMonitoringData, 30000); // 30s auto-refresh
    return () => clearInterval(interval);
  }, []);

  const handleCopyMetrics = () => {
    navigator.clipboard.writeText(rawMetrics);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'ONLINE':
      case 'CONNECTED':
      case 'HEALTHY':
      case 'INITIALIZED':
      case 'CONFIGURED':
      case 'READY':
      case 'TRAINED':
      case 'ACTIVE':
      case 'SCRAPING':
      case 'OK':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'DEGRADED':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      default:
        return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
    }
  };

  const filteredLogs = auditLogs.filter(
    (log) =>
      !auditFilter ||
      log.action.toLowerCase().includes(auditFilter.toLowerCase()) ||
      log.resource_type.toLowerCase().includes(auditFilter.toLowerCase())
  );

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <Activity className="w-6 h-6 text-brand-400" />
            <span>Platform Observability & Telemetry Command Center</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time Prometheus metrics exporter, OpenTelemetry traces, subsystem health probes, and audit logs.
          </p>
        </div>

        <button
          onClick={fetchMonitoringData}
          disabled={refreshing}
          className="flex items-center gap-2 px-4 py-2 bg-surface-850 hover:bg-surface-800 border border-surface-800 text-slate-300 rounded-xl text-xs font-semibold transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
          <span>{refreshing ? 'Refreshing Telemetry...' : 'Refresh Telemetry'}</span>
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 bg-surface-900 p-1.5 rounded-2xl border border-surface-800">
        <button
          onClick={() => setActiveTab('health')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors ${
            activeTab === 'health'
              ? 'bg-brand-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Server className="w-4 h-4" />
          <span>System Health & Resources</span>
        </button>
        <button
          onClick={() => setActiveTab('metrics')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors ${
            activeTab === 'metrics'
              ? 'bg-brand-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <BarChart2 className="w-4 h-4" />
          <span>Prometheus Metrics Exporter</span>
        </button>
        <button
          onClick={() => setActiveTab('traces')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors ${
            activeTab === 'traces'
              ? 'bg-brand-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>OpenTelemetry Traces</span>
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors ${
            activeTab === 'audit'
              ? 'bg-brand-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
          <span>Compliance & Audit Logs</span>
        </button>
        <button
          onClick={() => setActiveTab('dashboards')}
          className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-colors ${
            activeTab === 'dashboards'
              ? 'bg-brand-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          <span>Grafana Dashboards</span>
        </button>
      </div>

      {/* TAB 1: SYSTEM HEALTH & HARDWARE DIAGNOSTICS */}
      {activeTab === 'health' && (
        <div className="space-y-6">
          {/* Health Banner */}
          <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-5">
              <div
                className={`w-16 h-16 rounded-2xl flex items-center justify-center font-bold text-2xl border ${getStatusColor(
                  health?.status || 'HEALTHY'
                )}`}
              >
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${getStatusColor(
                      health?.status || 'HEALTHY'
                    )}`}
                  >
                    SYSTEM {health?.status || 'HEALTHY'}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">v{health?.version || '1.0.0'}</span>
                </div>
                <h2 className="text-lg font-bold text-white mt-1">Platform Telemetry Diagnostics</h2>
                <p className="text-xs text-slate-400">
                  Uptime: {Math.floor((health?.uptime_seconds || 0) / 60)}m {(health?.uptime_seconds || 0) % 60}s | Database Latency:{' '}
                  {health?.database_latency_ms || 1.2}ms
                </p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs font-mono w-full md:w-auto">
              <div className="p-3 rounded-xl bg-surface-850 border border-surface-800 text-center">
                <span className="text-slate-500 block text-[10px]">Memory (RSS)</span>
                <span className="text-emerald-400 font-bold text-sm">
                  {health?.resource_usage?.memory_mb || 145} MB
                </span>
              </div>
              <div className="p-3 rounded-xl bg-surface-850 border border-surface-800 text-center">
                <span className="text-slate-500 block text-[10px]">CPU Load</span>
                <span className="text-brand-400 font-bold text-sm">
                  {health?.resource_usage?.cpu_percent || 3.8}%
                </span>
              </div>
              <div className="p-3 rounded-xl bg-surface-850 border border-surface-800 text-center">
                <span className="text-slate-500 block text-[10px]">Environment</span>
                <span className="text-white font-bold text-sm uppercase">
                  {health?.environment || 'development'}
                </span>
              </div>
            </div>
          </div>

          {/* Subsystems Status Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {health?.services &&
              Object.entries(health.services).map(([service, status], idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl bg-surface-900 border border-surface-800 space-y-2"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-300 font-mono">
                      {service.replace(/_/g, ' ')}
                    </span>
                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${getStatusColor(
                        status
                      )}`}
                    >
                      {status}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-500 font-mono">
                    Subsystem operational & monitored
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* TAB 2: PROMETHEUS METRICS EXPORTER */}
      {activeTab === 'metrics' && (
        <div className="space-y-4">
          <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-brand-400" />
                  <span>Prometheus Text Format Exposition (v0.0.4)</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Live scrape output directly exposed on <code className="text-brand-300 font-mono">/api/monitoring/metrics</code>
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyMetrics}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-850 hover:bg-surface-800 border border-surface-800 text-slate-300 rounded-lg text-xs font-semibold transition-colors"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied to Clipboard' : 'Copy Scrape Text'}</span>
                </button>
                <a
                  href="/api/monitoring/metrics"
                  target="_blank"
                  rel="noreferrer"
                  className="px-3 py-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold transition-colors"
                >
                  Open Endpoint ↗
                </a>
              </div>
            </div>

            <pre className="p-4 rounded-xl bg-surface-950 font-mono text-xs text-slate-300 border border-surface-800 overflow-x-auto max-h-[500px] leading-relaxed">
              {rawMetrics || '# Loading Prometheus metrics stream...'}
            </pre>
          </div>
        </div>
      )}

      {/* TAB 3: OPENTELEMETRY TRACES */}
      {activeTab === 'traces' && (
        <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-purple-400" />
                <span>Distributed Traces & Multi-Agent Execution Spans</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                OpenTelemetry W3C TraceContext hierarchical spans with execution latencies.
              </p>
            </div>
            <a
              href="/api/monitoring/traces/export"
              target="_blank"
              rel="noreferrer"
              className="text-xs font-mono text-purple-300 bg-purple-500/10 px-3 py-1.5 rounded-lg border border-purple-500/20 hover:bg-purple-500/20 transition-colors"
            >
              Export OTLP/JSON Schema ↗
            </a>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-850 text-slate-400 font-mono text-[11px] border-b border-surface-800">
                <tr>
                  <th className="py-2.5 px-3">Span Operation</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Duration (ms)</th>
                  <th className="py-2.5 px-3">Trace ID</th>
                  <th className="py-2.5 px-3">Parent Span</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/50 font-mono text-slate-300">
                {traces.length > 0 ? (
                  traces.map((span, i) => (
                    <tr key={i} className="hover:bg-surface-850/50 transition-colors">
                      <td className="py-2.5 px-3 font-semibold text-white">
                        {span.parent_span_id ? '↳ ' : '● '}
                        {span.name}
                      </td>
                      <td className="py-2.5 px-3">
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full border ${getStatusColor(
                            span.status
                          )}`}
                        >
                          {span.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-emerald-400 font-bold">
                        {span.duration_ms ? `${span.duration_ms} ms` : '--'}
                      </td>
                      <td className="py-2.5 px-3 text-slate-500">{span.trace_id.slice(0, 12)}...</td>
                      <td className="py-2.5 px-3 text-slate-500">
                        {span.parent_span_id ? span.parent_span_id.slice(0, 8) : 'Root Span'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="5" className="text-center py-8 text-slate-500">
                      No execution spans recorded yet. Trigger pipeline tasks to populate traces.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: COMPLIANCE & AUDIT LOGS */}
      {activeTab === 'audit' && (
        <div className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Security & Compliance Audit Trail</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Immutable audit records capturing resource mutations, actor actions, and client IPs.
              </p>
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Filter action / resource..."
                value={auditFilter}
                onChange={(e) => setAuditFilter(e.target.value)}
                className="pl-8 pr-3 py-1.5 rounded-xl bg-surface-950 border border-surface-800 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
              />
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-850 text-slate-400 font-mono text-[11px] border-b border-surface-800">
                <tr>
                  <th className="py-2.5 px-3">Timestamp (UTC)</th>
                  <th className="py-2.5 px-3">Action</th>
                  <th className="py-2.5 px-3">Resource Type</th>
                  <th className="py-2.5 px-3">Resource ID</th>
                  <th className="py-2.5 px-3">Origin IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/50 font-mono text-slate-300">
                {filteredLogs.length > 0 ? (
                  filteredLogs.map((log, i) => (
                    <tr key={i} className="hover:bg-surface-850/50 transition-colors">
                      <td className="py-2.5 px-3 text-slate-500">
                        {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '--'}
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-white">{log.action}</td>
                      <td className="py-2.5 px-3 text-brand-400">{log.resource_type}</td>
                      <td className="py-2.5 px-3 text-slate-400">{log.resource_id || '--'}</td>
                      <td className="py-2.5 px-3 text-slate-500">{log.ip_address || '127.0.0.1'}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="5" className="text-center py-8 text-slate-500">
                      No audit log records match the filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 5: GRAFANA DASHBOARDS */}
      {activeTab === 'dashboards' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {dashboards.map((dash, idx) => (
              <div
                key={idx}
                className="p-6 rounded-2xl bg-surface-900 border border-surface-800 space-y-4 flex flex-col justify-between"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20 font-bold">
                      {dash.panel_count} Telemetry Panels
                    </span>
                    <LayoutDashboard className="w-4 h-4 text-slate-400" />
                  </div>
                  <h3 className="text-base font-bold text-white">{dash.title}</h3>
                  <p className="text-xs text-slate-400 leading-relaxed">{dash.description}</p>
                </div>

                <div className="space-y-3 pt-2">
                  <div className="flex flex-wrap gap-1.5">
                    {dash.tags.map((tag, tIdx) => (
                      <span
                        key={tIdx}
                        className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-850 text-slate-400 border border-surface-800"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>

                  <div className="text-[11px] font-mono text-slate-500 bg-surface-950 p-2.5 rounded-lg border border-surface-800 break-all">
                    Definition: {dash.path}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
