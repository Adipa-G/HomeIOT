import { useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { DeviceDetailResponse, HeartbeatListItem, LogBatchListItem, PaginatedResponse } from '../types/api';
import { StatusBadge } from '../components/StatusBadge';
import { Pagination } from '../components/Pagination';
import { ConfirmModal } from '../components/ConfirmModal';
import { toast } from '../components/Toast';
import { formatUtc, formatMs, formatBytes } from '../lib/format';

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState<'heartbeats' | 'logs'>('heartbeats');
  const [hbOffset, setHbOffset] = useState(0);
  const [logOffset, setLogOffset] = useState(0);

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
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">{device.device_id}</h2>
          <div className="mt-2 flex flex-wrap gap-4 text-sm text-gray-600">
            <span>Platform: <strong>{device.platform ?? '—'}</strong></span>
            <span>Version: <strong>{device.version ?? '—'}</strong></span>
            <span>IP: <strong>{device.ip ?? '—'}</strong></span>
            <span>Created: {formatUtc(device.created_at_utc)}</span>
          </div>
        </div>
        <div className="flex gap-2">
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

      {tab === 'logs' && (
        logs.isLoading ? <p className="text-sm text-gray-500">Loading…</p> : logs.data && (
          <>
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                  <tr>
                    <th className="px-4 py-3">Received</th>
                    <th className="px-4 py-3">Reason</th>
                    <th className="px-4 py-3">Count</th>
                    <th className="px-4 py-3">Dropped</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {logs.data.items.map((l) => (
                    <tr key={l.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-gray-600">{formatUtc(l.received_at_utc)}</td>
                      <td className="px-4 py-3 text-gray-600">{l.reason}</td>
                      <td className="px-4 py-3 text-gray-600">{l.received_count}</td>
                      <td className="px-4 py-3 text-gray-600">{l.dropped_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination offset={logOffset} limit={25} total={logs.data.total} onChange={setLogOffset} />
          </>
        )
      )}
    </div>
  );
}
