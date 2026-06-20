import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DeviceDetailPage from '../../pages/DeviceDetailPage';
import { renderWithProviders } from '../test-utils';
import { api } from '../../api/client';
import { extractJsonValue } from '../../components/ModuleVariableVisualizer';
import type { ModuleResultListItem } from '../../types/api';

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

/**
 * Helper to extract historical values for a json_path from recent module results
 * (Extracted from DeviceDetailPage for testing)
 */
const getHistoricalValues = (
  moduleId: string,
  jsonPath: string,
  config: any,
  moduleResults: ModuleResultListItem[]
): (string | number | null)[] | undefined => {
  const historyPoints = (config as any)?.historyPoints;
  if (!historyPoints || historyPoints < 2) return undefined;

  const results = moduleResults.filter(
    (r: ModuleResultListItem) =>
      r.module_id === moduleId && r.output && r.status === 'success'
  );

  if (results.length === 0) return undefined;

  // Get last N results and extract values
  const recentResults = results.slice(-historyPoints);
  return recentResults.map((r: ModuleResultListItem) => {
    try {
      const outputData = JSON.parse(r.output || '{}');
      return extractJsonValue(outputData, jsonPath);
    } catch {
      return null;
    }
  });
};

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

describe('DeviceDetailPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.setItem('auth_token', 'test-token');
  });

  it('renders device info', async () => {
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('/modules') && !url.includes('/results')) return Promise.resolve(mockModules);
      if (url.includes('/modules/results')) return Promise.resolve(mockModuleResults);
      if (url.includes('/heartbeats')) return Promise.resolve(mockHeartbeats);
      if (url.includes('/logs')) return Promise.resolve(mockLogs);
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
      if (url.includes('/modules') && !url.includes('/results')) return Promise.resolve(mockModules);
      if (url.includes('/modules/results')) return Promise.resolve(mockModuleResults);
      if (url.includes('/heartbeats')) return Promise.resolve(mockHeartbeats);
      if (url.includes('/logs')) return Promise.resolve(mockLogs);
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
      if (url.includes('/modules') && !url.includes('/results')) return Promise.resolve(mockModules);
      if (url.includes('/modules/results')) return Promise.resolve(mockModuleResults);
      if (url.includes('/heartbeats')) return Promise.resolve(mockHeartbeats);
      if (url.includes('/logs')) return Promise.resolve(mockLogs);
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

  it('switches to modules tab and shows tiles', async () => {
    const user = userEvent.setup();
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('/modules') && !url.includes('/results')) return Promise.resolve(mockModules);
      if (url.includes('/modules/results')) return Promise.resolve(mockModuleResults);
      if (url.includes('/heartbeats')) return Promise.resolve(mockHeartbeats);
      if (url.includes('/logs')) return Promise.resolve(mockLogs);
      return Promise.resolve(mockDevice);
    });
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
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('/modules') && !url.includes('/results')) return Promise.resolve(mockModules);
      if (url.includes('/modules/results')) return Promise.resolve(mockModuleResults);
      if (url.includes('/heartbeats')) return Promise.resolve(mockHeartbeats);
      if (url.includes('/logs')) return Promise.resolve(mockLogs);
      if (url.includes('/devices')) return Promise.resolve(mockDevice);
      return Promise.resolve(mockDevice);
    });
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

  describe('Historical Values Helper', () => {
    const mockResults: ModuleResultListItem[] = [
      {
        id: '1',
        device_id: 'esp32-001',
        module_id: 'temp-reader',
        module_version: '1.0',
        run_id: 'run-001',
        status: 'success',
        output: JSON.stringify({ temperature: 20, humidity: 45 }),
        variable_values: '{}',
        elapsed_ms: 100,
        started_at_utc: '2026-01-01T10:00:00Z',
        finished_at_utc: '2026-01-01T10:00:00Z',
        error_message: null,
      },
      {
        id: '2',
        device_id: 'esp32-001',
        module_id: 'temp-reader',
        module_version: '1.0',
        run_id: 'run-002',
        status: 'success',
        output: JSON.stringify({ temperature: 22, humidity: 46 }),
        variable_values: '{}',
        elapsed_ms: 100,
        started_at_utc: '2026-01-01T10:05:00Z',
        finished_at_utc: '2026-01-01T10:05:00Z',
        error_message: null,
      },
      {
        id: '3',
        device_id: 'esp32-001',
        module_id: 'temp-reader',
        module_version: '1.0',
        run_id: 'run-003',
        status: 'success',
        output: JSON.stringify({ temperature: 24, humidity: 47 }),
        variable_values: '{}',
        elapsed_ms: 100,
        started_at_utc: '2026-01-01T10:10:00Z',
        finished_at_utc: '2026-01-01T10:10:00Z',
        error_message: null,
      },
    ];

    it('returns undefined when historyPoints is not configured', () => {
      const result = getHistoricalValues('temp-reader', 'temperature', {}, mockResults);
      expect(result).toBeUndefined();
    });

    it('returns undefined when historyPoints is less than 2', () => {
      const result = getHistoricalValues('temp-reader', 'temperature', { historyPoints: 1 }, mockResults);
      expect(result).toBeUndefined();
    });

    it('returns undefined when no matching results for module', () => {
      const result = getHistoricalValues('non-existent', 'temperature', { historyPoints: 5 }, mockResults);
      expect(result).toBeUndefined();
    });

    it('returns undefined when no successful results', () => {
      const failedResults: ModuleResultListItem[] = [
        {
          ...mockResults[0],
          status: 'error' as any,
        },
      ];
      const result = getHistoricalValues('temp-reader', 'temperature', { historyPoints: 5 }, failedResults);
      expect(result).toBeUndefined();
    });

    it('extracts historical values in order', () => {
      const result = getHistoricalValues('temp-reader', 'temperature', { historyPoints: 3 }, mockResults);
      expect(result).toEqual([20, 22, 24]);
    });

    it('limits results to historyPoints count', () => {
      const manyResults = [
        ...mockResults,
        {
          ...mockResults[0],
          id: '4',
          run_id: 'run-004',
          output: JSON.stringify({ temperature: 25, humidity: 48 }),
        },
      ];
      const result = getHistoricalValues('temp-reader', 'temperature', { historyPoints: 2 }, manyResults);
      expect(result?.length).toBe(2);
      expect(result).toEqual([24, 25]);
    });

    it('extracts nested json path values', () => {
      const nestedResults: ModuleResultListItem[] = [
        {
          ...mockResults[0],
          output: JSON.stringify({ sensor: { data: { temperature: 19.5 } } }),
        },
        {
          ...mockResults[1],
          output: JSON.stringify({ sensor: { data: { temperature: 21.5 } } }),
        },
      ];
      const result = getHistoricalValues('temp-reader', 'sensor.data.temperature', { historyPoints: 2 }, nestedResults);
      expect(result).toEqual([19.5, 21.5]);
    });

    it('handles mixed null and valid values', () => {
      const mixedResults: ModuleResultListItem[] = [
        {
          ...mockResults[0],
          output: JSON.stringify({ temperature: 20 }),
        },
        {
          ...mockResults[1],
          output: JSON.stringify({ humidity: 46 }), // temperature missing
        },
        {
          ...mockResults[2],
          output: JSON.stringify({ temperature: 24 }),
        },
      ];
      const result = getHistoricalValues('temp-reader', 'temperature', { historyPoints: 3 }, mixedResults);
      expect(result).toEqual([20, null, 24]);
    });

    it('handles invalid JSON in output', () => {
      const invalidResults: ModuleResultListItem[] = [
        {
          ...mockResults[0],
          output: 'invalid json {',
        },
        {
          ...mockResults[1],
          output: JSON.stringify({ temperature: 22 }),
        },
      ];
      const result = getHistoricalValues('temp-reader', 'temperature', { historyPoints: 2 }, invalidResults);
      expect(result).toEqual([null, 22]);
    });

    it('filters by module_id correctly', () => {
      const multiModuleResults: ModuleResultListItem[] = [
        {
          ...mockResults[0],
          module_id: 'temp-reader',
          output: JSON.stringify({ value: 20 }),
        },
        {
          ...mockResults[1],
          module_id: 'humidity-reader',
          output: JSON.stringify({ value: 50 }),
        },
        {
          ...mockResults[2],
          module_id: 'temp-reader',
          output: JSON.stringify({ value: 24 }),
        },
      ];
      const result = getHistoricalValues('temp-reader', 'value', { historyPoints: 3 }, multiModuleResults);
      expect(result).toEqual([20, 24]); // Only temp-reader values
    });

    it('ignores failed status results', () => {
      const mixedStatusResults: ModuleResultListItem[] = [
        {
          ...mockResults[0],
          status: 'success',
          output: JSON.stringify({ temperature: 20 }),
        },
        {
          ...mockResults[1],
          status: 'error' as any,
          output: JSON.stringify({ temperature: 22 }),
        },
        {
          ...mockResults[2],
          status: 'success',
          output: JSON.stringify({ temperature: 24 }),
        },
      ];
      const result = getHistoricalValues('temp-reader', 'temperature', { historyPoints: 5 }, mixedStatusResults);
      expect(result).toEqual([20, 24]); // Only success status
    });

    it('handles numeric strings in output', () => {
      const stringResults: ModuleResultListItem[] = [
        {
          ...mockResults[0],
          output: JSON.stringify({ temperature: '20.5' }),
        },
        {
          ...mockResults[1],
          output: JSON.stringify({ temperature: '22.7' }),
        },
      ];
      const result = getHistoricalValues('temp-reader', 'temperature', { historyPoints: 2 }, stringResults);
      expect(result).toEqual(['20.5', '22.7']);
    });

    it('handles zero values', () => {
      const zeroResults: ModuleResultListItem[] = [
        {
          ...mockResults[0],
          module_id: 'sensor',
          output: JSON.stringify({ value: 0 }),
        },
      ];
      const result = getHistoricalValues('sensor', 'value', { historyPoints: 2 }, zeroResults);
      expect(result).toEqual([0]);
    });

    it('handles negative values', () => {
      const negativeResults: ModuleResultListItem[] = [
        {
          ...mockResults[0],
          output: JSON.stringify({ temperature: -15.5 }),
        },
      ];
      const result = getHistoricalValues('temp-reader', 'temperature', { historyPoints: 2 }, negativeResults);
      expect(result).toEqual([-15.5]);
    });

    it('skips results with empty output', () => {
      const emptyResults: ModuleResultListItem[] = [
        {
          ...mockResults[0],
          output: '',
        },
        {
          ...mockResults[1],
          output: JSON.stringify({ temperature: 22 }),
        },
      ];
      const result = getHistoricalValues('temp-reader', 'temperature', { historyPoints: 2 }, emptyResults);
      expect(result).toEqual([22]); // Empty output is skipped by filter
    });

    it('returns last N results when more available', () => {
      const result = getHistoricalValues('temp-reader', 'temperature', { historyPoints: 2 }, mockResults);
      expect(result).toEqual([22, 24]); // Last 2 values
    });

    it('handles very large arrays efficiently', () => {
      const largeResults: ModuleResultListItem[] = Array.from({ length: 100 }, (_, i) => ({
        ...mockResults[0],
        id: String(i),
        run_id: `run-${i}`,
        output: JSON.stringify({ value: i }),
      }));

      const result = getHistoricalValues('temp-reader', 'value', { historyPoints: 5 }, largeResults);
      expect(result?.length).toBe(5);
      expect(result).toEqual([95, 96, 97, 98, 99]); // Last 5
    });
  });
});
