import React, { useState, type FormEvent } from 'react';
import { useParams, useNavigate } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type {
  ModuleDetailResponse,
  AssignModuleRequest,
  PaginatedResponse,
  DeviceListItem,
  ModuleVariableDefItem,
  UpsertVariableDefRequest,
} from '../types/api';
import { ConfirmModal } from '../components/ConfirmModal';
import AssignmentVariablesPanel from '../components/AssignmentVariablesPanel';
import { StatusBadge } from '../components/StatusBadge';
import { toast } from '../components/Toast';
import { formatUtc } from '../lib/format';
import { ApiError } from '../api/client';

export default function ModuleDetailPage() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editing, setEditing] = useState(false);

  const [versionCode, setVersionCode] = useState('');
  const [versionFile, setVersionFile] = useState<File | null>(null);
  const [versionSource, setVersionSource] = useState('');
  const [uploadMode, setUploadMode] = useState<'file' | 'code'>('file');
  const [showVersionForm, setShowVersionForm] = useState(false);

  const [assignDevice, setAssignDevice] = useState('');
  const [assignVersion, setAssignVersion] = useState('');
  const [assignIntervalMs, setAssignIntervalMs] = useState('');
  const [assignTimeoutMs, setAssignTimeoutMs] = useState('');
  const [expandedAssignmentId, setExpandedAssignmentId] = useState<string | null>(null);
  const [expandedVersion, setExpandedVersion] = useState<string | null>(null);
  const [expandedCode, setExpandedCode] = useState<string | null>(null);
  const [varName, setVarName] = useState('');
  const [varType, setVarType] = useState<'string' | 'number' | 'boolean' | 'json'>('string');
  const [varDefaultValue, setVarDefaultValue] = useState('');
  const [varDescription, setVarDescription] = useState('');
  const [varServerCode, setVarServerCode] = useState('');
  const [varError, setVarError] = useState('');
  const [showVariableForm, setShowVariableForm] = useState(false);

  const { data: mod, isLoading } = useQuery({
    queryKey: ['module', moduleId],
    queryFn: () => api.get<ModuleDetailResponse>(`/api/admin/modules/${moduleId}`),
  });

  const { data: devicesPage } = useQuery({
    queryKey: ['devices-all'],
    queryFn: () => api.get<PaginatedResponse<DeviceListItem>>('/api/admin/devices?limit=200'),
  });

  const updateModule = useMutation({
    mutationFn: () => api.put(`/api/admin/modules/${moduleId}`, { description: editDesc }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['module', moduleId] }); setEditing(false); toast('Module updated'); },
  });

  const deleteModule = useMutation({
    mutationFn: () => api.delete(`/api/admin/modules/${moduleId}`),
    onSuccess: () => { toast('Module deleted'); navigate('/modules', { replace: true }); },
  });

  const uploadVersion = useMutation({
    mutationFn: () => {
      if (uploadMode === 'file') {
        const fd = new FormData();
        fd.append('version', versionCode);
        fd.append('file', versionFile!);
        return api.upload(`/api/admin/modules/${moduleId}/versions`, fd);
      }
      return api.post(`/api/admin/modules/${moduleId}/versions`, { version: versionCode, code: versionSource });
    },
    onSuccess: () => {
      clearVersionForm();
      setShowVersionForm(false);
      qc.invalidateQueries({ queryKey: ['module', moduleId] });
      toast('Version uploaded');
    },
  });

  const deleteVersion = useMutation({
    mutationFn: (version: string) => api.delete(`/api/admin/modules/${moduleId}/versions/${version}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['module', moduleId] }); toast('Version deleted'); },
  });

  const assignModule = useMutation({
    mutationFn: () => {
      const trimmedInterval = assignIntervalMs.trim();
      const intervalMs = trimmedInterval ? Number.parseInt(trimmedInterval, 10) : undefined;
      if (trimmedInterval && intervalMs && (!Number.isFinite(intervalMs) || intervalMs <= 0)) {
        throw new Error('Interval must be a positive number.');
      }

      const trimmedTimeout = assignTimeoutMs.trim();
      const timeoutMs = trimmedTimeout ? Number.parseInt(trimmedTimeout, 10) : undefined;
      if (trimmedTimeout && timeoutMs && (!Number.isFinite(timeoutMs) || timeoutMs <= 0)) {
        throw new Error('Timeout must be a positive number.');
      }

      const body: AssignModuleRequest = {
        device_id: assignDevice,
        version: assignVersion,
        interval_ms: intervalMs,
        timeout_ms: timeoutMs,
      };
      return api.post(`/api/admin/modules/${moduleId}/assignments`, body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['module', moduleId] });
      setAssignDevice('');
      setAssignVersion('');
      setAssignIntervalMs('');
      setAssignTimeoutMs('');
      toast('Assigned');
    },
    onError: (err) => {
      toast(err instanceof Error ? err.message : 'Failed to assign module');
    },
  });

  const deleteAssignment = useMutation({
    mutationFn: (assignmentId: string) => api.delete(`/api/admin/modules/${moduleId}/assignments/${assignmentId}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['module', moduleId] }); toast('Unassigned'); },
  });

  const upsertVariable = useMutation({
    mutationFn: () => {
      const trimmedName = varName.trim();
      if (!trimmedName) {
        throw new Error('Variable name is required.');
      }

      const body: UpsertVariableDefRequest = {
        type: varType,
        default_value: varDefaultValue.trim() === '' ? null : varDefaultValue,
        description: varDescription.trim() === '' ? null : varDescription,
        server_code: varServerCode.trim() === '' ? null : varServerCode,
      };
      return api.put<ModuleVariableDefItem>(
        `/api/admin/modules/${moduleId}/variables/${encodeURIComponent(trimmedName)}`,
        body,
      );
    },
    onSuccess: () => {
      clearVariableForm();
      setShowVariableForm(false);
      qc.invalidateQueries({ queryKey: ['module', moduleId] });
      toast('Variable saved');
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setVarError(err.error.message);
        return;
      }
      if (err instanceof Error) {
        setVarError(err.message);
        return;
      }
      setVarError('Failed to save variable');
    },
  });

  const deleteVariable = useMutation({
    mutationFn: (name: string) => api.delete(`/api/admin/modules/${moduleId}/variables/${encodeURIComponent(name)}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['module', moduleId] });
      toast('Variable deleted');
    },
  });

  if (isLoading || !mod) return <p className="text-sm text-gray-500">Loading…</p>;

  const startEdit = () => { setEditName(mod.module_id); setEditDesc(mod.description ?? ''); setEditing(true); };

  const clearVersionForm = () => {
    setVersionCode('');
    setVersionFile(null);
    setVersionSource('');
    setUploadMode('file');
  };

  const startAddVersion = () => {
    clearVersionForm();
    setShowVersionForm(true);
  };

  const clearVariableForm = () => {
    setVarName('');
    setVarType('string');
    setVarDefaultValue('');
    setVarDescription('');
    setVarServerCode('');
    setVarError('');
  };

  const startAddVariable = () => {
    clearVariableForm();
    setShowVariableForm(true);
  };

  const startEditVariable = (v: ModuleVariableDefItem) => {
    setVarName(v.name);
    setVarType((v.type as 'string' | 'number' | 'boolean' | 'json') || 'string');
    setVarDefaultValue(v.default_value ?? '');
    setVarDescription(v.description ?? '');
    setVarServerCode(v.server_code ?? '');
    setVarError('');
    setShowVariableForm(true);
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          {editing ? (
            <form onSubmit={(e: FormEvent) => { e.preventDefault(); updateModule.mutate(); }} className="space-y-2">
              <input
                value={editName}
                readOnly
                disabled
                aria-label="Module ID"
                className="rounded border border-gray-300 bg-gray-100 px-2 py-1 text-lg font-semibold text-gray-600"
              />
              <p className="text-xs text-gray-500">Module ID cannot be changed for an existing module.</p>
              <textarea value={editDesc} onChange={(e) => setEditDesc(e.target.value)} rows={2} className="block w-full sm:w-80 rounded border border-gray-300 px-2 py-1 text-sm" />
              <div className="flex gap-2">
                <button type="submit" disabled={updateModule.isPending} className="rounded bg-blue-600 px-3 py-1 text-sm text-white">Save</button>
                <button type="button" onClick={() => setEditing(false)} className="rounded border border-gray-300 px-3 py-1 text-sm">Cancel</button>
              </div>
            </form>
          ) : (
            <>
              <h2 className="text-xl font-semibold text-gray-900">{mod.module_id}</h2>
              {mod.description && <p className="mt-1 text-sm text-gray-600">{mod.description}</p>}
              <div className="mt-2 flex flex-wrap gap-4 text-sm text-gray-500">
                <span>ID: <code className="text-xs">{mod.module_id}</code></span>
                <span>Entrypoint: {mod.default_entrypoint}</span>
                <span>Created: {formatUtc(mod.created_at_utc)}</span>
              </div>
            </>
          )}
        </div>
        {!editing && (
          <div className="flex shrink-0 gap-2">
            <button onClick={startEdit} className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50">Edit</button>
            <ConfirmModal title="Delete module?" description="All versions and assignments will also be removed." onConfirm={async () => { await deleteModule.mutateAsync(); }}>
              {(open) => <button onClick={open} className="rounded bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700">Delete</button>}
            </ConfirmModal>
          </div>
        )}
      </div>

      {/* Versions */}
      <section className="mb-8">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">Versions</h3>
          <button
            type="button"
            onClick={startAddVersion}
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
          >
            + Add Version
          </button>
        </div>

        {mod.versions.length === 0 ? (
          <p className="text-sm text-gray-500">No versions yet.</p>
        ) : (
          <div className="mb-6 overflow-x-auto rounded-lg border border-gray-200">
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
                  <React.Fragment key={v.version}>
                    <tr className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono">{v.version}</td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-500">{v.package_hash?.slice(0, 16)}…</td>
                      <td className="px-4 py-3 text-gray-600">{formatUtc(v.created_at_utc)}</td>
                      <td className="px-4 py-3 text-right space-x-3">
                        <button
                          onClick={async () => {
                            if (expandedVersion === v.version) { setExpandedVersion(null); setExpandedCode(null); return; }
                            setExpandedVersion(v.version); setExpandedCode(null);
                            const res = await api.get<{ code: string }>(`/api/admin/modules/${moduleId}/versions/${v.version}/code`);
                            setExpandedCode(res.code);
                          }}
                          className="text-blue-600 hover:underline"
                        >
                          {expandedVersion === v.version ? 'Hide' : 'View'}
                        </button>
                        <ConfirmModal title="Delete version?" onConfirm={async () => { await deleteVersion.mutateAsync(v.version); }}>
                          {(open) => <button onClick={open} className="text-red-600 hover:underline">Delete</button>}
                        </ConfirmModal>
                      </td>
                    </tr>
                    {expandedVersion === v.version && (
                      <tr>
                        <td colSpan={4} className="bg-gray-900 px-4 py-3">
                          {expandedCode === null ? (
                            <p className="text-sm text-gray-400">Loading…</p>
                          ) : (
                            <pre className="overflow-x-auto font-mono text-xs leading-relaxed text-gray-200 whitespace-pre-wrap">{expandedCode}</pre>
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {showVersionForm && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h4 className="font-medium text-gray-900">Add Version</h4>
              <button
                type="button"
                onClick={() => { clearVersionForm(); setShowVersionForm(false); }}
                className="text-gray-500 hover:text-gray-700"
              >
                X
              </button>
            </div>

            <div className="mb-3 flex flex-wrap items-end gap-3">
              <div>
                <label className="mb-1 block text-xs text-gray-600">Version</label>
                <input
                  value={versionCode}
                  onChange={(e) => setVersionCode(e.target.value)}
                  placeholder="1.0.0"
                  className="rounded border border-gray-300 px-2 py-1 text-sm"
                />
              </div>
              <div className="flex gap-1">
                <button
                  type="button"
                  onClick={() => setUploadMode('file')}
                  className={`rounded px-2 py-1 text-xs ${uploadMode === 'file' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}
                >
                  File
                </button>
                <button
                  type="button"
                  onClick={() => setUploadMode('code')}
                  className={`rounded px-2 py-1 text-xs ${uploadMode === 'code' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}
                >
                  Code
                </button>
              </div>
            </div>

            {uploadMode === 'file' ? (
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <label className="mb-1 block text-xs text-gray-600">File</label>
                  <input type="file" onChange={(e) => setVersionFile(e.target.files?.[0] ?? null)} className="text-sm" />
                </div>
                <button
                  type="button"
                  onClick={() => uploadVersion.mutate()}
                  disabled={!versionCode || !versionFile || uploadVersion.isPending}
                  className="rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
                >
                  Upload
                </button>
              </div>
            ) : (
              <div>
                <label className="mb-1 block text-xs text-gray-600">Code</label>
                <textarea
                  value={versionSource}
                  onChange={(e) => setVersionSource(e.target.value)}
                  rows={10}
                  className="w-full rounded border border-gray-300 px-2 py-1 font-mono text-sm focus:border-blue-500 focus:outline-none"
                  placeholder={"def run(ctx):\n    pass"}
                />
                {!versionCode && versionSource && (
                  <p className="mt-1 text-xs text-amber-600">Enter a version number above to save.</p>
                )}
                <button
                  type="button"
                  onClick={() => uploadVersion.mutate()}
                  disabled={!versionCode || !versionSource || uploadVersion.isPending}
                  className="mt-2 rounded bg-blue-600 px-3 py-1 text-sm text-white disabled:opacity-50"
                >
                  Save Version
                </button>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Variables */}
      <section className="mb-8">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">Variables</h3>
          <button
            type="button"
            onClick={startAddVariable}
            className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
          >
            + Add Variable
          </button>
        </div>

        {/* Variable List */}
        {(mod.variable_defs ?? []).length === 0 ? (
          <p className="text-sm text-gray-500">No variable definitions yet.</p>
        ) : (
          <div className="mb-6 overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Default</th>
                  <th className="px-4 py-3">Server Code</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(mod.variable_defs ?? []).map((v) => (
                  <tr key={v.name} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono">{v.name}</td>
                    <td className="px-4 py-3">{v.type}</td>
                    <td className="px-4 py-3 font-mono text-xs">{v.default_value ?? '—'}</td>
                    <td className="px-4 py-3">{v.has_server_code ? 'Yes' : 'No'}</td>
                    <td className="px-4 py-3 text-right space-x-3">
                      <button
                        type="button"
                        onClick={() => startEditVariable(v)}
                        className="text-blue-600 hover:underline"
                      >
                        Edit
                      </button>
                      <ConfirmModal title="Delete variable?" onConfirm={async () => { await deleteVariable.mutateAsync(v.name); }}>
                        {(open) => <button onClick={open} className="text-red-600 hover:underline">Delete</button>}
                      </ConfirmModal>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Variable Form (Collapsible) */}
        {showVariableForm && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h4 className="font-medium text-gray-900">{varName.trim() ? `Edit: ${varName}` : 'Add Variable'}</h4>
              <button
                type="button"
                onClick={() => { clearVariableForm(); setShowVariableForm(false); }}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <div className="mb-3 rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-600">
              Server code is scoped per variable. Editing a variable loads its current server code.
            </div>
            {varError && <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">{varError}</p>}

            <div className="grid gap-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label htmlFor="var-name" className="mb-1 block text-xs text-gray-600">Variable name</label>
                  <input
                    id="var-name"
                    value={varName}
                    onChange={(e) => setVarName(e.target.value)}
                    placeholder="e.g. TEMP_THRESHOLD"
                    className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="var-type" className="mb-1 block text-xs text-gray-600">Type</label>
                  <select
                    id="var-type"
                    value={varType}
                    onChange={(e) => setVarType(e.target.value as 'string' | 'number' | 'boolean' | 'json')}
                    className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  >
                    <option value="string">string</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                    <option value="json">json</option>
                  </select>
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label htmlFor="var-default-value" className="mb-1 block text-xs text-gray-600">Default value</label>
                  <input
                    id="var-default-value"
                    value={varDefaultValue}
                    onChange={(e) => setVarDefaultValue(e.target.value)}
                    placeholder="optional"
                    className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                </div>
                <div>
                  <label htmlFor="var-description" className="mb-1 block text-xs text-gray-600">Description</label>
                  <input
                    id="var-description"
                    value={varDescription}
                    onChange={(e) => setVarDescription(e.target.value)}
                    placeholder="optional"
                    className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="var-server-code" className="mb-1 block text-xs text-gray-600">Server code (optional)</label>
                <textarea
                  id="var-server-code"
                  value={varServerCode}
                  onChange={(e) => setVarServerCode(e.target.value)}
                  rows={6}
                  className="w-full rounded border border-gray-300 px-2 py-1 font-mono text-sm"
                  placeholder={"// Example (C# script)\nreturn 42;"}
                />
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => upsertVariable.mutate()}
                  disabled={!varName.trim() || upsertVariable.isPending}
                  className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {upsertVariable.isPending ? 'Saving…' : 'Save'}
                </button>
                <button
                  type="button"
                  onClick={() => { clearVariableForm(); setShowVariableForm(false); }}
                  className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-100"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Assignments */}
      <section>
        <h3 className="mb-3 text-lg font-medium text-gray-900">Assignments</h3>
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <div>
            <label htmlFor="assign-device" className="mb-1 block text-xs text-gray-600">Device</label>
            <select
              id="assign-device"
              value={assignDevice}
              onChange={(e) => setAssignDevice(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1 text-sm min-w-[180px]"
            >
              <option value="">— select device —</option>
              {devicesPage?.items.map((d) => (
                <option key={d.device_id} value={d.device_id}>{d.device_id}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="assign-version" className="mb-1 block text-xs text-gray-600">Version</label>
            <select
              id="assign-version"
              value={assignVersion}
              onChange={(e) => setAssignVersion(e.target.value)}
              className="rounded border border-gray-300 px-2 py-1 text-sm min-w-[130px]"
            >
              <option value="">— select version —</option>
              {mod.versions.map((v) => (
                <option key={v.version} value={v.version}>{v.version}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="assign-interval-ms" className="mb-1 block text-xs text-gray-600">Interval (ms)</label>
            <input
              id="assign-interval-ms"
              type="number"
              min={1}
              value={assignIntervalMs}
              onChange={(e) => setAssignIntervalMs(e.target.value)}
              placeholder="60000"
              className="rounded border border-gray-300 px-2 py-1 text-sm min-w-[130px]"
            />
          </div>
          <div>
            <label htmlFor="assign-timeout-ms" className="mb-1 block text-xs text-gray-600">Timeout (ms)</label>
            <input
              id="assign-timeout-ms"
              type="number"
              min={1}
              value={assignTimeoutMs}
              onChange={(e) => setAssignTimeoutMs(e.target.value)}
              placeholder="5000"
              className="rounded border border-gray-300 px-2 py-1 text-sm min-w-[130px]"
            />
          </div>
          <button
            onClick={() => assignModule.mutate()}
            disabled={!assignDevice || !assignVersion || assignModule.isPending}
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
                  <th className="px-4 py-3">Interval</th>
                  <th className="px-4 py-3">Timeout</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Assigned</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {mod.assignments.map((a) => (
                  <tr key={a.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono">{a.device_id}</td>
                    <td className="px-4 py-3 font-mono">{a.version ?? 'latest'}</td>
                    <td className="px-4 py-3 font-mono text-xs">{a.interval_ms} ms</td>
                    <td className="px-4 py-3 font-mono text-xs">{a.timeout_ms} ms</td>
                    <td className="px-4 py-3">
                      <StatusBadge text={a.enabled ? 'active' : 'disabled'} variant={a.enabled ? 'green' : 'gray'} />
                    </td>
                    <td className="px-4 py-3 text-gray-600">{formatUtc(a.created_at_utc)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-3">
                        <button onClick={() => setExpandedAssignmentId(expandedAssignmentId === a.id ? null : a.id)} className="text-blue-600 hover:underline">Edit variables</button>
                        <ConfirmModal title="Remove assignment?" onConfirm={async () => { await deleteAssignment.mutateAsync(a.id); }}>
                          {(open) => <button onClick={open} className="text-red-600 hover:underline">Remove</button>}
                        </ConfirmModal>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {mod.assignments.map((a) => (
        expandedAssignmentId === a.id ? (
          <div key={`${a.id}-panel`} className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
            <h4 className="mb-3 text-sm font-medium text-gray-900">Variables for {a.device_id}</h4>
            <AssignmentVariablesPanel assignmentId={a.id} />
          </div>
        ) : null
      ))}
    </div>
  );
}
