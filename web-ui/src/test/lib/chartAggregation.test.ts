import { describe, it, expect } from 'vitest';
import {
  BAR_SLOT_PX,
  LINE_SLOT_PX,
  fitBuckets,
  fromSeriesPoints,
  isAggregated,
  maxBucketsForWidth,
  type ChartBucket,
} from '../../lib/chartAggregation';

const bucket = (avg: number | null, count = 1, min = avg, max = avg, start = 's', end = 'e'): ChartBucket => ({
  avg,
  min,
  max,
  count: avg === null ? 0 : count,
  start,
  end,
});

describe('maxBucketsForWidth', () => {
  it('divides the plot width by the slot size of the chart kind', () => {
    expect(maxBucketsForWidth('bar', 250)).toBe(Math.floor(250 / BAR_SLOT_PX));
    expect(maxBucketsForWidth('line', 250)).toBe(Math.floor(250 / LINE_SLOT_PX));
  });

  it('never returns less than one bucket', () => {
    expect(maxBucketsForWidth('bar', 0)).toBe(1);
    expect(maxBucketsForWidth('line', -10)).toBe(1);
  });
});

describe('fromSeriesPoints', () => {
  it('returns an empty list for missing points', () => {
    expect(fromSeriesPoints(undefined)).toEqual([]);
  });

  it('maps API points and fills min/max from avg when absent', () => {
    expect(
      fromSeriesPoints([
        { start_utc: 't1', end_utc: 't2', avg: 5, min: 1, max: 9, count: 3 },
        { start_utc: 't3', end_utc: 't3', avg: 7, min: null, max: null, count: 1 },
      ]),
    ).toEqual([
      { avg: 5, min: 1, max: 9, count: 3, start: 't1', end: 't2' },
      { avg: 7, min: 7, max: 7, count: 1, start: 't3', end: 't3' },
    ]);
  });

  it('turns empty or invalid buckets into gaps', () => {
    const [empty, zeroCount] = fromSeriesPoints([
      { start_utc: 't1', end_utc: 't2', avg: null, min: null, max: null, count: 0 },
      { start_utc: 't3', end_utc: 't4', avg: 4, min: 4, max: 4, count: 0 },
    ]);
    expect(empty).toEqual({ avg: null, min: null, max: null, count: 0, start: 't1', end: 't2' });
    expect(zeroCount.avg).toBeNull();
    expect(zeroCount.count).toBe(0);
  });
});

describe('fitBuckets', () => {
  it('returns the input unchanged when it already fits', () => {
    const input = [bucket(1), bucket(2)];
    expect(fitBuckets(input, 5)).toBe(input);
  });

  it('merges with a count-weighted average and the overall min/max', () => {
    const [merged] = fitBuckets([bucket(10, 1, 9, 11, 'a', 'b'), bucket(20, 3, 15, 25, 'c', 'd')], 1);
    expect(merged).toEqual({ avg: 17.5, min: 9, max: 25, count: 4, start: 'a', end: 'd' });
  });

  it('aligns groups to the newest end so the latest bucket is complete', () => {
    const input = [1, 2, 3, 4, 5].map((v) => bucket(v));
    const fitted = fitBuckets(input, 2);
    expect(fitted.map((b) => b.avg)).toEqual([1.5, 4]);
    expect(fitted.map((b) => b.count)).toEqual([2, 3]);
  });

  it('ignores gaps inside a group and keeps all-empty groups as gaps', () => {
    const fitted = fitBuckets([bucket(null), bucket(null), bucket(4), bucket(null)], 2);
    expect(fitted[0]).toMatchObject({ avg: null, min: null, max: null, count: 0 });
    expect(fitted[1]).toMatchObject({ avg: 4, min: 4, max: 4, count: 1 });
  });

  it('reduces 1440 samples to the requested maximum', () => {
    const input = Array.from({ length: 1440 }, (_, i) => bucket(i));
    const fitted = fitBuckets(input, 41);
    expect(fitted.length).toBeLessThanOrEqual(41);
    expect(fitted.reduce((n, b) => n + b.count, 0)).toBe(1440);
    expect(fitted[fitted.length - 1].max).toBe(1439);
  });
});

describe('isAggregated', () => {
  it('is true only when a bucket holds more than one sample', () => {
    expect(isAggregated([bucket(1), bucket(2)])).toBe(false);
    expect(isAggregated([bucket(1), bucket(2, 2)])).toBe(true);
    expect(isAggregated([])).toBe(false);
  });
});
