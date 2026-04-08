import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';
import { api } from '../api/client';
import type { OtaPlatformListItem } from '../types/api';

export default function OtaPlatformsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['ota-platforms'],
    queryFn: () => api.get<OtaPlatformListItem[]>('/api/admin/ota'),
  });

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold text-gray-900">OTA Platforms</h2>
      {isLoading ? <p className="text-sm text-gray-500">Loading…</p> : !data || data.length === 0 ? (
        <p className="text-sm text-gray-500">No platforms found.</p>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
          {data.map((p) => (
            <Link key={p.platform} to={`/ota/${p.platform}`} className="rounded-lg border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-sm">
              <p className="text-lg font-semibold text-gray-900">{p.platform}</p>
              <p className="mt-1 text-sm text-gray-500">{p.release_count} release{p.release_count !== 1 ? 's' : ''}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
