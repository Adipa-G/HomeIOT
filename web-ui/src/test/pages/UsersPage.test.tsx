import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import UsersPage from '../../pages/UsersPage';
import { renderWithProviders } from '../test-utils';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  ApiError: class extends Error {
    constructor(_status: number, error: { code: string; message: string }) {
      super(error.message);
    }
  },
}));

describe('UsersPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('shows loading state', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<UsersPage />);
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('renders user list', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 1, username: 'admin', created_at_utc: '2026-05-01T00:00:00Z' },
      { id: 2, username: 'viewer', created_at_utc: '2026-05-15T00:00:00Z' },
    ]);
    renderWithProviders(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText('admin')).toBeInTheDocument();
    });
    expect(screen.getByText('viewer')).toBeInTheDocument();
  });

  it('shows "No users" when empty', async () => {
    vi.mocked(api.get).mockResolvedValue([]);
    renderWithProviders(<UsersPage />);

    await waitFor(() => {
      expect(screen.getByText('No users.')).toBeInTheDocument();
    });
  });

  it('has Create User button', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<UsersPage />);
    expect(screen.getByText('Create User')).toBeInTheDocument();
  });
});
