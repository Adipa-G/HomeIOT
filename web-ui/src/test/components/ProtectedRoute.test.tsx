import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { Routes, Route } from 'react-router';
import { ProtectedRoute } from '../../components/ProtectedRoute';
import { renderWithProviders } from '../test-utils';

describe('ProtectedRoute', () => {
  it('redirects to /login when not authenticated', () => {
    localStorage.removeItem('auth_token');
    renderWithProviders(
      <Routes>
        <Route path="/login" element={<p>Login Page</p>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<p>Dashboard</p>} />
        </Route>
      </Routes>,
      { routerProps: { initialEntries: ['/'] } },
    );
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    localStorage.setItem('auth_token', 'valid-token');
    renderWithProviders(
      <Routes>
        <Route path="/login" element={<p>Login Page</p>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/" element={<p>Dashboard</p>} />
        </Route>
      </Routes>,
      { routerProps: { initialEntries: ['/'] } },
    );
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });
});
