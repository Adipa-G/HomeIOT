import { useState, useCallback, type FormEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { DevCommandEnqueueRequest, DevCommandEnqueueResponse, DevCommandPendingItem, DevCommandResultItem, DeviceListItem, PaginatedResponse } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
import { toast } from '../components/Toast';
import { ApiError } from '../api/client';
import { formatUtc } from '../lib/format';

export default function DevCommandsPage() {
  const qc = useQueryClient();
  const [deviceId, setDeviceId] = useState('');
  const [code, setCode] = useState('');
  const [timeoutMs, setTimeoutMs] = useState('');
  const [error, setError] = useState('');
  const [tab, setTab] = useState<'pending' | 'results'>('pending');
  const [expandedResult, setExpandedResult] = useState<string | null>(null);
  const toggleResult = useCallback((id: string) => setExpandedResult((prev) => (prev === id ? null : id)), []);

  const devices = useQuery({
    queryKey: ['devices-dev'],
    queryFn: () => api.get<PaginatedResponse<DeviceListItem>>('/api/admin/devices?page_size=200'),
    select: (data) => data.items.filter((d) => d.mode === 'development'),
  });

  const pending = useQuery({
    queryKey: ['dev-commands-pending'],
    queryFn: () => api.get<DevCommandPendingItem[]>('/api/admin/dev-commands/pending'),
    refetchInterval: 5000,
    enabled: tab === 'pending',
  });

  const results = useQuery({
    queryKey: ['dev-commands-results'],
    queryFn: () => api.get<DevCommandResultItem[]>('/api/admin/dev-commands/results'),
    refetchInterval: 5000,
    enabled: tab === 'results',
  });

  const enqueue = useMutation({
    mutationFn: () => {
      const body: DevCommandEnqueueRequest = { device_id: deviceId, code };
      const ms = parseInt(timeoutMs, 10);
      if (!isNaN(ms) && ms > 0) body.timeout_ms = ms;
      return api.post<DevCommandEnqueueResponse>('/api/admin/dev-commands', body);
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['dev-commands-pending'] });
      toast(`Command queued: ${data.command_id}`);
      setCode('');
      setTimeoutMs('');
    },
    onError: (err) => setError(err instanceof ApiError ? err.error.message : 'Failed'),
  });

  const handleSubmit = (e: FormEvent) => { e.preventDefault(); setError(''); enqueue.mutate(); };
  const tabClass = (t: string) => `px-4 py-2 text-sm font-medium ${tab === t ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500 hover:text-gray-700'}`;

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold text-gray-900">Dev Commands</h2>

      {/* Enqueue */}
      <form onSubmit={handleSubmit} className="mb-6 rounded-lg border border-gray-200 bg-white p-4">
        {error && <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
        <div className="flex flex-wrap items-start gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Device</label>
            <select
              value={deviceId}
              onChange={(e) => setDeviceId(e.target.value)}
              required
              className="rounded border border-gray-300 px-3 py-1.5 text-sm"
            >
              <option value="">Select device…</option>
              {(devices.data ?? []).map((d) => (
                <option key={d.device_id} value={d.device_id}>{d.device_id}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Timeout (ms)</label>
            <input value={timeoutMs} onChange={(e) => setTimeoutMs(e.target.value)} placeholder="optional" className="w-28 rounded border border-gray-300 px-3 py-1.5 text-sm" />
          </div>
        </div>
        <div className="mt-3">
          <label className="mb-1 block text-sm font-medium text-gray-700">Code</label>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
            rows={8}
            spellCheck={false}
            className="w-full rounded border border-gray-300 px-3 py-2 font-mono text-sm"
            placeholder="# enter MicroPython code here"
          />
        </div>
        <div className="mt-3">
          <button type="submit" disabled={enqueue.isPending} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white disabled:opacity-50">Send</button>
        </div>
      </form>

      {/* Tabs */}
      <div className="mb-4 flex border-b border-gray-200">
        <button className={tabClass('pending')} onClick={() => setTab('pending')}>Pending</button>
        <button className={tabClass('results')} onClick={() => setTab('results')}>Results</button>
      </div>

      {tab === 'pending' && (
        pending.isLoading ? <p className="text-sm text-gray-500">Loading…</p> : !pending.data || pending.data.length === 0 ? (
          <p className="text-sm text-gray-500">No pending commands.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Device</th>
                  <th className="px-4 py-3">Code</th>
                  <th className="px-4 py-3">Queued</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {pending.data.map((p) => (
                  <tr key={p.command_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{p.command_id.slice(0, 8)}</td>
                    <td className="px-4 py-3 font-mono text-gray-600">{p.device_id}</td>
                    <td className="px-4 py-3 font-mono text-sm">{p.code}</td>
                    <td className="px-4 py-3 text-gray-600">{formatUtc(p.queued_at_utc)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}

      {tab === 'results' && (
        results.isLoading ? <p className="text-sm text-gray-500">Loading…</p> : !results.data || results.data.length === 0 ? (
          <p className="text-sm text-gray-500">No results yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="w-6 px-2 py-3" />
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Exit Code</th>
                  <th className="px-4 py-3">Elapsed</th>
                  <th className="px-4 py-3">Completed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {results.data.map((r) => {
                  const expanded = expandedResult === r.command_id;
                  return (
                    <>
                      <tr key={r.command_id} className="cursor-pointer hover:bg-gray-50" onClick={() => toggleResult(r.command_id)}>
                        <td className="px-2 py-3 text-center text-gray-400">{expanded ? '▾' : '▸'}</td>
                        <td className="px-4 py-3 font-mono text-xs text-gray-500">{r.command_id.slice(0, 8)}</td>
                        <td className="px-4 py-3"><StatusBadge text={r.status} variant={r.status === 'success' ? 'green' : 'red'} /></td>
                        <td className="px-4 py-3 text-gray-600">{r.exit_code}</td>
                        <td className="px-4 py-3 text-gray-600">{r.elapsed_ms}ms</td>
                        <td className="px-4 py-3 text-gray-600">{formatUtc(r.finished_at_utc ?? '')}</td>
                      </tr>
                      {expanded && (
                        <tr key={r.command_id + '-detail'} className="bg-gray-50">
                          <td colSpan={6} className="px-6 py-4">
                            <div className="space-y-3">
                              <div>
                                <p className="mb-1 text-xs font-semibold uppercase text-gray-500">Code</p>
                                <pre className="overflow-x-auto rounded border border-gray-200 bg-white p-3 font-mono text-xs text-gray-800">{r.code ?? '—'}</pre>
                              </div>
                              {r.data != null && (
                                <div>
                                  <p className="mb-1 text-xs font-semibold uppercase text-gray-500">Data</p>
                                  <pre className="overflow-x-auto rounded border border-gray-200 bg-white p-3 font-mono text-xs text-gray-800">{JSON.stringify(r.data, null, 2)}</pre>
                                </div>
                              )}
                              {r.stdout && (
                                <div>
                                  <p className="mb-1 text-xs font-semibold uppercase text-gray-500">stdout</p>
                                  <pre className="overflow-x-auto rounded border border-gray-200 bg-white p-3 font-mono text-xs text-gray-600">{r.stdout}</pre>
                                </div>
                              )}
                              {r.stderr && (
                                <div>
                                  <p className="mb-1 text-xs font-semibold uppercase text-gray-500">stderr</p>
                                  <pre className="overflow-x-auto rounded border border-gray-200 bg-white p-3 font-mono text-xs text-red-600">{r.stderr}</pre>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  );
                })}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}
