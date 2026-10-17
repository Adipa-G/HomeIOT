import { describe, it, expect } from 'vitest';
import {
  extractJsonValue,
  getThresholdColor,
  isChartVisualization,
  parseVisualizationConfig,
} from '../../lib/visualization';

describe('getThresholdColor', () => {
  it('returns default blue color when no thresholds provided', () => {
    expect(getThresholdColor(50)).toBe('#3b82f6');
    expect(getThresholdColor(100, undefined)).toBe('#3b82f6');
    expect(getThresholdColor(0, [])).toBe('#3b82f6');
  });

  it('returns color of highest threshold value that is met or exceeded', () => {
    const thresholds = [
      { value: 50, color: '#fbbf24' },
      { value: 75, color: '#f97316' },
      { value: 90, color: '#ef4444' },
    ];
    expect(getThresholdColor(40, thresholds)).toBe('#3b82f6'); // Below all thresholds
    expect(getThresholdColor(50, thresholds)).toBe('#fbbf24'); // Meets first
    expect(getThresholdColor(75, thresholds)).toBe('#f97316'); // Meets second
    expect(getThresholdColor(90, thresholds)).toBe('#ef4444'); // Meets third
    expect(getThresholdColor(100, thresholds)).toBe('#ef4444'); // Exceeds all
  });

  it('returns highest matching threshold color for intermediate values', () => {
    const thresholds = [
      { value: 50, color: 'yellow' },
      { value: 100, color: 'red' },
    ];
    expect(getThresholdColor(60, thresholds)).toBe('yellow'); // Above 50, below 100
    expect(getThresholdColor(75, thresholds)).toBe('yellow'); // Above 50, below 100
    expect(getThresholdColor(99, thresholds)).toBe('yellow'); // Above 50, below 100
  });

  it('handles single threshold', () => {
    const thresholds = [{ value: 50, color: 'green' }];
    expect(getThresholdColor(25, thresholds)).toBe('#3b82f6'); // Below threshold
    expect(getThresholdColor(50, thresholds)).toBe('green'); // Meets threshold
    expect(getThresholdColor(75, thresholds)).toBe('green'); // Exceeds threshold
  });

  it('handles unsorted thresholds correctly', () => {
    const thresholds = [
      { value: 90, color: 'red' },
      { value: 50, color: 'yellow' },
      { value: 75, color: 'orange' },
    ];
    expect(getThresholdColor(60, thresholds)).toBe('yellow');
    expect(getThresholdColor(80, thresholds)).toBe('orange');
    expect(getThresholdColor(95, thresholds)).toBe('red');
  });

  it('returns default color for negative values below all thresholds', () => {
    const thresholds = [
      { value: 0, color: 'blue' },
      { value: 50, color: 'yellow' },
    ];
    expect(getThresholdColor(-10, thresholds)).toBe('#3b82f6'); // Below all
    expect(getThresholdColor(0, thresholds)).toBe('blue'); // Meets first
  });
});

describe('extractJsonValue', () => {
  it('extracts value from simple property', () => {
    const data = { temperature: 25.5 };
    const result = extractJsonValue(data, 'temperature');
    expect(result).toBe(25.5);
  });

  it('extracts value from nested property', () => {
    const data = { sensor: { temperature: 25.5 } };
    const result = extractJsonValue(data, 'sensor.temperature');
    expect(result).toBe(25.5);
  });

  it('extracts from deeply nested path', () => {
    const data = { devices: { room1: { temp: { current: 72 } } } };
    const result = extractJsonValue(data, 'devices.room1.temp.current');
    expect(result).toBe(72);
  });

  it('returns null for missing path', () => {
    const data = { temperature: 25.5 };
    const result = extractJsonValue(data, 'humidity');
    expect(result).toBeNull();
  });

  it('returns null for missing nested path', () => {
    const data = { sensor: { temperature: 25.5 } };
    const result = extractJsonValue(data, 'sensor.humidity');
    expect(result).toBeNull();
  });

  it('returns null for null data', () => {
    const result = extractJsonValue(null, 'temperature');
    expect(result).toBeNull();
  });

  it('returns null for empty path', () => {
    const data = { temperature: 25.5 };
    const result = extractJsonValue(data, '');
    expect(result).toBeNull();
  });

  it('handles numeric and string values', () => {
    const data = { number: 42, string: 'hello' };
    expect(extractJsonValue(data, 'number')).toBe(42);
    expect(extractJsonValue(data, 'string')).toBe('hello');
  });
});

describe('parseVisualizationConfig', () => {
  it('returns objects as-is', () => {
    expect(parseVisualizationConfig({ min: 1 })).toEqual({ min: 1 });
  });

  it('parses JSON strings', () => {
    expect(parseVisualizationConfig('{"max":5}')).toEqual({ max: 5 });
  });

  it('returns undefined for empty, invalid or non-object config', () => {
    expect(parseVisualizationConfig(undefined)).toBeUndefined();
    expect(parseVisualizationConfig(null)).toBeUndefined();
    expect(parseVisualizationConfig('')).toBeUndefined();
    expect(parseVisualizationConfig('not json')).toBeUndefined();
    expect(parseVisualizationConfig('42')).toBeUndefined();
  });
});

describe('isChartVisualization', () => {
  it('is true only for bar and line charts', () => {
    expect(isChartVisualization('bar_chart')).toBe(true);
    expect(isChartVisualization('line_chart')).toBe(true);
    expect(isChartVisualization('gauge')).toBe(false);
    expect(isChartVisualization(null)).toBe(false);
  });
});
