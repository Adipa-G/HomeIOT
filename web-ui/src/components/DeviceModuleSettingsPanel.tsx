import React, { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { ModuleVariableDefItem, ModuleVariableValueItem } from '../types/api';
import { ControlInput } from './ControlInput';
import { toast } from './Toast';

interface DeviceModuleSettingsPanelProps {
  moduleId: string;
  assignmentId: string;
  variableDefs: ModuleVariableDefItem[];
  variableValues: ModuleVariableValueItem[];
  onClose: () => void;
}

export const DeviceModuleSettingsPanel: React.FC<DeviceModuleSettingsPanelProps> = ({
  moduleId,
  assignmentId,
  variableDefs,
  variableValues,
  onClose,
}) => {
  const qc = useQueryClient();
  
  // Fetch fresh variable values from the API
  const { data: freshValues = variableValues } = useQuery({
    queryKey: ['module-assignment-variables', assignmentId],
    queryFn: () => api.get<ModuleVariableValueItem[]>(`/api/admin/modules/assignments/${assignmentId}/variables`),
  });
  
  const [formValues, setFormValues] = useState<Record<string, string | null>>(() => {
    const initial: Record<string, string | null> = {};
    freshValues.forEach((v) => {
      initial[v.variable_name] = v.value;
    });
    return initial;
  });

  // Update form values when freshValues change
  useEffect(() => {
    setFormValues(() => {
      const updated: Record<string, string | null> = {};
      freshValues.forEach((v) => {
        updated[v.variable_name] = v.value;
      });
      return updated;
    });
  }, [freshValues]);

  const saveVariable = useMutation({
    mutationFn: (name: string) => {
      const value = formValues[name];
      return api.put(`/api/admin/modules/assignments/${assignmentId}/variables/${encodeURIComponent(name)}`, { value });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['module-assignment-variables', assignmentId] });
      qc.invalidateQueries({ queryKey: ['module-assignment', assignmentId] });
      toast('Variable updated');
    },
    onError: () => toast('Failed to update variable', 'error'),
  });

  const removeVariable = useMutation({
    mutationFn: (name: string) => {
      return api.delete(`/api/admin/modules/assignments/${assignmentId}/variables/${encodeURIComponent(name)}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['module-assignment-variables', assignmentId] });
      qc.invalidateQueries({ queryKey: ['module-assignment', assignmentId] });
      toast('Variable override removed');
    },
    onError: () => toast('Failed to remove variable', 'error'),
  });

  const controllableVars = variableDefs.filter((v) => v.control_type);

  if (controllableVars.length === 0) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50" onClick={onClose}>
        <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900">Module Settings</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
          </div>
          <p className="text-sm text-gray-500">No controls configured for this module.</p>
          <button
            onClick={onClose}
            className="mt-4 w-full rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4" onClick={onClose}>
      <div className="w-full max-w-md max-h-[90vh] overflow-y-auto rounded-lg bg-white shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="sticky top-0 border-b border-gray-200 bg-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-gray-900">Module Settings</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
          </div>
          <p className="mt-1 text-sm text-gray-500">{moduleId}</p>
        </div>

        <div className="space-y-4 p-6">
          {controllableVars.map((varDef) => {
            const value = formValues[varDef.name];
            const isServerComputed = freshValues.find((v) => v.variable_name === varDef.name)?.source === 'server_computed';

            return (
              <div key={varDef.name} className="rounded-lg border border-gray-200 p-4">
                <ControlInput
                  label={varDef.description || varDef.name}
                  controlType={varDef.control_type}
                  controlOptions={varDef.control_options}
                  value={value}
                  onChange={(newValue) => setFormValues((prev) => ({ ...prev, [varDef.name]: newValue }))}
                  disabled={isServerComputed}
                />
                {isServerComputed && <p className="mt-2 text-xs text-amber-600">This value is computed by the server.</p>}

                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => saveVariable.mutate(varDef.name)}
                    disabled={saveVariable.isPending || isServerComputed}
                    className="flex-1 rounded bg-blue-600 px-2 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {saveVariable.isPending ? 'Saving…' : 'Save'}
                  </button>
                  {!isServerComputed && value !== freshValues.find((v) => v.variable_name === varDef.name)?.value && (
                    <button
                      onClick={() => {
                        removeVariable.mutate(varDef.name);
                        setFormValues((prev) => ({
                          ...prev,
                          [varDef.name]: freshValues.find((v) => v.variable_name === varDef.name)?.value || null,
                        }));
                      }}
                      disabled={removeVariable.isPending}
                      className="flex-1 rounded border border-gray-300 px-2 py-1 text-sm hover:bg-gray-50 disabled:opacity-50"
                    >
                      Reset
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="sticky bottom-0 border-t border-gray-200 bg-gray-50 p-6">
          <button
            onClick={onClose}
            className="w-full rounded border border-gray-300 px-4 py-2 text-sm hover:bg-gray-100"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
