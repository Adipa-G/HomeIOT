import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { api } from '../api/client';
import type { AdminLoginRequest, AdminLoginResponse } from '../types/api';

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem('auth_token'),
  );

  const login = useCallback(async (username: string, password: string) => {
    const body: AdminLoginRequest = { username, password };
    const res = await api.post<AdminLoginResponse>('/api/admin/auth/token', body);
    localStorage.setItem('auth_token', res.token);
    setToken(res.token);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    setToken(null);
  }, []);

  return (
    <AuthContext.Provider value={{ token, isAuthenticated: !!token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
