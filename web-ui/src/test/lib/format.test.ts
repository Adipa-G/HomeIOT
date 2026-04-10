import { describe, it, expect } from 'vitest';
import { formatUtc, formatBytes, formatMs } from '../../lib/format';

describe('formatUtc', () => {
  it('returns em dash for null', () => {
    expect(formatUtc(null)).toBe('—');
  });

  it('returns em dash for undefined', () => {
    expect(formatUtc(undefined)).toBe('—');
  });

  it('formats ISO date string', () => {
    const result = formatUtc('2026-05-30T10:30:00Z');
    expect(result).toMatch(/2026-05-30/);
    expect(result).toMatch(/\d{2}:\d{2}:\d{2}/);
  });

  it('returns raw string on parse failure', () => {
    expect(formatUtc('not-a-date')).toBe('not-a-date');
  });
});

describe('formatBytes', () => {
  it('returns "0 B" for zero', () => {
    expect(formatBytes(0)).toBe('0 B');
  });

  it('formats bytes', () => {
    expect(formatBytes(512)).toBe('512.0 B');
  });

  it('formats kilobytes', () => {
    expect(formatBytes(1024)).toBe('1.0 KB');
  });

  it('formats megabytes', () => {
    expect(formatBytes(1024 * 1024)).toBe('1.0 MB');
  });

  it('formats fractional megabytes', () => {
    expect(formatBytes(1536 * 1024)).toBe('1.5 MB');
  });
});

describe('formatMs', () => {
  it('returns em dash for null', () => {
    expect(formatMs(null)).toBe('—');
  });

  it('returns em dash for undefined', () => {
    expect(formatMs(undefined)).toBe('—');
  });

  it('formats milliseconds below 1000', () => {
    expect(formatMs(500)).toBe('500ms');
  });

  it('formats seconds for >= 1000', () => {
    expect(formatMs(1500)).toBe('1.5s');
  });

  it('formats zero', () => {
    expect(formatMs(0)).toBe('0ms');
  });
});
