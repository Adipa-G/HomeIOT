import { describe, it, expect } from 'vitest';
import { computeYScale, decimalsFor, formatChartTime } from '../../lib/chartScale';

describe('computeYScale', () => {
  it('uses configured min/max with evenly spaced ticks', () => {
    expect(computeYScale([5], { min: 0, max: 40 }, false)).toEqual({ lo: 0, hi: 40, ticks: [0, 10, 20, 30, 40] });
  });

  it('pads a flat series so it is not drawn on the axis edge', () => {
    const { lo, hi } = computeYScale([10, 10], undefined, false);
    expect(lo).toBeLessThan(10);
    expect(hi).toBeGreaterThan(10);
  });

  it('respects a configured min when auto-scaling the max', () => {
    const { lo, hi } = computeYScale([10, 70], { min: 0 }, false);
    expect(lo).toBe(0);
    expect(hi).toBeGreaterThanOrEqual(70);
  });
});

describe('decimalsFor', () => {
  it('returns the decimals needed up to 2', () => {
    expect(decimalsFor(5)).toBe(0);
    expect(decimalsFor(2.5)).toBe(1);
    expect(decimalsFor(0.25)).toBe(2);
    expect(decimalsFor(1 / 3)).toBe(2);
  });
});

describe('formatChartTime', () => {
  it('returns an empty string for invalid timestamps', () => {
    expect(formatChartTime('nope', 0)).toBe('');
  });

  it('includes the date only when the span exceeds a day', () => {
    const iso = '2026-05-10T10:00:00Z';
    const short = formatChartTime(iso, 60_000);
    const long = formatChartTime(iso, 2 * 24 * 60 * 60 * 1000);
    expect(short).not.toBe('');
    expect(long.length).toBeGreaterThan(short.length);
  });
});
