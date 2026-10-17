import type { ChartSeriesPoint } from '../types/api';

/**
 * A plotted slot after client-side fitting; mirrors the API point with parsed fields.
 */
export interface ChartBucket {
  avg: number | null;
  min: number | null;
  max: number | null;
  count: number;
  start: string | null;
  end: string | null;
}

/** Horizontal pixels each bar / line point needs to stay legible. */
export const BAR_SLOT_PX = 8;
export const LINE_SLOT_PX = 6;

export function maxBucketsForWidth(kind: 'bar' | 'line', plotWidth: number): number {
  return Math.max(1, Math.floor(plotWidth / (kind === 'bar' ? BAR_SLOT_PX : LINE_SLOT_PX)));
}

export function fromSeriesPoints(points: ChartSeriesPoint[] | undefined): ChartBucket[] {
  return (points ?? []).map((p) => {
    const hasValue = p.count > 0 && typeof p.avg === 'number' && Number.isFinite(p.avg);
    return {
      avg: hasValue ? p.avg : null,
      min: hasValue ? (p.min ?? p.avg) : null,
      max: hasValue ? (p.max ?? p.avg) : null,
      count: hasValue ? p.count : 0,
      start: p.start_utc ?? null,
      end: p.end_utc ?? p.start_utc ?? null,
    };
  });
}

function mergeBuckets(group: ChartBucket[]): ChartBucket {
  let count = 0;
  let sum = 0;
  let min = Infinity;
  let max = -Infinity;
  for (const b of group) {
    if (b.avg === null || b.count === 0) continue;
    count += b.count;
    sum += b.avg * b.count;
    min = Math.min(min, b.min ?? b.avg);
    max = Math.max(max, b.max ?? b.avg);
  }
  const start = group[0].start;
  const end = group[group.length - 1].end;
  if (count === 0) return { avg: null, min: null, max: null, count: 0, start, end };
  return { avg: sum / count, min, max, count, start, end };
}

/**
 * Merges adjacent buckets (count-weighted average, overall min/max) until at most `maxBuckets`
 * remain. Groups are aligned to the newest end so the latest bucket is always complete.
 */
export function fitBuckets(buckets: ChartBucket[], maxBuckets: number): ChartBucket[] {
  const limit = Math.max(1, maxBuckets);
  if (buckets.length <= limit) return buckets;

  const size = Math.ceil(buckets.length / limit);
  const merged: ChartBucket[] = [];
  for (let end = buckets.length; end > 0; end -= size) {
    merged.push(mergeBuckets(buckets.slice(Math.max(0, end - size), end)));
  }
  return merged.reverse();
}

/** True when any slot represents more than one sample, i.e. averaging is in effect. */
export function isAggregated(buckets: ChartBucket[]): boolean {
  return buckets.some((b) => b.count > 1);
}
