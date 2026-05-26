import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { ModuleResultListItem, PaginatedResponse } from '../types/api';
import { Pagination } from '../components/Pagination';
import { StatusBadge } from '../components/StatusBadge';
import { formatUtc, formatMs } from '../lib/format';

export default function ModuleResultsPage() {
  const [offset, setOffset] = useState(0);
  const [deviceId, setDeviceId] = useState('');
  const [moduleId, setModuleId] = useState('');
  const limit = 50;

  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (deviceId) params.set('device_id', deviceId);
  if (moduleId) params.set('module_id', moduleId);

  const { data, isLoading } = useQuery({
    queryKey: ['module-results', offset, deviceId, moduleId],
    queryFn: () => api.get<PaginatedResponse<ModuleResultListItem>>(`/api/admin/modules/results?${params}`),
  });

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold text-gray-900">Module Results</h2>
      <div className="mb-4 flex flex-wrap gap-3">
        <input placeholder="Filter device ID…" value={deviceId} onChange={(e) => { setDeviceId(e.target.value); setOffset(0); }} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none" />
        <input placeholder="Filter module ID…" value={moduleId} onChange={(e) => { setModuleId(e.target.value); setOffset(0); }} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none" />
      </div>
      {isLoading ? <p className="text-sm text-gray-500">Loading…</p> : !data || data.items.length === 0 ? (
        <p className="text-sm text-gray-500">No results found.</p>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3">Device</th>
                  <th className="px-4 py-3">Module</th>
                  <th className="px-4 py-3">Version</th>
                  <th className="px-4 py-3">Success</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3">Output</th>
                  <th className="px-4 py-3">Reported</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-gray-600">{r.device_id}</td>
                    <td className="px-4 py-3 font-mono text-gray-600">{r.module_id}</td>
                    <td className="px-4 py-3 font-mono text-gray-600">{r.module_version}</td>
                    <td className="px-4 py-3"><StatusBadge text={r.status === 'success' ? 'pass' : 'fail'} variant={r.status === 'success' ? 'green' : 'red'} /></td>
                    <td className="px-4 py-3 text-gray-600">{formatMs(r.elapsed_ms)}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-gray-600">{r.output ?? '—'}</td>
                    <td className="px-4 py-3 text-gray-600">{formatUtc(r.finished_at_utc)}</td>
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
