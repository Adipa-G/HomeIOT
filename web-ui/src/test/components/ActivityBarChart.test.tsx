import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ActivityBarChart } from '../../components/ActivityBarChart';

interface Bucket {
  bucket_start_utc: string;
  bucket_end_utc: string;
  count: number;
}

const buckets: Bucket[] = [
  { bucket_start_utc: '2026-06-01T00:00:00Z', bucket_end_utc: '2026-06-02T00:00:00Z', count: 3 },
  { bucket_start_utc: '2026-06-02T00:00:00Z', bucket_end_utc: '2026-06-03T00:00:00Z', count: 7 },
];

describe('ActivityBarChart', () => {
  it('renders a bar per bucket', () => {
    render(
      <ActivityBarChart
        title="By day"
        buckets={buckets}
        getSegments={(b) => [{ value: b.count, color: '#3b82f6', label: 'heartbeats' }]}
        getBucketKey={(b) => b.bucket_start_utc}
        formatLabel={(b) => b.bucket_start_utc}
      />,
    );

    expect(screen.getByText('By day')).toBeInTheDocument();
    expect(screen.getByTestId('bar-2026-06-01T00:00:00Z')).toBeInTheDocument();
    expect(screen.getByTestId('bar-2026-06-02T00:00:00Z')).toBeInTheDocument();
  });

  it('fires onBarClick with the correct bucket', async () => {
    const user = userEvent.setup();
    const onBarClick = vi.fn();
    render(
      <ActivityBarChart
        title="By day"
        buckets={buckets}
        getSegments={(b) => [{ value: b.count, color: '#3b82f6', label: 'heartbeats' }]}
        getBucketKey={(b) => b.bucket_start_utc}
        formatLabel={(b) => b.bucket_start_utc}
        onBarClick={onBarClick}
      />,
    );

    await user.click(screen.getByLabelText('2026-06-02T00:00:00Z: 7'));

    expect(onBarClick).toHaveBeenCalledWith(buckets[1]);
  });

  it('shows loading state', () => {
    render(
      <ActivityBarChart
        title="By day"
        buckets={[]}
        getSegments={() => []}
        getBucketKey={(b: Bucket) => b.bucket_start_utc}
        formatLabel={(b: Bucket) => b.bucket_start_utc}
        isLoading
      />,
    );

    expect(screen.getByText('Loading…')).toBeInTheDocument();
  });

  it('shows empty state when there is no data', () => {
    render(
      <ActivityBarChart
        title="By day"
        buckets={[]}
        getSegments={() => []}
        getBucketKey={(b: Bucket) => b.bucket_start_utc}
        formatLabel={(b: Bucket) => b.bucket_start_utc}
      />,
    );

    expect(screen.getByText('No data')).toBeInTheDocument();
  });
});
