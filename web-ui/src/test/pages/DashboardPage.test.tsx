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
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.includes('/dashboard/modules')) return [];
      return mockDashboard;
    });
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
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.includes('/dashboard/modules')) return [];
      return mockDashboard;
    });
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('2.0% failure rate')).toBeInTheDocument();
    });
  });

  it('renders modules grouped by device when flagged modules exist', async () => {
    const mockModules = [
      {
        assignment_id: 'a1',
        device_id: 'esp32-001',
        module_id: 'sensor-reader',
        status: 'ok',
        output: '{"temp":21.5}',
        error_message: null,
        finished_at_utc: '2026-05-10T00:00:00Z',
        variable_defs: [
          {
            name: 'temp',
            type: 'number',
            default_value: null,
            description: null,
            has_server_code: false,
            visualizations: [
              { id: 'v1', json_path: 'temp', display_name: 'Temperature', visualization_type: 'number_display' },
            ],
          },
        ],
      },
    ];
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.includes('/dashboard/modules')) return mockModules;
      return mockDashboard;
    });
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });
    expect(screen.getByText('sensor-reader')).toBeInTheDocument();
  });

  it('renders one tile per visualization, each captioned with its module id', async () => {
    const mockModules = [
      {
        assignment_id: 'a2',
        device_id: 'esp32-002',
        module_id: 'multi-sensor',
        status: 'ok',
        output: '{"temp":21.5,"humidity":40,"pressure":1013}',
        error_message: null,
        finished_at_utc: '2026-05-10T00:00:00Z',
        variable_defs: [
          {
            name: 'readings',
            type: 'json',
            default_value: null,
            description: null,
            has_server_code: false,
            visualizations: [
              { id: 'v1', json_path: 'temp', display_name: 'Temperature', visualization_type: 'number_display' },
              { id: 'v2', json_path: 'humidity', display_name: 'Humidity', visualization_type: 'number_display' },
              { id: 'v3', json_path: 'pressure', display_name: 'Pressure', visualization_type: 'number_display' },
            ],
          },
        ],
      },
    ];
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.includes('/dashboard/modules')) return mockModules;
      return mockDashboard;
    });
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-002')).toBeInTheDocument();
    });
    expect(screen.getAllByText('multi-sensor')).toHaveLength(3);
    expect(screen.getByText('Temperature')).toBeInTheDocument();
    expect(screen.getByText('Humidity')).toBeInTheDocument();
    expect(screen.getByText('Pressure')).toBeInTheDocument();
  });

  it('renders a status fallback tile for a module with no visualizations', async () => {
    const mockModules = [
      {
        assignment_id: 'a3',
        device_id: 'esp32-003',
        module_id: 'no-viz-module',
        status: 'ok',
        output: '{"temp":21.5}',
        error_message: null,
        finished_at_utc: '2026-05-10T00:00:00Z',
        variable_defs: [
          {
            name: 'temp',
            type: 'number',
            default_value: null,
            description: null,
            has_server_code: false,
            visualizations: [],
          },
        ],
      },
    ];
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.includes('/dashboard/modules')) return mockModules;
      return mockDashboard;
    });
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-003')).toBeInTheDocument();
    });
    expect(screen.getByText('Status: ok')).toBeInTheDocument();
  });

  it('renders an error tile for a module with an error message', async () => {
    const mockModules = [
      {
        assignment_id: 'a4',
        device_id: 'esp32-004',
        module_id: 'failing-module',
        status: 'error',
        output: null,
        error_message: 'Timed out',
        finished_at_utc: '2026-05-10T00:00:00Z',
        variable_defs: [],
      },
    ];
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.includes('/dashboard/modules')) return mockModules;
      return mockDashboard;
    });
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-004')).toBeInTheDocument();
    });
    expect(screen.getByText('Status: error')).toBeInTheDocument();
    expect(screen.getByText('Timed out')).toBeInTheDocument();
  });

  it('sizes device boxes using the same grid track structure as the metric cards', async () => {
    const mockModules = [
      {
        assignment_id: 'a1',
        device_id: 'esp32-001',
        module_id: 'sensor-reader',
        status: 'ok',
        output: '{"temp":21.5}',
        error_message: null,
        finished_at_utc: '2026-05-10T00:00:00Z',
        variable_defs: [
          {
            name: 'temp',
            type: 'number',
            default_value: null,
            description: null,
            has_server_code: false,
            visualizations: [
              { id: 'v1', json_path: 'temp', display_name: 'Temperature', visualization_type: 'number_display' },
            ],
          },
        ],
      },
    ];
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.includes('/dashboard/modules')) return mockModules;
      return mockDashboard;
    });
    const { container } = renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });

    const deviceHeading = screen.getByText('esp32-001');
    const deviceBox = deviceHeading.parentElement;
    const devicesContainer = deviceBox?.parentElement;
    expect(devicesContainer?.className).toContain('grid-cols-2');
    expect(devicesContainer?.className).toContain('lg:grid-cols-3');
    expect(devicesContainer?.className).toContain('xl:grid-cols-4');
    expect(deviceBox?.className).not.toMatch(/col-span-[2-9]/);

    const metricsContainer = container.querySelector('.grid.grid-cols-2.gap-4.lg\\:grid-cols-3.xl\\:grid-cols-4');
    expect(metricsContainer).not.toBeNull();
  });

  it('keeps a lone tile at half width instead of shrinking to a third column', async () => {
    const mockModules = [
      {
        assignment_id: 'a1',
        device_id: 'esp32-001',
        module_id: 'sensor-reader',
        status: 'ok',
        output: '{"temp":21.5}',
        error_message: null,
        finished_at_utc: '2026-05-10T00:00:00Z',
        variable_defs: [
          {
            name: 'temp',
            type: 'number',
            default_value: null,
            description: null,
            has_server_code: false,
            visualizations: [
              { id: 'v1', json_path: 'temp', display_name: 'Temperature', visualization_type: 'number_display' },
            ],
          },
        ],
      },
    ];
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.includes('/dashboard/modules')) return mockModules;
      return mockDashboard;
    });
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });

    const tileGrid = screen.getByText('Temperature').closest('.grid');
    expect(tileGrid?.className).toContain('grid-cols-2');
    expect(tileGrid?.className).not.toContain('lg:grid-cols-3');
  });

  it('expands the tile grid to 3 columns at lg once there are 3 or more tiles', async () => {
    const mockModules = [
      {
        assignment_id: 'a2',
        device_id: 'esp32-002',
        module_id: 'multi-sensor',
        status: 'ok',
        output: '{"temp":21.5,"humidity":40,"pressure":1013}',
        error_message: null,
        finished_at_utc: '2026-05-10T00:00:00Z',
        variable_defs: [
          {
            name: 'readings',
            type: 'json',
            default_value: null,
            description: null,
            has_server_code: false,
            visualizations: [
              { id: 'v1', json_path: 'temp', display_name: 'Temperature', visualization_type: 'number_display' },
              { id: 'v2', json_path: 'humidity', display_name: 'Humidity', visualization_type: 'number_display' },
              { id: 'v3', json_path: 'pressure', display_name: 'Pressure', visualization_type: 'number_display' },
            ],
          },
        ],
      },
    ];
    vi.mocked(api.get).mockImplementation(async (path: string) => {
      if (path.includes('/dashboard/modules')) return mockModules;
      return mockDashboard;
    });
    renderWithProviders(<DashboardPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-002')).toBeInTheDocument();
    });

    const tileGrid = screen.getByText('Temperature').closest('.grid');
    expect(tileGrid?.className).toContain('grid-cols-2');
    expect(tileGrid?.className).toContain('lg:grid-cols-3');
  });
});
