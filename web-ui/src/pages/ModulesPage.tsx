import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';
import { api } from '../api/client';
import type { ModuleListItem } from '../types/api';
import { formatUtc } from '../lib/format';

export default function ModulesPage() {
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['modules'],
    queryFn: () => api.get<ModuleListItem[]>('/api/admin/modules'),
  });

  const filtered = data?.filter((m) =>
    !search || m.module_id.toLowerCase().includes(search.toLowerCase()) || (m.description ?? '').toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">Modules</h2>
        <Link to="/modules/new" className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">
          Create Module
        </Link>
      </div>

      <input
        type="text"
        placeholder="Search modules…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="mb-4 w-64 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
      />

      {isLoading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : !filtered || filtered.length === 0 ? (
        <p className="text-sm text-gray-500">No modules found.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Module ID</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Versions</th>
                <th className="px-4 py-3">Assignments</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((m) => (
                <tr key={m.module_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link to={`/modules/${m.module_id}`} className="font-mono text-blue-600 hover:underline">{m.module_id}</Link>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{m.description ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{m.version_count}</td>
                  <td className="px-4 py-3 text-gray-600">{m.assignment_count}</td>
                  <td className="px-4 py-3 text-gray-600">{formatUtc(m.created_at_utc)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
