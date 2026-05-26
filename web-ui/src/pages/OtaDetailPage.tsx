import { useParams, useNavigate } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { OtaReleaseDetailResponse } from '../types/api';
import { ConfirmModal } from '../components/ConfirmModal';
import { toast } from '../components/Toast';
import { formatBytes } from '../lib/format';

export default function OtaDetailPage() {
  const { platform, version } = useParams<{ platform: string; version: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['ota-detail', platform, version],
    queryFn: () => api.get<OtaReleaseDetailResponse>(`/api/admin/ota/${platform}/${version}`),
  });

  const deleteRelease = useMutation({
    mutationFn: () => api.delete(`/api/admin/ota/${platform}/${version}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['ota-releases', platform] }); toast('Release deleted'); navigate(`/ota/${platform}`, { replace: true }); },
  });

  if (isLoading || !data) return <p className="text-sm text-gray-500">Loading…</p>;

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">{platform} v{data.version}</h2>
          <p className="mt-1 text-sm text-gray-500">{data.manifest.length} file{data.manifest.length !== 1 ? 's' : ''}</p>
        </div>
        <ConfirmModal title="Delete release?" description={`This will permanently delete ${platform} v${data.version}.`} onConfirm={async () => { await deleteRelease.mutateAsync(); }}>
          {(open) => <button onClick={open} className="rounded bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700">Delete</button>}
        </ConfirmModal>
      </div>

      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">Path</th>
              <th className="px-4 py-3">Size</th>
              <th className="px-4 py-3">SHA256</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.manifest.map((f) => (
              <tr key={f.path} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-mono">{f.path}</td>
                <td className="px-4 py-3 text-gray-600">{formatBytes(f.size_bytes)}</td>
                <td className="px-4 py-3 font-mono text-xs text-gray-500">{f.hash}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
