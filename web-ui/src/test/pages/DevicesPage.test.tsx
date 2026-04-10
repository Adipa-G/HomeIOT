import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import DevicesPage from '../../pages/DevicesPage';
import { renderWithProviders } from '../test-utils';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

const mockDevices = {
  items: [
    {
      device_id: 'esp32-001',
      platform: 'esp32',
      version: '1.2.0',
      ip: '192.168.1.10',
      mode: 'production',
      last_heartbeat_at_utc: '2026-05-30T08:00:00Z',
      created_at_utc: '2026-05-01T00:00:00Z',
    },
    {
      device_id: 'pico-002',
      platform: 'pico',
      version: '1.0.0',
      ip: null,
      mode: 'development',
      last_heartbeat_at_utc: null,
      created_at_utc: '2026-05-15T00:00:00Z',
    },
  ],
  total: 2,
  offset: 0,
  limit: 50,
};

describe('DevicesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('shows loading state', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<DevicesPage />);
    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('renders device list', async () => {
    vi.mocked(api.get).mockResolvedValue(mockDevices);
    renderWithProviders(<DevicesPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });

    expect(screen.getByText('pico-002')).toBeInTheDocument();
    expect(screen.getAllByText('production').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('development').length).toBeGreaterThanOrEqual(1);
  });

  it('shows "No devices found" when empty', async () => {
    vi.mocked(api.get).mockResolvedValue({ items: [], total: 0, offset: 0, limit: 50 });
    renderWithProviders(<DevicesPage />);

    await waitFor(() => {
      expect(screen.getByText('No devices found.')).toBeInTheDocument();
    });
  });

  it('renders filter inputs', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<DevicesPage />);
    expect(screen.getByPlaceholderText('Search device ID…')).toBeInTheDocument();
  });
});
