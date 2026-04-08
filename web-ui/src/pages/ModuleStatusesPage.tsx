import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { ModuleStatusListItem, PaginatedResponse } from '../types/api';
import { Pagination } from '../components/Pagination';
import { StatusBadge } from '../components/StatusBadge';
import { formatUtc, formatBytes } from '../lib/format';

export default function ModuleStatusesPage() {
  const [offset, setOffset] = useState(0);
  const [deviceId, setDeviceId] = useState('');
  const limit = 50;

  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (deviceId) params.set('device_id', deviceId);

  const { data, isLoading } = useQuery({
    queryKey: ['module-statuses', offset, deviceId],
    queryFn: () => api.get<PaginatedResponse<ModuleStatusListItem>>(`/api/admin/modules/statuses?${params}`),
  });

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold text-gray-900">Module Statuses</h2>
      <input placeholder="Filter device ID…" value={deviceId} onChange={(e) => { setDeviceId(e.target.value); setOffset(0); }} className="mb-4 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none" />
      {isLoading ? <p className="text-sm text-gray-500">Loading…</p> : !data || data.items.length === 0 ? (
        <p className="text-sm text-gray-500">No statuses found.</p>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3">Device</th>
                  <th className="px-4 py-3">Module</th>
                  <th className="px-4 py-3">Version</th>
                  <th className="px-4 py-3">State</th>
                  <th className="px-4 py-3">Memory</th>
                  <th className="px-4 py-3">Updated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map((s) => (
                  <tr key={s.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-gray-600">{s.device_id}</td>
                    <td className="px-4 py-3 font-mono text-gray-600">{s.module_id}</td>
                    <td className="px-4 py-3 font-mono text-gray-600">{s.version}</td>
                    <td className="px-4 py-3"><StatusBadge text={s.state} variant={s.state === 'running' ? 'green' : s.state === 'error' ? 'red' : 'gray'} /></td>
                    <td className="px-4 py-3 text-gray-600">{s.memory_bytes != null ? formatBytes(s.memory_bytes) : '—'}</td>
                    <td className="px-4 py-3 text-gray-600">{formatUtc(s.updated_at_utc)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination offset={offset} limit={limit} total={data.total} onChange={setOffset} />
        </>
      )}
    </div>
  );
}
