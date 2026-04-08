import { useState, type FormEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { DevCommandEnqueueRequest, DevCommandEnqueueResponse, DevCommandPendingItem, DevCommandResultItem } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
import { toast } from '../components/Toast';
import { ApiError } from '../api/client';
import { formatUtc } from '../lib/format';

export default function DevCommandsPage() {
  const qc = useQueryClient();
  const [deviceId, setDeviceId] = useState('');
  const [command, setCommand] = useState('');
  const [payload, setPayload] = useState('');
  const [error, setError] = useState('');
  const [tab, setTab] = useState<'pending' | 'results'>('pending');

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
      const body: DevCommandEnqueueRequest = { device_id: deviceId, command };
      if (payload.trim()) {
        try { body.payload = JSON.parse(payload); } catch { body.payload = payload; }
      }
      return api.post<DevCommandEnqueueResponse>('/api/admin/dev-commands', body);
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['dev-commands-pending'] });
      toast(`Command queued: ${data.command_id}`);
      setCommand('');
      setPayload('');
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
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Device ID</label>
            <input value={deviceId} onChange={(e) => setDeviceId(e.target.value)} required className="rounded border border-gray-300 px-3 py-1.5 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Command</label>
            <input value={command} onChange={(e) => setCommand(e.target.value)} required className="rounded border border-gray-300 px-3 py-1.5 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Payload (JSON)</label>
            <input value={payload} onChange={(e) => setPayload(e.target.value)} placeholder="{}" className="rounded border border-gray-300 px-3 py-1.5 text-sm" />
          </div>
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
                  <th className="px-4 py-3">Command</th>
                  <th className="px-4 py-3">Queued</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {pending.data.map((p) => (
                  <tr key={p.command_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{p.command_id.slice(0, 8)}</td>
                    <td className="px-4 py-3 font-mono text-gray-600">{p.device_id}</td>
                    <td className="px-4 py-3">{p.command}</td>
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
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Device</th>
                  <th className="px-4 py-3">Command</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Response</th>
                  <th className="px-4 py-3">Completed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {results.data.map((r) => (
                  <tr key={r.command_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{r.command_id.slice(0, 8)}</td>
                    <td className="px-4 py-3 font-mono text-gray-600">{r.device_id}</td>
                    <td className="px-4 py-3">{r.command}</td>
                    <td className="px-4 py-3"><StatusBadge text={r.status} variant={r.status === 'success' ? 'green' : 'red'} /></td>
                    <td className="max-w-xs truncate px-4 py-3 text-gray-600">{r.response != null ? JSON.stringify(r.response) : '—'}</td>
                    <td className="px-4 py-3 text-gray-600">{formatUtc(r.completed_at_utc)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}
