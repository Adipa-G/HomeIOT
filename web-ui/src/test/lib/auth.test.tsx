import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { AuthProvider, useAuth } from '../../lib/auth';
import type { ReactNode } from 'react';

vi.mock('../../api/client', () => ({
  api: {
    post: vi.fn(),
  },
  ApiError: class extends Error {
    constructor(_status: number, error: { code: string; message: string }) {
      super(error.message);
    }
  },
}));

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe('useAuth', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('throws when used outside AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow('useAuth must be used within AuthProvider');
  });

  it('starts unauthenticated when no token in storage', () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
  });

  it('starts authenticated when token exists in storage', () => {
    localStorage.setItem('auth_token', 'existing-token');
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.token).toBe('existing-token');
  });

  it('login stores token and updates state', async () => {
    const { api } = await import('../../api/client');
    vi.mocked(api.post).mockResolvedValue({ token: 'new-jwt', expires_at: '2026-06-01T00:00:00Z' });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await act(async () => {
      await result.current.login('admin', 'password');
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.token).toBe('new-jwt');
    expect(localStorage.getItem('auth_token')).toBe('new-jwt');
    expect(api.post).toHaveBeenCalledWith('/api/admin/auth/token', { username: 'admin', password: 'password' });
  });

  it('logout clears token and updates state', () => {
    localStorage.setItem('auth_token', 'some-token');
    const { result } = renderHook(() => useAuth(), { wrapper });

    act(() => {
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
    expect(localStorage.getItem('auth_token')).toBeNull();
  });
});
