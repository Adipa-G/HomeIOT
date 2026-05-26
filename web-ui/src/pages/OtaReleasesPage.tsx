import { useState } from 'react';
import { useParams, Link } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { OtaReleaseListItem } from '../types/api';
import { toast } from '../components/Toast';
import { formatBytes } from '../lib/format';

export default function OtaReleasesPage() {
  const { platform } = useParams<{ platform: string }>();
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['ota-releases', platform],
    queryFn: () => api.get<OtaReleaseListItem[]>(`/api/admin/ota/${platform}`),
  });

  const upload = useMutation({
    mutationFn: () => {
      const version = file!.name.replace(/\.zip$/i, '');
      const fd = new FormData();
      fd.append('file', file!);
      return api.upload(`/api/admin/ota/${platform}/${version}`, fd);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['ota-releases', platform] }); setFile(null); toast('Release uploaded'); },
  });

  return (
    <div>
      <h2 className="mb-4 text-xl font-semibold text-gray-900">{platform} Releases</h2>

      {/* Upload */}
      <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg border border-gray-200 bg-white p-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Upload ZIP</label>
          <input type="file" accept=".zip" onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-sm" />
        </div>
        <button
          onClick={() => upload.mutate()}
          disabled={!file || upload.isPending}
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {upload.isPending ? 'Uploading…' : 'Upload'}
        </button>
      </div>

      {isLoading ? <p className="text-sm text-gray-500">Loading…</p> : !data || data.length === 0 ? (
        <p className="text-sm text-gray-500">No releases found.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Version</th>
                <th className="px-4 py-3">Files</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((r) => (
                <tr key={r.version} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link to={`/ota/${platform}/${r.version}`} className="font-mono text-blue-600 hover:underline">{r.version}</Link>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{r.file_count}</td>
                  <td className="px-4 py-3 text-gray-600">{formatBytes(r.total_size_bytes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
