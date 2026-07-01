import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate } from 'react-router';
import { useAuth } from '../lib/auth';
import { ApiError } from '../api/client';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Auto-clear error after 10 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError('');
      }, 10000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(username, password);
      navigate('/', { replace: true });
    } catch (err) {
      const errorMessage = err instanceof ApiError ? err.error.message : 'Login failed';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <form onSubmit={handleSubmit} className="w-full max-w-sm rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-xl font-bold text-gray-900">HomeIOT Admin</h1>
        {error && <p className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <label htmlFor="username" className="mb-1 block text-sm font-medium text-gray-700">Username</label>
        <input
          id="username"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          className="mb-4 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">Password</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          className="mb-6 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
