import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ActivityDrilldownPanel } from '../../components/ActivityDrilldownPanel';
import { renderWithProviders } from '../test-utils';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: {
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const NOW = new Date('2026-06-15T14:23:00Z');

describe('ActivityDrilldownPanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('requests default day/hour/5-min windows on mount', async () => {
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('bucket=day')) {
        return Promise.resolve([{ bucket_start_utc: '2026-06-15T00:00:00Z', bucket_end_utc: '2026-06-16T00:00:00Z', count: 5 }]);
      }
      if (url.includes('bucket=hour')) {
        return Promise.resolve([{ bucket_start_utc: '2026-06-15T14:00:00Z', bucket_end_utc: '2026-06-15T15:00:00Z', count: 2 }]);
      }
      return Promise.resolve([{ bucket_start_utc: '2026-06-15T14:00:00Z', bucket_end_utc: '2026-06-15T14:05:00Z', count: 1 }]);
    });

    renderWithProviders(
      <ActivityDrilldownPanel deviceId="dev-001" kind="heartbeats" onFilterChange={vi.fn()} />,
    );

    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('/api/admin/devices/dev-001/heartbeats/activity?bucket=day&from=2026-05-17T00:00:00Z&to=2026-06-16T00:00:00Z'),
      );
    });
    expect(api.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/admin/devices/dev-001/heartbeats/activity?bucket=hour&from=2026-06-15T00:00:00Z&to=2026-06-16T00:00:00Z'),
    );
    expect(api.get).toHaveBeenCalledWith(
      expect.stringContaining('/api/admin/devices/dev-001/heartbeats/activity?bucket=five_minute&from=2026-06-15T14:00:00Z&to=2026-06-15T15:00:00Z'),
    );
  });

  it('clicking a day bar re-queries the hour endpoint for that day and calls onFilterChange', async () => {
    const user = userEvent.setup();
    const onFilterChange = vi.fn();
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('bucket=day')) {
        return Promise.resolve([{ bucket_start_utc: '2026-06-10T00:00:00Z', bucket_end_utc: '2026-06-11T00:00:00Z', count: 5 }]);
      }
      if (url.includes('bucket=hour')) {
        return Promise.resolve([]);
      }
      return Promise.resolve([]);
    });

    renderWithProviders(
      <ActivityDrilldownPanel deviceId="dev-001" kind="heartbeats" onFilterChange={onFilterChange} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId('bar-2026-06-10T00:00:00Z')).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText('Jun 10: 5'));

    expect(onFilterChange).toHaveBeenCalledWith('2026-06-10T00:00:00Z', '2026-06-11T00:00:00Z');
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('bucket=hour&from=2026-06-10T00:00:00Z&to=2026-06-11T00:00:00Z'),
      );
    });
  });

  it('clicking an hour bar re-queries the 5-minute endpoint and calls onFilterChange', async () => {
    const user = userEvent.setup();
    const onFilterChange = vi.fn();
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('bucket=day')) return Promise.resolve([]);
      if (url.includes('bucket=hour')) {
        return Promise.resolve([{ bucket_start_utc: '2026-06-15T09:00:00Z', bucket_end_utc: '2026-06-15T10:00:00Z', count: 4 }]);
      }
      return Promise.resolve([]);
    });

    renderWithProviders(
      <ActivityDrilldownPanel deviceId="dev-001" kind="heartbeats" onFilterChange={onFilterChange} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId('bar-2026-06-15T09:00:00Z')).toBeInTheDocument();
    });

    await user.click(screen.getByLabelText('09:00: 4'));

    expect(onFilterChange).toHaveBeenCalledWith('2026-06-15T09:00:00Z', '2026-06-15T10:00:00Z');
    await waitFor(() => {
      expect(api.get).toHaveBeenCalledWith(
        expect.stringContaining('bucket=five_minute&from=2026-06-15T09:00:00Z&to=2026-06-15T10:00:00Z'),
      );
    });
  });

  it('clicking a 5-minute bar only calls onFilterChange', async () => {
    const user = userEvent.setup();
    const onFilterChange = vi.fn();
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.includes('bucket=day')) return Promise.resolve([]);
      if (url.includes('bucket=hour')) return Promise.resolve([]);
      return Promise.resolve([{ bucket_start_utc: '2026-06-15T14:05:00Z', bucket_end_utc: '2026-06-15T14:10:00Z', count: 1 }]);
    });

    renderWithProviders(
      <ActivityDrilldownPanel deviceId="dev-001" kind="heartbeats" onFilterChange={onFilterChange} />,
    );

    await waitFor(() => {
      expect(screen.getByTestId('bar-2026-06-15T14:05:00Z')).toBeInTheDocument();
    });

    const callCountBefore = vi.mocked(api.get).mock.calls.length;
    await user.click(screen.getByLabelText('14:05: 1'));

    expect(onFilterChange).toHaveBeenCalledWith('2026-06-15T14:05:00Z', '2026-06-15T14:10:00Z');
    // No new queries should have been fired as a result of this click.
    expect(vi.mocked(api.get).mock.calls.length).toBe(callCountBefore);
  });
});
