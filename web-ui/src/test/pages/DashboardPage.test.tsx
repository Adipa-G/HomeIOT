import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import DashboardPage from '../../pages/DashboardPage';
import { renderWithProviders } from '../test-utils';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
  },
}));

const mockDashboard = {
  total_devices: 10,
  devices_online_24h: 7,
  total_modules: 5,
  total_assignments: 12,
  total_users: 3,
  heartbeats_24h: 200,
  log_batches_24h: 50,
  module_runs_24h: 100,
  module_failures_24h: 2,
};

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('shows loading state initially', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    renderWithProviders(<DashboardPage />);
    expect(screen.getByText('Loading dashboard…')).toBeInTheDocument();
  });

  it('renders dashboard metrics', async () => {
    vi.mocked(api.get).mockResolvedValue(mockDashboard);
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('200')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  it('shows failure rate when there are runs', async () => {
    vi.mocked(api.get).mockResolvedValue(mockDashboard);
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('2.0% failure rate')).toBeInTheDocument();
    });
  });
});
