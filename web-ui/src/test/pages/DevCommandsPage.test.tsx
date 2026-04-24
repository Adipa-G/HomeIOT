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

  const devicesResponse = {
    items: [
      { device_id: 'esp32-dev-01', platform: 'esp32', version: '3.6.0', ip: null, mode: 'development', last_heartbeat_at_utc: null, created_at_utc: '2026-01-01T00:00:00Z' },
    ],
    total: 1,
    page: 1,
    page_size: 200,
  };

  it('renders enqueue form', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<DevCommandsPage />);
    expect(screen.getByText('Dev Commands')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument();
  });

  it('shows device dropdown with development devices', async () => {
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('devices')) return Promise.resolve(devicesResponse);
      return new Promise(() => {});
    });
    renderWithProviders(<DevCommandsPage />);
    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'esp32-dev-01' })).toBeInTheDocument();
    });
  });

  it('shows code textarea', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<DevCommandsPage />);
    expect(screen.getByPlaceholderText('# enter MicroPython code here')).toBeInTheDocument();
  });

  it('shows pending tab by default', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<DevCommandsPage />);
    expect(screen.getByText('Pending')).toBeInTheDocument();
    expect(screen.getByText('Results')).toBeInTheDocument();
  });

  it('shows "No pending commands" when empty', async () => {
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('devices')) return Promise.resolve(devicesResponse);
      return Promise.resolve([]);
    });
    renderWithProviders(<DevCommandsPage />);

    await waitFor(() => {
      expect(screen.getByText('No pending commands.')).toBeInTheDocument();
    });
  });

  it('renders pending commands', async () => {
    const pending = [
      {
        command_id: 'abcdefgh-1234-5678-9abc-def012345678',
        device_id: 'esp32-dev-01',
        code: 'print("hello")',
        queued_at_utc: '2026-05-30T12:00:00Z',
      },
    ];
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('devices')) return Promise.resolve(devicesResponse);
      return Promise.resolve(pending);
    });
    renderWithProviders(<DevCommandsPage />);

    await waitFor(() => {
      expect(screen.getAllByText('esp32-dev-01').length).toBeGreaterThan(0);
    });
    expect(screen.getByText('print("hello")')).toBeInTheDocument();
  });
});
