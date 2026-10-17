/**
 * Shared, framework-free helpers for module variable visualizations.
 */

export interface VisualizationConfig {
  min?: number;
  max?: number;
  unit?: string;
  decimals?: number;
  color?: string;
  barColor?: string;
  lineColor?: string;
  fillColor?: string;
  thresholds?: Array<{ value: number; color: string }>;
  historyPoints?: number; // Number of recent runs a line/bar chart covers (max 1440); averaged server-side to fit
}

export const DEFAULT_COLOR = '#3b82f6';

export const CHART_VISUALIZATION_TYPES: ReadonlySet<string> = new Set(['bar_chart', 'line_chart']);

export function isChartVisualization(type: string | null | undefined): boolean {
  return !!type && CHART_VISUALIZATION_TYPES.has(type);
}

/**
 * Visualization config arrives either as an object or as a JSON string; invalid JSON yields undefined.
 */
export function parseVisualizationConfig(config: unknown): VisualizationConfig | undefined {
  if (config === null || config === undefined || config === '') return undefined;
  if (typeof config === 'string') {
    try {
      const parsed = JSON.parse(config);
      return parsed && typeof parsed === 'object' ? (parsed as VisualizationConfig) : undefined;
    } catch {
      return undefined;
    }
  }
  return typeof config === 'object' ? (config as VisualizationConfig) : undefined;
}

/**
 * Simple utility to extract JSON value using dot notation path
 */
export function extractJsonValue(data: unknown, path: string): string | number | null {
  if (!data || !path) return null;
  try {
    const keys = path.split('.');
    let result: unknown = data;
    for (const key of keys) {
      result = (result as Record<string, unknown> | null | undefined)?.[key];
    }
    return (result ?? null) as string | number | null;
  } catch {
    return null;
  }
}

/**
 * Format a number with specified decimals and unit
 */
export function formatValue(value: number | null, decimals?: number, unit?: string): string {
  if (value === null) return '—';
  const formatted = decimals !== undefined ? value.toFixed(decimals) : String(value);
  return unit ? `${formatted} ${unit}` : formatted;
}

/**
 * Get color based on thresholds
 */
export function getThresholdColor(
  value: number,
  thresholds?: Array<{ value: number; color: string }>,
  defaultColor: string = DEFAULT_COLOR,
): string {
  if (!thresholds || thresholds.length === 0) return defaultColor;
  // Find the highest threshold that value meets or exceeds
  const sorted = [...thresholds].sort((a, b) => a.value - b.value);
  let matchedColor = defaultColor; // default if value is below all thresholds
  for (const threshold of sorted) {
    if (value >= threshold.value) {
      matchedColor = threshold.color;
    }
  }
  return matchedColor;
}
