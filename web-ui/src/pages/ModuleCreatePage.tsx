import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';
import { useMutation } from '@tanstack/react-query';
import { api } from '../api/client';
import type { CreateModuleRequest, ModuleDetailResponse } from '../types/api';
import { toast } from '../components/Toast';
import { ApiError } from '../api/client';
import { ModuleTemplatePicker } from '../components/ModuleTemplatePicker';

export default function ModuleCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<CreateModuleRequest>({ module_id: '', description: '' });
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: () => api.post<ModuleDetailResponse>('/api/admin/modules', form),
    onSuccess: (data) => { toast('Module created'); navigate(`/modules/${data.module_id}`, { replace: true }); },
    onError: (err) => setError(err instanceof ApiError ? err.error.message : 'Failed to create'),
  });

  const handleSubmit = (e: FormEvent) => { e.preventDefault(); setError(''); mutation.mutate(); };

  return (
    <div className="max-w-lg">
      <h2 className="mb-6 text-xl font-semibold text-gray-900">Create Module</h2>
      {error && <p className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Module ID</label>
          <input
            type="text"
            required
            value={form.module_id}
            onChange={(e) => setForm({ ...form, module_id: e.target.value })}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="e.g. sensor-reader"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Description</label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={3}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Version <span className="text-gray-400 font-normal">(optional)</span></label>
          <input
            type="text"
            value={form.version ?? ''}
            onChange={(e) => setForm({ ...form, version: e.target.value || undefined })}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="e.g. 1.0.0"
          />
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between">
            <label className="block text-sm font-medium text-gray-700">Code <span className="text-gray-400 font-normal">(optional)</span></label>
            <ModuleTemplatePicker
              onSelect={(code) => setForm((f) => ({ ...f, code, version: f.version || '1.0.0' }))}
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
            </ModuleTemplatePicker>
          </div>
          <textarea
            value={form.code ?? ''}
            onChange={(e) => setForm({ ...form, code: e.target.value || undefined })}
            rows={10}
            className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none"
            placeholder="def run(ctx):&#10;    pass"
          />
          {form.code && !form.version && (
            <p className="mt-1 text-xs text-amber-600">Version is required when code is provided.</p>
          )}
        </div>
        <button
          type="submit"
          disabled={mutation.isPending}
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {mutation.isPending ? 'Creating…' : 'Create Module'}
        </button>
      </form>
    </div>
  );
}
