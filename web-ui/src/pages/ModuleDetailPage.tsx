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
import { DeviceCodeTemplatePicker } from '../components/DeviceCodeTemplatePicker';
import { ServerCodeTemplatePicker } from '../components/ServerCodeTemplatePicker';
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
  const [varControlType, setVarControlType] = useState<string>('');
  const [varControlOptions, setVarControlOptions] = useState('');
  const [varError, setVarError] = useState('');
  const [showVariableForm, setShowVariableForm] = useState(false);
  const [outputVarName, setOutputVarName] = useState('');
  const [outputVarError, setOutputVarError] = useState('');
  const [showQuickAddOutputVariable, setShowQuickAddOutputVariable] = useState(false);
  const [inferringSchema, setInferringSchema] = useState(false);
  const [showVisualizationForm, setShowVisualizationForm] = useState(false);
  const [selectedVarForViz, setSelectedVarForViz] = useState<ModuleVariableDefItem | null>(null);
  const [selectedVizForEdit, setSelectedVizForEdit] = useState<string | null>(null);
  const [vizJsonPath, setVizJsonPath] = useState('');
  const [vizDisplayName, setVizDisplayName] = useState('');
  const [vizType, setVizType] = useState('');
  const [vizConfig, setVizConfig] = useState('{}');
  const [vizError, setVizError] = useState('');

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

      let controlOptions = null;
      if (varControlOptions.trim()) {
        try {
          controlOptions = JSON.parse(varControlOptions);
        } catch {
          throw new Error('Control options must be valid JSON');
        }
      }

      const body: UpsertVariableDefRequest = {
        type: varType,
        default_value: varDefaultValue.trim() === '' ? null : varDefaultValue,
        description: varDescription.trim() === '' ? null : varDescription,
        server_code: varServerCode.trim() === '' ? null : varServerCode,
        control_type: varControlType || null,
        control_options: controlOptions,
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

  const createOutputVariable = useMutation({
    mutationFn: () => {
      const trimmedName = outputVarName.trim();
      if (!trimmedName) {
        throw new Error('Output variable name is required.');
      }
      const body: UpsertVariableDefRequest = {
        type: 'json',
        default_value: null,
        description: null,
        server_code: null,
        control_type: null,
        control_options: null,
      };
      return api.put<ModuleVariableDefItem>(
        `/api/admin/modules/${moduleId}/variables/${encodeURIComponent(trimmedName)}`,
        body,
      );
    },
    onSuccess: () => {
      setOutputVarName('');
      setOutputVarError('');
      setShowQuickAddOutputVariable(false);
      qc.invalidateQueries({ queryKey: ['module', moduleId] });
      toast('Output variable created');
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setOutputVarError(err.error.message);
        return;
      }
      if (err instanceof Error) {
        setOutputVarError(err.message);
        return;
      }
      setOutputVarError('Failed to create output variable');
    },
  });

  const inferSchema = useMutation({
    mutationFn: (varName: string) => api.post(`/api/admin/modules/${moduleId}/variables/${encodeURIComponent(varName)}/infer-schema`, {}),
    onSuccess: async () => {
      // Refetch the module data to get the updated schema from the server
      await qc.refetchQueries({ queryKey: ['module', moduleId] });
      toast('Schema inferred! Available fields are now visible when adding visualizations.');
    },
    onError: () => toast('Failed to infer schema (no recent execution results found)', 'error'),
  });

  const upsertVisualization = useMutation({
    mutationFn: () => {
      if (!selectedVarForViz) throw new Error('No variable selected');
      if (!vizJsonPath.trim()) throw new Error('JSON path is required');
      if (!vizDisplayName.trim()) throw new Error('Display name is required');

      const config = vizConfig.trim() ? JSON.parse(vizConfig) : {};
      const body = {
        json_path: vizJsonPath.trim(),
        display_name: vizDisplayName.trim(),
        visualization_type: vizType || null,
        visualization_config: config || null,
      };
      
      if (selectedVizForEdit) {
        // Update existing visualization
        return api.put(
          `/api/admin/modules/${moduleId}/variables/${encodeURIComponent(selectedVarForViz.name)}/visualizations/${selectedVizForEdit}`,
          body,
        );
      } else {
        // Create new visualization
        return api.post(
          `/api/admin/modules/${moduleId}/variables/${encodeURIComponent(selectedVarForViz.name)}/visualizations`,
          body,
        );
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['module', moduleId] });
      clearVisualizationForm();
      toast(selectedVizForEdit ? 'Visualization updated' : 'Visualization created');
    },
    onError: (err) => {
      if (err instanceof Error) setVizError(err.message);
      else setVizError(selectedVizForEdit ? 'Failed to update visualization' : 'Failed to create visualization');
    },
  });

  const deleteVisualization = useMutation({
    mutationFn: (vizId: string) => {
      if (!selectedVarForViz) throw new Error('No variable selected');
      return api.delete(
        `/api/admin/modules/${moduleId}/variables/${encodeURIComponent(selectedVarForViz.name)}/visualizations/${vizId}`,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['module', moduleId] });
      toast('Visualization deleted');
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

  const getVisualizationHints = (type: string) => {
    switch (type) {
      case 'gauge':
        return 'Configure: min, max, unit, decimals, thresholds (array of {value, color})';
      case 'progress_bar':
        return 'Configure: min, max, unit, decimals';
      case 'number_display':
        return 'Configure: min, max, unit, decimals (shows range)';
      case 'text_display':
        return 'Configure: unit, prefix, suffix';
      case 'bar_chart':
        return 'Configure: min, max, unit, decimals, barColor, historyPoints';
      case 'line_chart':
        return 'Configure: min, max, unit, decimals, lineColor, fillColor, historyPoints';
      default:
        return 'Select a visualization type to see configuration options';
    }
  };

  const getDefaultVisualizationConfig = (type: string): object => {
    switch (type) {
      case 'gauge':
        return { min: 0, max: 100, unit: '', decimals: 1, thresholds: [{ value: 0, color: '#6b926d'}, {value: 50, color: '#f59e0b'}, {value: 80, color: '#ef4444'}] };
      case 'progress_bar':
        return { min: 0, max: 100, unit: '', decimals: 1, thresholds: [{ value: 0, color: '#6b926d'}, {value: 50, color: '#f59e0b'}, {value: 80, color: '#ef4444'}] };
      case 'number_display':
        return { min: 0, max: 100, unit: '', decimals: 1, thresholds: [{ value: 0, color: '#6b926d'}, {value: 50, color: '#f59e0b'}, {value: 80, color: '#ef4444'}] };
      case 'text_display':
        return { unit: '', prefix: '', suffix: '' };
      case 'bar_chart':
        return { min: 0, max: 100, unit: '', decimals: 1, barColor: '#3b82f6', historyPoints: 10, thresholds: [{ value: 0, color: '#6b926d'}, {value: 50, color: '#f59e0b'}, {value: 80, color: '#ef4444'}] };
      case 'line_chart':
        return { min: 0, max: 100, unit: '', decimals: 1, lineColor: '#3b82f6', fillColor: '#3b82f60d', historyPoints: 10, thresholds: [{ value: 0, color: '#6b926d'}, {value: 50, color: '#f59e0b'}, {value: 80, color: '#ef4444'}] };
      default:
        return {};
    }
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
    setVarControlType('');
    setVarControlOptions('');
    setVarError('');
  };

  const clearVisualizationForm = () => {
    setSelectedVizForEdit(null);
    setSelectedVarForViz(null);
    setVizJsonPath('');
    setVizDisplayName('');
    setVizType('');
    setVizConfig('{}');
    setVizError('');
    setShowVisualizationForm(false);
  };

  const startAddVariable = () => {
    clearVariableForm();
    setShowVariableForm(true);
  };

  const startAddOutputVariable = () => {
    setOutputVarName('');
    setOutputVarError('');
    setShowQuickAddOutputVariable(true);
  };

  const startEditVariable = (v: ModuleVariableDefItem) => {
    setVarName(v.name);
    setVarType((v.type as 'string' | 'number' | 'boolean' | 'json') || 'string');
    setVarDefaultValue(v.default_value ?? '');
    setVarDescription(v.description ?? '');
    setVarServerCode(v.server_code ?? '');
    setVarControlType(v.control_type ?? '');
    setVarControlOptions(Array.isArray(v.control_options) ? JSON.stringify(v.control_options) : '');
    setVarError('');
    setShowVariableForm(true);
  };

  const startAddVisualization = (varDef: ModuleVariableDefItem) => {
    clearVisualizationForm();
    // Directly fetch the latest data and update the query cache
    api.get<ModuleDetailResponse>(`/api/admin/modules/${moduleId}`).then(freshData => {
      qc.setQueryData(['module', moduleId], freshData);
      const freshVar = freshData?.variable_defs?.find(v => v.name === varDef.name);
      setSelectedVarForViz(freshVar || varDef);
      setShowVisualizationForm(true);
    });
  };

  const startEditVisualization = (varDef: ModuleVariableDefItem, viz: any) => {
    clearVisualizationForm();
    // Directly fetch the latest data and update the query cache
    api.get<ModuleDetailResponse>(`/api/admin/modules/${moduleId}`).then(freshData => {
      qc.setQueryData(['module', moduleId], freshData);
      const freshVar = freshData?.variable_defs?.find(v => v.name === varDef.name);
      setSelectedVarForViz(freshVar || varDef);
      setSelectedVizForEdit(viz.id);
      setVizJsonPath(viz.json_path);
      setVizDisplayName(viz.display_name);
      setVizType(viz.visualization_type || '');
      setVizConfig(viz.visualization_config ? JSON.stringify(viz.visualization_config) : '{}');
      setShowVisualizationForm(true);
    });
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
              <DeviceCodeTemplatePicker
                onSelect={(code) => {
                  setVersionSource(code);
                  setUploadMode('code');
                }}
              >
                {(openPicker) => (
                  <button
                    type="button"
                    onClick={openPicker}
                    className="rounded bg-blue-600 px-2 py-1 text-xs font-medium text-white hover:bg-blue-700"
                  >
                    Use a template
                  </button>
                )}
              </DeviceCodeTemplatePicker>
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
        {/* Separate variables into control and output */}
        {(() => {
          const allVars = mod.variable_defs ?? [];
          const controlVars = allVars.filter(v => v.control_type);
          const outputVars = allVars.filter(v => !v.control_type);

          return (
            <>
              {/* Control Variables */}
              <div className="mb-8">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">Input Variables {controlVars.length > 0 && <span className="text-sm font-normal text-gray-500">({controlVars.length})</span>}</h3>
                  <button
                    type="button"
                    onClick={startAddVariable}
                    className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700"
                  >
                    + Add Input Variable
                  </button>
                </div>

                {controlVars.length === 0 ? (
                  <p className="text-sm text-gray-500">No input variables yet.</p>
                ) : (
                  <div className="mb-6 overflow-x-auto rounded-lg border border-gray-200">
                    <table className="w-full text-left text-sm">
                      <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                        <tr>
                          <th className="px-4 py-3">Name</th>
                          <th className="px-4 py-3">Type</th>
                          <th className="px-4 py-3">Control</th>
                          <th className="px-4 py-3">Server Code</th>
                          <th className="px-4 py-3"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {controlVars.map((v) => (
                          <tr key={v.name} className="hover:bg-gray-50">
                            <td className="px-4 py-3 font-mono">{v.name}</td>
                            <td className="px-4 py-3">{v.type}</td>
                            <td className="px-4 py-3 text-xs">{v.control_type ? `${v.control_type}` : '—'}</td>
                            <td className="px-4 py-3">{v.has_server_code ? 'Yes' : 'No'}</td>
                            <td className="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                              <button
                                type="button"
                                onClick={() => startEditVariable(v)}
                                className="text-blue-600 hover:underline text-xs"
                              >
                                Edit
                              </button>
                              <ConfirmModal title="Delete variable?" onConfirm={async () => { await deleteVariable.mutateAsync(v.name); }}>
                                {(open) => <button onClick={open} className="text-red-600 hover:underline text-xs">Delete</button>}
                              </ConfirmModal>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

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
                      <div className="mb-1 flex items-center justify-between">
                        <label htmlFor="var-server-code" className="block text-xs text-gray-600">Server code (optional)</label>
                        <ServerCodeTemplatePicker onSelect={(code) => setVarServerCode(code)}>
                          {(openPicker) => (
                            <button
                              type="button"
                              onClick={openPicker}
                              className="rounded bg-blue-600 px-2 py-1 text-xs font-medium text-white hover:bg-blue-700"
                            >
                              Use a template
                            </button>
                          )}
                        </ServerCodeTemplatePicker>
                      </div>
                      <textarea
                        id="var-server-code"
                        value={varServerCode}
                        onChange={(e) => setVarServerCode(e.target.value)}
                        rows={6}
                        className="w-full rounded border border-gray-300 px-2 py-1 font-mono text-sm"
                        placeholder={"// Example (C# script)\nreturn 42;"}
                      />
                    </div>
                    <hr className="my-2" />
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div>
                        <label htmlFor="var-control-type" className="mb-1 block text-xs text-gray-600">Control type (optional)</label>
                        <select
                          id="var-control-type"
                          value={varControlType}
                          onChange={(e) => setVarControlType(e.target.value)}
                          className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                        >
                          <option value="">— none —</option>
                          <option value="text">text input</option>
                          <option value="dropdown">dropdown</option>
                          <option value="toggle">toggle</option>
                        </select>
                      </div>
                      {varControlType === 'dropdown' && (
                        <div>
                          <label htmlFor="var-control-options" className="mb-1 block text-xs text-gray-600">Dropdown options (JSON array)</label>
                          <input
                            id="var-control-options"
                            value={varControlOptions}
                            onChange={(e) => setVarControlOptions(e.target.value)}
                            placeholder='["Option1", "Option2", "Option3"]'
                            className="w-full rounded border border-gray-300 px-2 py-1 text-sm font-mono"
                          />
                        </div>
                      )}
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

              {/* Output Variables */}
              <div className="mb-8">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-lg font-medium text-gray-900">Output Variables {outputVars.length > 0 && <span className="text-sm font-normal text-gray-500">({outputVars.length})</span>}</h3>
                  <button
                    type="button"
                    onClick={startAddOutputVariable}
                    className="rounded bg-green-600 px-3 py-1 text-sm text-white hover:bg-green-700"
                  >
                    + Add Output Variable
                  </button>
                </div>

                {outputVars.length === 0 ? (
                  <p className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">
                    No output variables yet. Output variables are used for displaying module execution results with visualizations and schema inference.
                  </p>
                ) : (
                  <div className="overflow-x-auto rounded-lg border border-gray-200">
                    <table className="w-full text-left text-sm">
                      <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                        <tr>
                          <th className="px-4 py-3">Name</th>
                          <th className="px-4 py-3">Type</th>
                          <th className="px-4 py-3">Description</th>
                          <th className="px-4 py-3"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {outputVars.map((v) => (
                          <tr key={v.name} className="hover:bg-gray-50">
                            <td className="px-4 py-3 font-mono">{v.name}</td>
                            <td className="px-4 py-3">{v.type}</td>
                            <td className="px-4 py-3 text-xs text-gray-600">{v.description || '—'}</td>
                            <td className="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                              <button
                                type="button"
                                onClick={() => startAddVisualization(v)}
                                className="text-green-600 hover:underline text-xs"
                              >
                                Visualizations
                              </button>
                              <button
                                type="button"
                                onClick={() => {
                                  setInferringSchema(true);
                                  inferSchema.mutate(v.name, {
                                    onSettled: () => setInferringSchema(false),
                                  });
                                }}
                                disabled={inferringSchema}
                                className="text-amber-600 hover:underline text-xs disabled:opacity-50"
                                title="Infer JSON structure from latest execution result"
                              >
                                Schema
                              </button>
                              <ConfirmModal title="Delete output variable?" description="Visualizations will also be removed." onConfirm={async () => { await deleteVariable.mutateAsync(v.name); }}>
                                {(open) => <button onClick={open} className="text-red-600 hover:underline text-xs">Delete</button>}
                              </ConfirmModal>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          );
        })()}

        {/* Quick Add Output Variable Form */}
        {showQuickAddOutputVariable && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h4 className="font-medium text-gray-900">Add Output Variable</h4>
              <button
                type="button"
                onClick={() => { setOutputVarName(''); setOutputVarError(''); setShowQuickAddOutputVariable(false); }}
                className="text-gray-500 hover:text-gray-700"
              >
                ✕
              </button>
            </div>

            <div className="mb-3 rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-600">
              Output variables display module execution results. They are automatically configured for visualizations and schema inference.
            </div>
            {outputVarError && <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">{outputVarError}</p>}

            <div className="grid gap-3">
              <div>
                <label htmlFor="output-var-name" className="mb-1 block text-xs text-gray-600">Variable name</label>
                <input
                  id="output-var-name"
                  value={outputVarName}
                  onChange={(e) => setOutputVarName(e.target.value)}
                  placeholder="e.g. SENSOR_OUTPUT"
                  className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  autoFocus
                />
              </div>
            </div>

            <div className="flex gap-2 pt-3">
              <button
                type="button"
                onClick={() => createOutputVariable.mutate()}
                disabled={!outputVarName.trim() || createOutputVariable.isPending}
                className="rounded bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 disabled:opacity-50"
              >
                {createOutputVariable.isPending ? 'Creating…' : 'Create'}
              </button>
              <button
                type="button"
                onClick={() => { setOutputVarName(''); setOutputVarError(''); setShowQuickAddOutputVariable(false); }}
                className="rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-100"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Visualization Management Modal */}
        {showVisualizationForm && selectedVarForViz && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
            <div className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-lg bg-white shadow-xl">
              <div className="sticky top-0 border-b border-gray-200 bg-white p-6">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-900">{selectedVizForEdit ? 'Edit' : 'Add'} Visualization</h3>
                  <button onClick={clearVisualizationForm} className="text-gray-400 hover:text-gray-600">✕</button>
                </div>
                <p className="mt-1 text-xs text-gray-500">Variable: {selectedVarForViz.name}</p>
                {!selectedVizForEdit && selectedVarForViz.inferred_json_schema !== null && selectedVarForViz.inferred_json_schema !== undefined && (
                  (() => {
                    const schema = selectedVarForViz.inferred_json_schema;
                    const schemaStr = typeof schema === 'string' ? schema : JSON.stringify(schema);
                    const hasContent = schemaStr && schemaStr.length > 2; // More than just '{}'
                    return hasContent ? (
                      <div className="mt-2 rounded bg-blue-50 p-3">
                        <p className="mb-2 text-xs font-semibold text-blue-900">Inferred Schema:</p>
                        <pre className="overflow-x-auto text-xs text-blue-700 font-mono bg-white rounded p-2 border border-blue-200 max-h-32">
                          {schemaStr}
                        </pre>
                      </div>
                    ) : (
                      <div className="mt-2 rounded bg-amber-50 p-2">
                        <p className="text-xs text-amber-700">No schema inferred yet. Click <strong>Schema</strong> button to analyze recent execution results.</p>
                      </div>
                    );
                  })()
                )}
              </div>

              <div className="space-y-4 p-6">
                {vizError && <p className="rounded bg-red-50 p-2 text-sm text-red-700">{vizError}</p>}

                <div>
                  <label htmlFor="viz-json-path" className="mb-1 block text-xs text-gray-600">JSON Path</label>
                  <input
                    id="viz-json-path"
                    value={vizJsonPath}
                    onChange={(e) => setVizJsonPath(e.target.value)}
                    placeholder="e.g. temp, sensor_data.temperature"
                    className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                  <p className="mt-1 text-xs text-gray-500">Specify the field to extract from variable output.</p>
                </div>

                <div>
                  <label htmlFor="viz-display-name" className="mb-1 block text-xs text-gray-600">Display Name</label>
                  <input
                    id="viz-display-name"
                    value={vizDisplayName}
                    onChange={(e) => setVizDisplayName(e.target.value)}
                    placeholder="e.g. Temperature"
                    className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                </div>

                <div>
                  <label htmlFor="viz-type" className="mb-1 block text-xs text-gray-600">Visualization Type</label>
                  <select
                    id="viz-type"
                    value={vizType}
                    onChange={(e) => setVizType(e.target.value)}
                    className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                  >
                    <option value="">— select —</option>
                    <option value="gauge">Gauge</option>
                    <option value="progress_bar">Progress Bar</option>
                    <option value="number_display">Number Display</option>
                    <option value="text_display">Text Display</option>
                    <option value="line_chart">Line Chart</option>
                    <option value="bar_chart">Bar Chart</option>
                  </select>
                </div>

                <div>
                  <div className="mb-1 flex items-center justify-between">
                    <label htmlFor="viz-config" className="text-xs text-gray-600">Configuration (JSON)</label>
                    {vizType && (vizConfig === '{}' || vizConfig.trim() === '') && (
                      <button
                        type="button"
                        onClick={() => setVizConfig(JSON.stringify(getDefaultVisualizationConfig(vizType), null, 2))}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        + Add default
                      </button>
                    )}
                  </div>
                  <textarea
                    id="viz-config"
                    value={vizConfig}
                    onChange={(e) => setVizConfig(e.target.value)}
                    rows={4}
                    className="w-full rounded border border-gray-300 px-2 py-1 font-mono text-xs"
                    placeholder={'{"min": 0, "max": 100, "unit": "°C"}'}
                  />
                  <p className="mt-1 text-xs text-gray-500">{getVisualizationHints(vizType)}</p>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => upsertVisualization.mutate()}
                    disabled={upsertVisualization.isPending}
                    className="flex-1 rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {upsertVisualization.isPending ? 'Saving…' : selectedVizForEdit ? 'Update' : 'Create'}
                  </button>
                  {selectedVizForEdit && (
                    <button
                      onClick={() => {
                        if (selectedVizForEdit) {
                          deleteVisualization.mutate(selectedVizForEdit, {
                            onSuccess: () => clearVisualizationForm(),
                          });
                        }
                      }}
                      disabled={deleteVisualization.isPending}
                      className="flex-1 rounded bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-50"
                    >
                      {deleteVisualization.isPending ? 'Deleting…' : 'Delete'}
                    </button>
                  )}
                  <button
                    onClick={clearVisualizationForm}
                    className="flex-1 rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                </div>
              </div>

              {/* Existing Visualizations - Only show if not currently editing */}
              {!selectedVizForEdit && (selectedVarForViz.visualizations ?? []).length > 0 && (
                <div className="border-t border-gray-200 p-6">
                  <h4 className="mb-3 font-medium text-gray-900">Existing Visualizations</h4>
                  <div className="space-y-2">
                    {selectedVarForViz.visualizations!.map((viz) => (
                      <div key={viz.id} className="flex items-center justify-between rounded border border-gray-200 p-2">
                        <div className="text-xs">
                          <p className="font-mono">{viz.json_path}</p>
                          <p className="text-gray-600">{viz.display_name}</p>
                        </div>
                        <button
                          onClick={() => startEditVisualization(selectedVarForViz, viz)}
                          className="text-blue-600 hover:underline text-xs"
                        >
                          Edit
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
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
