import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import DevCommandsPage from '../../pages/DevCommandsPage';
import { renderWithProviders } from '../test-utils';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
  ApiError: class extends Error {
    constructor(public status: number, public error: { code: string; message: string }) {
      super(error.message);
    }
  },
}));

describe('DevCommandsPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('renders enqueue form', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<DevCommandsPage />);
    expect(screen.getByText('Dev Commands')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument();
  });

  it('shows pending tab by default', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<DevCommandsPage />);
    expect(screen.getByText('Pending')).toBeInTheDocument();
    expect(screen.getByText('Results')).toBeInTheDocument();
  });

  it('shows "No pending commands" when empty', async () => {
    vi.mocked(api.get).mockResolvedValue([]);
    renderWithProviders(<DevCommandsPage />);

    await waitFor(() => {
      expect(screen.getByText('No pending commands.')).toBeInTheDocument();
    });
  });

  it('renders pending commands', async () => {
    vi.mocked(api.get).mockResolvedValue([
      {
        command_id: 'abcdefgh-1234-5678-9abc-def012345678',
        device_id: 'esp32-001',
        command: 'reboot',
        queued_at_utc: '2026-05-30T12:00:00Z',
      },
    ]);
    renderWithProviders(<DevCommandsPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });
    expect(screen.getByText('reboot')).toBeInTheDocument();
  });
});
