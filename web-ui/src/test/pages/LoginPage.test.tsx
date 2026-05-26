import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LoginPage from '../../pages/LoginPage';
import { renderWithProviders } from '../test-utils';
import { api, ApiError } from '../../api/client';

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

describe('LoginPage', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it('renders login form', () => {
    renderWithProviders(<LoginPage />, { routerProps: { initialEntries: ['/login'] } });
    expect(screen.getByText('HomeIOT Admin')).toBeInTheDocument();
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('shows error on failed login', async () => {
    vi.mocked(api.post).mockRejectedValue(new ApiError(401, { code: 'unauthorized', message: 'Invalid credentials' }));

    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { routerProps: { initialEntries: ['/login'] } });

    await user.type(screen.getByLabelText('Username'), 'admin');
    await user.type(screen.getByLabelText('Password'), 'wrong');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByText('Invalid credentials')).toBeInTheDocument();
  });

  it('calls login on form submit', async () => {
    vi.mocked(api.post).mockResolvedValue({ token: 'jwt-token', expires_at: '2026-06-01T00:00:00Z' });

    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { routerProps: { initialEntries: ['/login'] } });

    await user.type(screen.getByLabelText('Username'), 'admin');
    await user.type(screen.getByLabelText('Password'), 'password');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(api.post).toHaveBeenCalledWith('/api/admin/auth/token', { username: 'admin', password: 'password' });
  });
});
