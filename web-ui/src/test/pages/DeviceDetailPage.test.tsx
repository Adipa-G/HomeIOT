import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DeviceDetailPage from '../../pages/DeviceDetailPage';
import { renderWithProviders } from '../test-utils';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return { ...actual, useParams: () => ({ deviceId: 'esp32-001' }), useNavigate: () => vi.fn() };
});

const mockDevice = {
  device_id: 'esp32-001',
  platform: 'esp32',
  version: '1.5.0',
  ip: '192.168.1.50',
  mode: 'production',
  last_heartbeat_at_utc: '2026-05-30T10:00:00Z',
  created_at_utc: '2026-05-01T00:00:00Z',
  updated_at_utc: '2026-05-30T10:00:00Z',
  latest_heartbeat: { uptime_ms: 360000, free_memory_bytes: 65536, received_at_utc: '2026-05-30T10:00:00Z' },
};

const mockHeartbeats = {
  items: [
    { uptime_ms: 360000, free_memory_bytes: 65536, received_at_utc: '2026-05-30T10:00:00Z' },
  ],
  total: 1,
};

const mockLogs = {
  items: [
    {
      id: 'batch-1',
      reason: 'interval',
      received_count: 2,
      dropped_count: 0,
      truncated: false,
      logs_json: JSON.stringify([
        { ts: 100, level: 'INFO', message: 'Boot complete', context: { mode: 'production' } },
        { ts: 200, level: 'WARN', message: 'Low memory', context: {} },
      ]),
      received_at_utc: '2026-05-30T10:00:00Z',
    },
    {
      id: 'batch-2',
      reason: 'threshold',
      received_count: 1,
      dropped_count: 0,
      truncated: false,
      logs_json: JSON.stringify([
        { ts: 50, level: 'ERROR', message: 'Connection failed', context: { host: '10.0.0.1' } },
      ]),
      received_at_utc: '2026-05-30T09:00:00Z',
    },
  ],
  total: 2,
};

describe('DeviceDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('renders device info', async () => {
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('/heartbeats')) return Promise.resolve(mockHeartbeats);
      return Promise.resolve(mockDevice);
    });
    renderWithProviders(<DeviceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });
    expect(screen.getByText('1.5.0')).toBeInTheDocument();
  });

  it('switches to logs tab and shows entries sorted descending', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('/logs')) return Promise.resolve(mockLogs);
      if (url.includes('/heartbeats')) return Promise.resolve(mockHeartbeats);
      return Promise.resolve(mockDevice);
    });
    renderWithProviders(<DeviceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Logs'));

    await waitFor(() => {
      expect(screen.getByText('Boot complete')).toBeInTheDocument();
    });
    expect(screen.getByText('Low memory')).toBeInTheDocument();
    expect(screen.getByText('Connection failed')).toBeInTheDocument();

    // Verify context data is displayed
    expect(screen.getByText(/mode=production/)).toBeInTheDocument();
    expect(screen.getByText(/host=10.0.0.1/)).toBeInTheDocument();
  });

  it('shows log entries in descending order (newest batch first)', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('/logs')) return Promise.resolve(mockLogs);
      if (url.includes('/heartbeats')) return Promise.resolve(mockHeartbeats);
      return Promise.resolve(mockDevice);
    });
    renderWithProviders(<DeviceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Logs'));

    await waitFor(() => {
      expect(screen.getByText('Boot complete')).toBeInTheDocument();
    });

    // The batch from 10:00 (ts=200, ts=100) should appear before batch from 09:00 (ts=50)
    const logEntries = screen.getAllByText(/Boot complete|Low memory|Connection failed/);
    expect(logEntries).toHaveLength(3);
    // First entries should be from the 10:00 batch (descending)
    expect(logEntries[0].textContent).toContain('Low memory');
    expect(logEntries[2].textContent).toContain('Connection failed');
  });
});
