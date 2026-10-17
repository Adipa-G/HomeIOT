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

const mockModuleResults = {
  items: [
    {
      id: 'r1',
      device_id: 'esp32-001',
      module_id: 'sensor_read',
      module_version: '1.0.0',
      run_id: 'run-001',
      status: 'success',
      elapsed_ms: 42,
      error_message: null,
      output: JSON.stringify({ temperature: 23.5 }),
      variable_values: JSON.stringify({ TEMP_THRESHOLD: 28, MODE: 'AUTO' }),
      started_at_utc: '2026-05-30T10:00:00Z',
      finished_at_utc: '2026-05-30T10:00:00Z',
    },
    {
      id: 'r2',
      device_id: 'esp32-001',
      module_id: 'led_blink',
      module_version: '2.0.0',
      run_id: 'run-002',
      status: 'error',
      elapsed_ms: 5,
      error_message: 'NameError: x not defined',
      output: null,
      variable_values: JSON.stringify({ BLINK_MS: 500 }),
      started_at_utc: '2026-05-30T09:55:00Z',
      finished_at_utc: '2026-05-30T09:55:00Z',
    },
  ],
  total: 2,
};

const mockModules = [
  {
    module_id: 'sensor_read',
    description: 'Read temperature sensor',
    version: '1.0.0',
    variable_defs: [
      {
        id: 'var-1',
        name: 'temperature',
        json_path: 'temperature',
        visualizations: [],
      },
    ],
    assignments: [],
  },
  {
    module_id: 'led_blink',
    description: 'Blink LED',
    version: '2.0.0',
    variable_defs: [],
    assignments: [],
  },
];

function defaultApiGetMock(url: string) {
  if (url.includes('/activity')) return Promise.resolve([]);
  if (url.includes('/modules/chart-series')) return Promise.resolve([]);
  if (url.includes('/modules') && !url.includes('/results')) return Promise.resolve(mockModules);
  if (url.includes('/modules/results')) return Promise.resolve(mockModuleResults);
  if (url.includes('/heartbeats')) return Promise.resolve(mockHeartbeats);
  if (url.includes('/logs')) return Promise.resolve(mockLogs);
  return Promise.resolve(mockDevice);
}

describe('DeviceDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('renders device info', async () => {
    vi.mocked(api.get).mockImplementation(defaultApiGetMock);
    renderWithProviders(<DeviceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });
    expect(screen.getByText('1.5.0')).toBeInTheDocument();
  });

  it('switches to logs tab and shows entries sorted descending', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockImplementation(defaultApiGetMock);
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
    vi.mocked(api.get).mockImplementation(defaultApiGetMock);
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

  it('switches to modules tab and shows tiles', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockImplementation(defaultApiGetMock);
    renderWithProviders(<DeviceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Modules'));

    await waitFor(() => {
      expect(screen.getByText('sensor_read')).toBeInTheDocument();
    });
    expect(screen.getByText('led_blink')).toBeInTheDocument();
    // Tile shows latest output
    expect(screen.getByText(/"temperature"/)).toBeInTheDocument();
    // Status badges
    expect(screen.getByText('success')).toBeInTheDocument();
    expect(screen.getByText('error')).toBeInTheDocument();
  });

  it('renders module results with visualization tiles on modules tab', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockImplementation(defaultApiGetMock);
    renderWithProviders(<DeviceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Modules'));

    await waitFor(() => {
      expect(screen.getByText('sensor_read')).toBeInTheDocument();
    });

    expect(screen.getByText('led_blink')).toBeInTheDocument();
    // Tiles show output data
    expect(screen.getByText(/"temperature"/)).toBeInTheDocument();
    // Status badges
    expect(screen.getByText('success')).toBeInTheDocument();
    expect(screen.getByText('error')).toBeInTheDocument();
  });

  it('passes the device chart series to chart visualizations on the modules tab', async () => {
    const user = userEvent.setup();
    const chartModules = [
      {
        ...mockModules[0],
        variable_defs: [
          {
            id: 'var-1',
            name: 'temperature',
            visualizations: [
              { id: 'viz-temp', json_path: 'temperature', display_name: 'Temp chart', visualization_type: 'bar_chart' },
            ],
          },
        ],
      },
      mockModules[1],
    ];
    const chartSeries = [
      {
        module_id: 'sensor_read',
        series: [
          {
            visualization_id: 'viz-temp',
            points: [
              { start_utc: '2026-05-30T09:00:00Z', end_utc: '2026-05-30T09:30:00Z', avg: 21, min: 20, max: 22, count: 30 },
              { start_utc: '2026-05-30T09:30:00Z', end_utc: '2026-05-30T10:00:00Z', avg: 23, min: 22, max: 24, count: 30 },
            ],
          },
        ],
      },
    ];
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('/modules/chart-series')) return Promise.resolve(chartSeries);
      if (url === '/api/admin/modules') return Promise.resolve(chartModules);
      return defaultApiGetMock(url);
    });
    renderWithProviders(<DeviceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });
    await user.click(screen.getByText('Modules'));

    await waitFor(() => {
      expect(screen.getAllByTestId('chart-bar')).toHaveLength(2);
    });
    expect(screen.getByText('2 bars · 60 samples')).toBeInTheDocument();
    expect(api.get).toHaveBeenCalledWith('/api/admin/modules/chart-series?device_id=esp32-001');
  });

  it('clicking a heartbeat activity bar filters the table and clear-filter resets it', async () => {
    vi.setSystemTime(new Date('2026-06-15T12:00:00Z'));
    const user = userEvent.setup();
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('/heartbeats/activity') && url.includes('bucket=day')) {
        return Promise.resolve([
          { bucket_start_utc: '2026-06-15T00:00:00Z', bucket_end_utc: '2026-06-16T00:00:00Z', count: 3 },
        ]);
      }
      return defaultApiGetMock(url);
    });

    renderWithProviders(<DeviceDetailPage />);

    await waitFor(() => {
      expect(screen.getByText('esp32-001')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Heartbeats'));

    await waitFor(() => {
      expect(screen.getByLabelText('Jun 15: 3')).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText('Jun 15: 3'));

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('/heartbeats?offset=0&limit=25&from=2026-06-15T00:00:00Z&to=2026-06-16T00:00:00Z'),
      );
    });
    expect(screen.getByText('Clear filter')).toBeInTheDocument();

    await user.click(screen.getByText('Clear filter'));

    await waitFor(() => {
      expect(screen.queryByText('Clear filter')).not.toBeInTheDocument();
    });

    vi.setSystemTime(new Date());
  });
});
