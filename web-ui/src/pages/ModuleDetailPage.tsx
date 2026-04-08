import { useState, type FormEvent } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { ModuleDetailResponse, AssignModuleRequest } from '../types/api';
import { ConfirmModal } from '../components/ConfirmModal';
import { StatusBadge } from '../components/StatusBadge';
import { toast } from '../components/Toast';
import { formatUtc } from '../lib/format';

export default function ModuleDetailPage() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editing, setEditing] = useState(false);

  const [versionCode, setVersionCode] = useState('');
  const [versionFile, setVersionFile] = useState<File | null>(null);

  const [assignDevice, setAssignDevice] = useState('');
  const [assignVersion, setAssignVersion] = useState('');

  const { data: mod, isLoading } = useQuery({
    queryKey: ['module', moduleId],
    queryFn: () => api.get<ModuleDetailResponse>(`/api/admin/modules/${moduleId}`),
  });

  const updateModule = useMutation({
    mutationFn: () => api.put(`/api/admin/modules/${moduleId}`, { name: editName, description: editDesc }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['module', moduleId] }); setEditing(false); toast('Module updated'); },
  });

  const deleteModule = useMutation({
    mutationFn: () => api.delete(`/api/admin/modules/${moduleId}`),
    onSuccess: () => { toast('Module deleted'); navigate('/modules', { replace: true }); },
  });

  const uploadVersion = useMutation({
    mutationFn: () => {
      const fd = new FormData();
      fd.append('version', versionCode);
      fd.append('file', versionFile!);
      return api.upload(`/api/admin/modules/${moduleId}/versions`, fd);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['module', moduleId] }); setVersionCode(''); setVersionFile(null); toast('Version uploaded'); },
  });

  const deleteVersion = useMutation({
    mutationFn: (version: string) => api.delete(`/api/admin/modules/${moduleId}/versions/${version}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['module', moduleId] }); toast('Version deleted'); },
  });

  const assignModule = useMutation({
    mutationFn: () => {
      const body: AssignModuleRequest = { device_id: assignDevice, version: assignVersion || undefined };
      return api.post(`/api/admin/modules/${moduleId}/assignments`, body);
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['module', moduleId] }); setAssignDevice(''); setAssignVersion(''); toast('Assigned'); },
  });

  const deleteAssignment = useMutation({
    mutationFn: (assignmentId: string) => api.delete(`/api/admin/modules/${moduleId}/assignments/${assignmentId}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['module', moduleId] }); toast('Unassigned'); },
  });

  if (isLoading || !mod) return <p className="text-sm text-gray-500">Loading…</p>;

  const startEdit = () => { setEditName(mod.name); setEditDesc(mod.description ?? ''); setEditing(true); };

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          {editing ? (
            <form onSubmit={(e: FormEvent) => { e.preventDefault(); updateModule.mutate(); }} className="space-y-2">
              <input value={editName} onChange={(e) => setEditName(e.target.value)} className="rounded border border-gray-300 px-2 py-1 text-lg font-semibold" />
              <textarea value={editDesc} onChange={(e) => setEditDesc(e.target.value)} rows={2} className="block w-80 rounded border border-gray-300 px-2 py-1 text-sm" />
              <div className="flex gap-2">
                <button type="submit" disabled={updateModule.isPending} className="rounded bg-blue-600 px-3 py-1 text-sm text-white">Save</button>
                <button type="button" onClick={() => setEditing(false)} className="rounded border border-gray-300 px-3 py-1 text-sm">Cancel</button>
              </div>
            </form>
          ) : (
            <>
              <h2 className="text-xl font-semibold text-gray-900">{mod.name}</h2>
              {mod.description && <p className="mt-1 text-sm text-gray-600">{mod.description}</p>}
              <div className="mt-2 flex flex-wrap gap-4 text-sm text-gray-500">
                <span>ID: <code className="text-xs">{mod.module_id}</code></span>
                <span>Platform: {mod.platform}</span>
                <span>Created: {formatUtc(mod.created_at_utc)}</span>
              </div>
            </>
          )}
        </div>
        {!editing && (
          <div className="flex gap-2">
            <button onClick={startEdit} className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50">Edit</button>
            <ConfirmModal title="Delete module?" description="All versions and assignments will also be removed." onConfirm={() => deleteModule.mutateAsync()}>
              {(open) => <button onClick={open} className="rounded bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700">Delete</button>}
            </ConfirmModal>
          </div>
        )}
      </div>

      {/* Versions */}
      <section className="mb-8">
        <h3 className="mb-3 text-lg font-medium text-gray-900">Versions</h3>
        <div className="mb-3 flex items-end gap-3">
          <div>
            <label className="mb-1 block text-xs text-gray-600">Version</label>
            <input value={versionCode} onChange={(e) => setVersionCode(e.target.value)} placeholder="1.0.0" className="rounded border border-gray-300 px-2 py-1 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-600">File</label>
            <input type="file" onChange={(e) => setVersionFile(e.target.files?.[0] ?? null)} className="text-sm" />
          </div>
          <button
            onClick={() => uploadVersion.mutate()}
            disabled={!versionCode || !versionFile || uploadVersion.isPending}
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
          >
            Upload
          </button>
        </div>
        {mod.versions.length === 0 ? (
          <p className="text-sm text-gray-500">No versions yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3">Version</th>
                  <th className="px-4 py-3">SHA256</th>
                  <th className="px-4 py-3">Uploaded</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {mod.versions.map((v) => (
                  <tr key={v.version} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono">{v.version}</td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{v.sha256?.slice(0, 16)}…</td>
                    <td className="px-4 py-3 text-gray-600">{formatUtc(v.created_at_utc)}</td>
                    <td className="px-4 py-3 text-right">
                      <ConfirmModal title="Delete version?" onConfirm={() => deleteVersion.mutateAsync(v.version)}>
                        {(open) => <button onClick={open} className="text-red-600 hover:underline">Delete</button>}
                      </ConfirmModal>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Assignments */}
      <section>
        <h3 className="mb-3 text-lg font-medium text-gray-900">Assignments</h3>
        <div className="mb-3 flex items-end gap-3">
          <div>
            <label className="mb-1 block text-xs text-gray-600">Device ID</label>
            <input value={assignDevice} onChange={(e) => setAssignDevice(e.target.value)} className="rounded border border-gray-300 px-2 py-1 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-600">Version (optional)</label>
            <input value={assignVersion} onChange={(e) => setAssignVersion(e.target.value)} placeholder="latest" className="rounded border border-gray-300 px-2 py-1 text-sm" />
          </div>
          <button
            onClick={() => assignModule.mutate()}
            disabled={!assignDevice || assignModule.isPending}
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
          >
            Assign
          </button>
        </div>
        {mod.assignments.length === 0 ? (
          <p className="text-sm text-gray-500">No assignments.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3">Device</th>
                  <th className="px-4 py-3">Version</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Assigned</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {mod.assignments.map((a) => (
                  <tr key={a.assignment_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono">{a.device_id}</td>
                    <td className="px-4 py-3 font-mono">{a.version ?? 'latest'}</td>
                    <td className="px-4 py-3">
                      <StatusBadge text={a.status} variant={a.status === 'active' ? 'green' : a.status === 'pending' ? 'yellow' : 'gray'} />
                    </td>
                    <td className="px-4 py-3 text-gray-600">{formatUtc(a.assigned_at_utc)}</td>
                    <td className="px-4 py-3 text-right">
                      <ConfirmModal title="Remove assignment?" onConfirm={() => deleteAssignment.mutateAsync(a.assignment_id)}>
                        {(open) => <button onClick={open} className="text-red-600 hover:underline">Remove</button>}
                      </ConfirmModal>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
