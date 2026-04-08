import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';
import { useMutation } from '@tanstack/react-query';
import { api } from '../api/client';
import type { CreateModuleRequest, ModuleDetailResponse } from '../types/api';
import { toast } from '../components/Toast';
import { ApiError } from '../api/client';

export default function ModuleCreatePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<CreateModuleRequest>({ name: '', platform: 'esp32', description: '' });
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
          <label className="mb-1 block text-sm font-medium text-gray-700">Name</label>
          <input
            type="text"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Platform</label>
          <select
            value={form.platform}
            onChange={(e) => setForm({ ...form, platform: e.target.value })}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="esp32">esp32</option>
            <option value="pico">pico</option>
          </select>
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
