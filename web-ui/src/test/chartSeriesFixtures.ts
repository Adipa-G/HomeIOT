import type { ChartSeriesPoint } from '../types/api';

const BASE = Date.parse('2026-05-10T10:00:00Z');
const iso = (ms: number) => new Date(ms).toISOString().replace('.000Z', 'Z');

/**
 * Raw (unaggregated) chart series: one point per value, one minute apart. `null` entries
 * become empty slots.
 */
export function samplesSeries(values: (number | null)[], stepMinutes = 1): ChartSeriesPoint[] {
  return values.map((v, i) => {
    const at = iso(BASE + i * stepMinutes * 60_000);
    return v === null
      ? { start_utc: at, end_utc: at, avg: null, min: null, max: null, count: 0 }
      : { start_utc: at, end_utc: at, avg: v, min: v, max: v, count: 1 };
  });
}

/**
 * Aggregated chart series: one bucket per entry, `bucketMinutes` wide.
 */
export function bucketSeries(
  buckets: Array<{ avg: number; min: number; max: number; count: number } | null>,
  bucketMinutes = 15,
): ChartSeriesPoint[] {
  return buckets.map((b, i) => {
    const start_utc = iso(BASE + i * bucketMinutes * 60_000);
    const end_utc = iso(BASE + (i + 1) * bucketMinutes * 60_000);
    return b === null
      ? { start_utc, end_utc, avg: null, min: null, max: null, count: 0 }
      : { start_utc, end_utc, ...b };
  });
}
