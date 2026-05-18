import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '../api/client';
import type { ModuleVariableValueItem } from '../types/api';
import { ConfirmModal } from './ConfirmModal';
import { toast } from './Toast';

interface Props {
  assignmentId: string;
}

export function AssignmentVariablesPanel({ assignmentId }: Props) {
  const qc = useQueryClient();
  const [editingValues, setEditingValues] = useState<Record<string, string | null>>({});

  const { data, isLoading } = useQuery({
    queryKey: ['assignment-variables', assignmentId],
    queryFn: () => api.get<ModuleVariableValueItem[]>(`/api/admin/modules/assignments/${assignmentId}/variables`),
    enabled: !!assignmentId,
  });

  const saveMutation = useMutation({
    mutationFn: ({ name, value }: { name: string; value: string | null }) =>
      api.put(`/api/admin/modules/assignments/${assignmentId}/variables/${encodeURIComponent(name)}`, { value }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['assignment-variables', assignmentId] }); toast('Saved'); },
    onError: (err) => { if (err instanceof ApiError) toast(err.error.message); else if (err instanceof Error) toast(err.message); else toast('Failed to save'); },
  });

  const deleteMutation = useMutation({
    mutationFn: (name: string) => api.delete(`/api/admin/modules/assignments/${assignmentId}/variables/${encodeURIComponent(name)}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['assignment-variables', assignmentId] }); toast('Override removed'); },
    onError: (err) => { if (err instanceof ApiError) toast(err.error.message); else if (err instanceof Error) toast(err.message); else toast('Failed to delete'); },
  });

  const list = data ?? [];

  const onChangeValue = (name: string, value: string) => {
    setEditingValues((s) => ({ ...s, [name]: value }));
  };

  const currentValue = (item: ModuleVariableValueItem) => {
    if (editingValues.hasOwnProperty(item.variable_name)) return editingValues[item.variable_name];
    return item.value ?? '';
  };

  return (
    <div className="w-full p-6">
      {isLoading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : (
        <div className="rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Source</th>
                <th className="px-4 py-3">Value</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {list.map((it) => (
                <tr key={it.variable_name} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono">{it.variable_name}</td>
                  <td className="px-4 py-3 text-xs text-gray-600">{it.source}</td>
                  <td className="px-4 py-3">
                    {it.source === 'server_computed' ? (
                      <div className="text-sm text-gray-600">{it.value ?? '—'}</div>
                    ) : (
                      <input
                        value={currentValue(it) ?? ''}
                        onChange={(e) => onChangeValue(it.variable_name, e.target.value)}
                        className="w-full rounded border border-gray-300 px-2 py-1 text-sm"
                      />
                    )}
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    {it.source !== 'server_computed' && (
                      <>
                        <button
                          onClick={() => saveMutation.mutate({ name: it.variable_name, value: editingValues[it.variable_name] ?? it.value ?? null })}
                          className="text-blue-600 hover:underline"
                        >
                          Save
                        </button>
                        <ConfirmModal title="Remove override?" onConfirm={() => deleteMutation.mutateAsync(it.variable_name)}>
                          {(open) => <button onClick={open} className="text-red-600 hover:underline">Remove</button>}
                        </ConfirmModal>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default AssignmentVariablesPanel;
