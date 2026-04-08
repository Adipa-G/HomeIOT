import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';
import { api } from '../api/client';
import type { DeviceListItem, PaginatedResponse } from '../types/api';
import { Pagination } from '../components/Pagination';
import { StatusBadge } from '../components/StatusBadge';
import { formatUtc } from '../lib/format';

export default function DevicesPage() {
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const [platform, setPlatform] = useState('');
  const [mode, setMode] = useState('');
  const limit = 50;

  const params = new URLSearchParams({ offset: String(offset), limit: String(limit) });
  if (search) params.set('search', search);
  if (platform) params.set('platform', platform);
  if (mode) params.set('mode', mode);

  const { data, isLoading } = useQuery({
    queryKey: ['devices', offset, search, platform, mode],
    queryFn: () => api.get<PaginatedResponse<DeviceListItem>>(`/api/admin/devices?${params}`),
  });

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold text-gray-900">Devices</h2>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search device ID…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
        />
        <select
          value={platform}
          onChange={(e) => { setPlatform(e.target.value); setOffset(0); }}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All platforms</option>
          <option value="esp32">esp32</option>
          <option value="pico">pico</option>
        </select>
        <select
          value={mode}
          onChange={(e) => { setMode(e.target.value); setOffset(0); }}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All modes</option>
          <option value="production">production</option>
          <option value="development">development</option>
        </select>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : !data || data.items.length === 0 ? (
        <p className="text-sm text-gray-500">No devices found.</p>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3">Device ID</th>
                  <th className="px-4 py-3">Platform</th>
                  <th className="px-4 py-3">Version</th>
                  <th className="px-4 py-3">Mode</th>
                  <th className="px-4 py-3">Last Heartbeat</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.items.map((d) => (
                  <tr key={d.device_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link to={`/devices/${d.device_id}`} className="text-blue-600 hover:underline">
                        {d.device_id}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{d.platform ?? '—'}</td>
                    <td className="px-4 py-3 text-gray-600">{d.version ?? '—'}</td>
                    <td className="px-4 py-3">
                      <StatusBadge
                        text={d.mode}
                        variant={d.mode === 'development' ? 'yellow' : 'green'}
                      />
                    </td>
                    <td className="px-4 py-3 text-gray-600">{formatUtc(d.last_heartbeat_at_utc)}</td>
                    <td className="px-4 py-3 text-gray-600">{formatUtc(d.created_at_utc)}</td>
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
