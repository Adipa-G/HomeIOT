import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { DeviceDetailResponse, HeartbeatListItem, LogBatchListItem, LogEntry, ModuleResultListItem, PaginatedResponse } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
import { Pagination } from '../components/Pagination';
import { ConfirmModal } from '../components/ConfirmModal';
import { toast } from '../components/Toast';
import { formatUtc, formatMs, formatBytes } from '../lib/format';

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState<'heartbeats' | 'logs' | 'modules'>('heartbeats');
  const [hbOffset, setHbOffset] = useState(0);
  const [logOffset, setLogOffset] = useState(0);
  const [modOffset, setModOffset] = useState(0);
  const [selectedModule, setSelectedModule] = useState<string | null>(null);
  const [modHistoryOffset, setModHistoryOffset] = useState(0);
  const [expandedResultId, setExpandedResultId] = useState<string | null>(null);

  const { data: device, isLoading } = useQuery({
    queryKey: ['device', deviceId],
    queryFn: () => api.get<DeviceDetailResponse>(`/api/admin/devices/${deviceId}`),
  });

  const heartbeats = useQuery({
    queryKey: ['heartbeats', deviceId, hbOffset],
    queryFn: () => api.get<PaginatedResponse<HeartbeatListItem>>(`/api/admin/devices/${deviceId}/heartbeats?offset=${hbOffset}&limit=25`),
    enabled: tab === 'heartbeats',
  });

  const logs = useQuery({
    queryKey: ['logs', deviceId, logOffset],
    queryFn: () => api.get<PaginatedResponse<LogBatchListItem>>(`/api/admin/devices/${deviceId}/logs?offset=${logOffset}&limit=25`),
    enabled: tab === 'logs',
  });

  const moduleResults = useQuery({
    queryKey: ['moduleResults', deviceId, modOffset],
    queryFn: () => api.get<PaginatedResponse<ModuleResultListItem>>(`/api/admin/modules/results?device_id=${deviceId}&offset=${modOffset}&limit=100`),
    enabled: tab === 'modules' && selectedModule === null,
  });

  const moduleHistory = useQuery({
    queryKey: ['moduleHistory', deviceId, selectedModule, modHistoryOffset],
    queryFn: () => api.get<PaginatedResponse<ModuleResultListItem>>(`/api/admin/modules/results?device_id=${deviceId}&module_id=${selectedModule}&offset=${modHistoryOffset}&limit=25`),
    enabled: tab === 'modules' && selectedModule !== null,
  });

  const toggleMode = useMutation({
    mutationFn: () => {
      const newMode = device?.mode === 'production' ? 'development' : 'production';
      return api.put(`/api/admin/devices/${deviceId}/mode`, { mode: newMode });
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['device', deviceId] }); toast('Mode updated'); },
  });

  const deleteDevice = useMutation({
    mutationFn: () => api.delete(`/api/admin/devices/${deviceId}`),
    onSuccess: () => { toast('Device deleted'); navigate('/devices', { replace: true }); },
  });

  if (isLoading || !device) return <p className="text-sm text-gray-500">Loading…</p>;

  const tabClass = (t: string) =>
    `px-4 py-2 text-sm font-medium ${tab === t ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500 hover:text-gray-700'}`;

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">{device.device_id}</h2>
          <div className="mt-2 flex flex-wrap gap-4 text-sm text-gray-600">
            <span>Platform: <strong>{device.platform ?? '—'}</strong></span>
            <span>Version: <strong>{device.version ?? '—'}</strong></span>
            <span>IP: <strong>{device.ip ?? '—'}</strong></span>
            <span>Created: {formatUtc(device.created_at_utc)}</span>
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          <button onClick={() => toggleMode.mutate()} className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50">
            Switch to {device.mode === 'production' ? 'development' : 'production'}
          </button>
          <ConfirmModal title="Delete device?" description={`This will permanently delete ${device.device_id} and all its data.`} onConfirm={() => deleteDevice.mutateAsync()}>
            {(open) => <button onClick={open} className="rounded bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700">Delete</button>}
          </ConfirmModal>
        </div>
      </div>

      <div className="mb-1 flex gap-6 rounded-t-lg border-b border-gray-200 bg-white px-2">
        <StatusBadge text={device.mode} variant={device.mode === 'development' ? 'yellow' : 'green'} />
        {device.latest_heartbeat && (
          <span className="py-2 text-xs text-gray-500">
            Uptime: {formatMs(device.latest_heartbeat.uptime_ms)} · Memory: {device.latest_heartbeat.free_memory_bytes != null ? formatBytes(device.latest_heartbeat.free_memory_bytes) : '—'}
          </span>
        )}
      </div>

      {/* Tabs */}
      <div className="mb-4 flex border-b border-gray-200">
        <button className={tabClass('heartbeats')} onClick={() => setTab('heartbeats')}>Heartbeats</button>
        <button className={tabClass('logs')} onClick={() => setTab('logs')}>Logs</button>
        <button className={tabClass('modules')} onClick={() => setTab('modules')}>Modules</button>
      </div>

      {tab === 'heartbeats' && (
        heartbeats.isLoading ? <p className="text-sm text-gray-500">Loading…</p> : heartbeats.data && (
          <>
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                  <tr>
                    <th className="px-4 py-3">Received</th>
                    <th className="px-4 py-3">Uptime</th>
                    <th className="px-4 py-3">Free Memory</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {heartbeats.data.items.map((h, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-600">{formatUtc(h.received_at_utc)}</td>
                      <td className="px-4 py-3 text-gray-600">{formatMs(h.uptime_ms)}</td>
                      <td className="px-4 py-3 text-gray-600">{h.free_memory_bytes != null ? formatBytes(h.free_memory_bytes) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination offset={hbOffset} limit={25} total={heartbeats.data.total} onChange={setHbOffset} />
          </>
        )
      )}

      {tab === 'modules' && selectedModule === null && (
        moduleResults.isLoading ? <p className="text-sm text-gray-500">Loading…</p> : moduleResults.data && (() => {
          const byModule = new Map<string, ModuleResultListItem>();
          for (const r of moduleResults.data.items) {
            if (!byModule.has(r.module_id)) byModule.set(r.module_id, r);
          }
          const tiles = Array.from(byModule.values());
          if (tiles.length === 0) return <p className="text-sm text-gray-400">No module results</p>;
          return (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {tiles.map((r) => {
                const isSuccess = r.status === 'success' || r.status === 'ok';
                return (
                  <div
                    key={r.module_id}
                    className="cursor-pointer rounded-lg border border-gray-200 bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
                    onClick={() => { setSelectedModule(r.module_id); setModHistoryOffset(0); setExpandedResultId(null); }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-gray-900">{r.module_id}</span>
                      <span className={`rounded px-2 py-0.5 text-xs font-medium ${isSuccess ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {r.status}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mb-2">
                      v{r.module_version} · {r.elapsed_ms != null ? `${r.elapsed_ms} ms` : '—'} · {formatUtc(r.finished_at_utc)}
                    </div>
                    {r.error_message && (
                      <div className="text-xs text-red-500 mb-2 truncate">{r.error_message}</div>
                    )}
                    <div className="rounded bg-gray-900 p-2 text-xs font-mono text-gray-200 max-h-32 overflow-auto whitespace-pre-wrap">
                      {r.output ? formatOutput(r.output) : <span className="text-gray-500">No output</span>}
                    </div>
                  </div>
                );
              })}
            </div>
          );
        })()
      )}

      {tab === 'modules' && selectedModule !== null && (
        <>
          <button
            className="mb-3 text-sm text-blue-600 hover:text-blue-800"
            onClick={() => { setSelectedModule(null); setExpandedResultId(null); }}
          >
            ← All modules
          </button>
          {moduleHistory.isLoading ? <p className="text-sm text-gray-500">Loading…</p> : moduleHistory.data && (
            <>
              <h3 className="mb-2 text-sm font-semibold text-gray-900">{selectedModule} — Run History</h3>
              <div className="overflow-x-auto rounded-lg border border-gray-200">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                    <tr>
                      <th className="px-4 py-3">Version</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Duration</th>
                      <th className="px-4 py-3">Variables</th>
                      <th className="px-4 py-3">Finished</th>
                      <th className="px-4 py-3">Error</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {moduleHistory.data.items.length === 0 ? (
                      <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">No results</td></tr>
                    ) : moduleHistory.data.items.map((r) => {
                      const isSuccess = r.status === 'success' || r.status === 'ok';
                      const expanded = expandedResultId === r.id;
                      return (
                        <React.Fragment key={r.id}>
                          <tr className="hover:bg-gray-50 cursor-pointer" onClick={() => setExpandedResultId(expanded ? null : r.id)}>
                            <td className="px-4 py-3 text-gray-600">{r.module_version}</td>
                            <td className="px-4 py-3">
                              <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${isSuccess ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                {r.status}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-gray-600">{r.elapsed_ms != null ? `${r.elapsed_ms} ms` : '—'}</td>
                            <td className="px-4 py-3 text-xs text-gray-600">{formatVariablePreview(r.variable_values)}</td>
                            <td className="px-4 py-3 text-gray-600">{formatUtc(r.finished_at_utc)}</td>
                            <td className="px-4 py-3 text-red-600 text-xs">{r.error_message ?? '—'}</td>
                          </tr>
                          {expanded && (
                            <tr>
                              <td colSpan={6} className="bg-gray-900 px-6 py-3">
                                <div className="mb-2 text-xs text-gray-300">Variables used:</div>
                                <div className="mb-3 text-xs font-mono text-gray-200 whitespace-pre-wrap">
                                  {r.variable_values ? formatOutput(r.variable_values) : <span className="text-gray-500">No variables</span>}
                                </div>
                                <div className="mb-2 text-xs text-gray-300">Output:</div>
                                <div className="text-xs font-mono text-gray-200 whitespace-pre-wrap">
                                  {r.output ? formatOutput(r.output) : <span className="text-gray-500">No output</span>}
                                </div>
                                {r.error_message && (
                                  <div className="mt-2 text-xs font-mono text-red-400 whitespace-pre-wrap">{r.error_message}</div>
                                )}
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <Pagination offset={modHistoryOffset} limit={25} total={moduleHistory.data.total} onChange={setModHistoryOffset} />
            </>
          )}
        </>
      )}

      {tab === 'logs' && (
        logs.isLoading ? <p className="text-sm text-gray-500">Loading…</p> : logs.data && (() => {
          const allEntries = logs.data.items.flatMap((l) => {
            const entries: LogEntry[] = (() => { try { return JSON.parse(l.logs_json); } catch { return []; } })();
            return entries.map((e) => ({ ...e, batchTime: l.received_at_utc }));
          });
          allEntries.sort((a, b) => {
            const ba = new Date(a.batchTime).getTime();
            const bb = new Date(b.batchTime).getTime();
            if (ba !== bb) return bb - ba;
            return (b.ts ?? 0) - (a.ts ?? 0);
          });
          return (
            <>
              <div className="rounded-lg border border-gray-200 bg-gray-900 px-4 py-3 font-mono text-xs leading-relaxed text-gray-200">
                {allEntries.length === 0 ? (
                  <p className="text-gray-500">No log entries</p>
                ) : (
                  allEntries.map((e, i) => {
                    const ctx = e.context && typeof e.context === 'object' && Object.keys(e.context).length > 0
                      ? e.context as Record<string, unknown>
                      : null;
                    return (
                      <div key={i} className="flex gap-2 py-0.5">
                        <span className="shrink-0 text-gray-500">{formatUtc(e.batchTime)}</span>
                        <LogLevel level={e.level} />
                        <span className="break-all">
                          {e.message ?? '—'}
                          {ctx && (
                            <span className="ml-2 text-gray-500">
                              {Object.entries(ctx).map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : v}`).join(' ')}
                            </span>
                          )}
                        </span>
                      </div>
                    );
                  })
                )}
              </div>
              <Pagination offset={logOffset} limit={25} total={logs.data.total} onChange={setLogOffset} />
            </>
          );
        })()
      )}
    </div>
  );
}

function formatOutput(raw: string): string {
  try {
    const parsed = JSON.parse(raw);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return raw;
  }
}

function formatVariablePreview(raw: string | null): string {
  if (!raw) return '—';

  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    const entries = Object.entries(parsed ?? {});
    if (entries.length === 0) return '—';

    const preview = entries
      .slice(0, 2)
      .map(([k, v]) => `${k}=${typeof v === 'object' ? JSON.stringify(v) : String(v)}`)
      .join(', ');

    return entries.length > 2 ? `${preview} +${entries.length - 2} more` : preview;
  } catch {
    return raw;
  }
}

const levelColors: Record<string, string> = {
  error: 'text-red-400',
  warn: 'text-yellow-400',
  warning: 'text-yellow-400',
  info: 'text-blue-400',
  debug: 'text-gray-500',
};

function LogLevel({ level }: { level: string | null }) {
  const l = (level ?? 'info').toLowerCase();
  return <span className={`shrink-0 w-12 uppercase ${levelColors[l] ?? 'text-gray-400'}`}>{l}</span>;
}
