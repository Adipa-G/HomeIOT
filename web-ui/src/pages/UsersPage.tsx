import { useState, type FormEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api/client';
import type { UserListItem, CreateUserRequest } from '../types/api';
import { ConfirmModal } from '../components/ConfirmModal';
import { toast } from '../components/Toast';
import { ApiError } from '../api/client';

export default function UsersPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState<CreateUserRequest>({ username: '', password: '' });
  const [changePw, setChangePw] = useState<{ username: string; password: string } | null>(null);
  const [error, setError] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.get<UserListItem[]>('/api/admin/users'),
  });

  const create = useMutation({
    mutationFn: () => api.post('/api/admin/users', form),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setShowCreate(false); setForm({ username: '', password: '' }); toast('User created'); },
    onError: (err) => setError(err instanceof ApiError ? err.error.message : 'Failed'),
  });

  const deleteUser = useMutation({
    mutationFn: (username: string) => api.delete(`/api/admin/users/${username}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); toast('User deleted'); },
  });

  const changePassword = useMutation({
    mutationFn: () => api.put(`/api/admin/users/${changePw!.username}/password`, { new_password: changePw!.password }),
    onSuccess: () => { setChangePw(null); toast('Password changed'); },
  });

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900">Users</h2>
        <button onClick={() => setShowCreate(!showCreate)} className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">
          {showCreate ? 'Cancel' : 'Create User'}
        </button>
      </div>

      {showCreate && (
        <form onSubmit={(e: FormEvent) => { e.preventDefault(); setError(''); create.mutate(); }} className="mb-4 rounded-lg border border-gray-200 bg-white p-4">
          {error && <p className="mb-3 rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>}
          <div className="flex items-end gap-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Username</label>
              <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required className="rounded border border-gray-300 px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Password</label>
              <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required autoComplete="new-password" className="rounded border border-gray-300 px-3 py-1.5 text-sm" />
            </div>
            <button type="submit" disabled={create.isPending} className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white disabled:opacity-50">Create</button>
          </div>
        </form>
      )}

      {/* Change password modal */}
      {changePw && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <form onSubmit={(e: FormEvent) => { e.preventDefault(); changePassword.mutate(); }} className="w-full max-w-sm rounded-lg bg-white p-6 shadow-lg">
            <h3 className="mb-4 text-lg font-semibold text-gray-900">Change password for {changePw.username}</h3>
            <input type="password" placeholder="New password" value={changePw.password} onChange={(e) => setChangePw({ ...changePw, password: e.target.value })} required autoComplete="new-password" className="mb-4 w-full rounded border border-gray-300 px-3 py-2 text-sm" />
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setChangePw(null)} className="rounded border border-gray-300 px-4 py-2 text-sm">Cancel</button>
              <button type="submit" disabled={changePassword.isPending} className="rounded bg-blue-600 px-4 py-2 text-sm text-white disabled:opacity-50">Save</button>
            </div>
          </form>
        </div>
      )}

      {isLoading ? <p className="text-sm text-gray-500">Loading…</p> : !data || data.length === 0 ? (
        <p className="text-sm text-gray-500">No users.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Username</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((u) => (
                <tr key={u.username} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{u.username}</td>
                  <td className="px-4 py-3 text-gray-600">{u.created_at_utc}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => setChangePw({ username: u.username, password: '' })} className="mr-3 text-blue-600 hover:underline">Password</button>
                    <ConfirmModal title="Delete user?" description={`Delete ${u.username}?`} onConfirm={() => deleteUser.mutateAsync(u.username)}>
                      {(open) => <button onClick={open} className="text-red-600 hover:underline">Delete</button>}
                    </ConfirmModal>
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
