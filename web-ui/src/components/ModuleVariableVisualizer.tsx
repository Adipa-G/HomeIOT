import React from 'react';

export interface VisualizationConfig {
  min?: number;
  max?: number;
  unit?: string;
  decimals?: number;
  color?: string;
  thresholds?: Array<{ value: number; color: string }>;
  historyPoints?: number; // Number of historical points to display (for line/bar charts)
}

interface ModuleVariableVisualizerProps {
  type: string;
  config?: VisualizationConfig | unknown;
  value: string | number | null;
  values?: (string | number | null)[]; // Optional array of historical values (oldest to newest)
  displayName: string;
}

/**
 * Simple utility to extract JSON value using dot notation path
 */
export function extractJsonValue(data: any, path: string): string | number | null {
  if (!data || !path) return null;
  try {
    const keys = path.split('.');
    let result = data;
    for (const key of keys) {
      result = result?.[key];
    }
    return result ?? null;
  } catch {
    return null;
  }
}

/**
 * Format a number with specified decimals and unit
 */
function formatValue(value: number | null, decimals?: number, unit?: string): string {
  if (value === null) return '—';
  const formatted = decimals !== undefined ? value.toFixed(decimals) : String(value);
  return unit ? `${formatted} ${unit}` : formatted;
}

/**
 * Get color based on thresholds
 */
export function getThresholdColor(value: number, thresholds?: Array<{ value: number; color: string }>): string {
  if (!thresholds || thresholds.length === 0) return '#3b82f6';
  // Find the highest threshold that value meets or exceeds
  const sorted = [...thresholds].sort((a, b) => a.value - b.value);
  let matchedColor = '#3b82f6'; // default if value is below all thresholds
  for (const threshold of sorted) {
    if (value >= threshold.value) {
      matchedColor = threshold.color;
    }
  }
  return matchedColor;
}

/**
 * Gauge visualization - circular SVG gauge
 */
function GaugeVisualization({ value, config }: { value: number; config?: VisualizationConfig }) {
  const min = config?.min ?? 0;
  const max = config?.max ?? 100;
  const clampedValue = Math.max(min, Math.min(max, value));
  const percentage = ((clampedValue - min) / (max - min)) * 100;
  
  // 270 degree gauge spanning from upper-left through bottom to upper-right
  // Start: 135° (upper-left), End: 45° (upper-right), spans 270° through left, bottom, right
  const startAngle = 135;
  const sweepDegrees = 270;
  const currentAngle = startAngle + (percentage / 100) * sweepDegrees;

  const radius = 45;
  const cx = 50;
  const cy = 50;
  
  // Calculate needle endpoint (points from center to arc)
  const needleAngleRad = (currentAngle * Math.PI) / 180;
  const x2 = cx + radius * Math.cos(needleAngleRad);
  const y2 = cy + radius * Math.sin(needleAngleRad);
  
  // Start position for arc (at 135 degrees = upper-left)
  const startAngleRad = (startAngle * Math.PI) / 180;
  const startX = cx + radius * Math.cos(startAngleRad);
  const startY = cy + radius * Math.sin(startAngleRad);
  
  // End position for full gauge (at 135 + 270 = 405 = 45 degrees = upper-right)
  const fullEndAngleRad = ((startAngle + sweepDegrees) * Math.PI) / 180;
  const fullEndX = cx + radius * Math.cos(fullEndAngleRad);
  const fullEndY = cy + radius * Math.sin(fullEndAngleRad);
  
  // Current arc endpoint
  const currentAngleRad = (currentAngle * Math.PI) / 180;
  const arcX = cx + radius * Math.cos(currentAngleRad);
  const arcY = cy + radius * Math.sin(currentAngleRad);
  
  // Large arc flag: set to 1 if sweep is > 180 degrees
  const largArcFlag = sweepDegrees > 180 ? 1 : 0;
  // For current colored arc
  const currentSweep = (percentage / 100) * sweepDegrees;
  const coloredLargArcFlag = currentSweep > 180 ? 1 : 0;

  const color = getThresholdColor(value, config?.thresholds);

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width="100%" height="100%" viewBox="0 0 100 100" className="drop-shadow-sm">
        {/* Background arc (full 270 degrees from upper-left through bottom to upper-right) */}
        <path
          d={`M ${startX} ${startY} A ${radius} ${radius} 0 ${largArcFlag} 1 ${fullEndX} ${fullEndY}`}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Colored arc (from start to current percentage position) */}
        <path
          d={`M ${startX} ${startY} A ${radius} ${radius} 0 ${coloredLargArcFlag} 1 ${arcX} ${arcY}`}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Needle */}
        <line x1={cx} y1={cy} x2={x2} y2={y2} stroke={color} strokeWidth="2" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="3" fill={color} />
      </svg>
      <div className="text-center">
        <div className="text-lg font-semibold" style={{ color }}>
          {formatValue(value, config?.decimals, config?.unit)}
        </div>
        <div className="text-xs text-gray-500">
          {min} — {max}
        </div>
      </div>
    </div>
  );
}

/**
 * Progress bar visualization
 */
function ProgressBarVisualization({ value, config }: { value: number; config?: VisualizationConfig }) {
  const min = config?.min ?? 0;
  const max = config?.max ?? 100;
  const clampedValue = Math.max(min, Math.min(max, value));
  const percentage = ((clampedValue - min) / (max - min)) * 100;
  const color = getThresholdColor(value, config?.thresholds);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">{formatValue(value, config?.decimals, config?.unit)}</span>
        <span className="text-xs text-gray-500">{percentage.toFixed(0)}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-200 overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${percentage}%`,
            backgroundColor: color,
          }}
        />
      </div>
      <div className="flex justify-between text-xs text-gray-500">
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}

/**
 * Number display - large formatted number
 */
function NumberDisplayVisualization({ value, config }: { value: number; config?: VisualizationConfig }) {
  const color = getThresholdColor(value, config?.thresholds);
  const minMax = config?.min !== undefined && config?.max !== undefined;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="text-4xl font-bold" style={{ color }}>
        {formatValue(value, config?.decimals, '')}
      </div>
      {config?.unit && <div className="text-sm text-gray-600">{config.unit}</div>}
      {minMax && (
        <div className="text-xs text-gray-500">
          Range: {config.min} — {config.max}
        </div>
      )}
    </div>
  );
}

/**
 * Text display - simple text value
 */
function TextDisplayVisualization({ value, config }: { value: string | number | null; config?: VisualizationConfig }) {
  return (
    <div className="text-lg font-medium text-gray-900">
      {formatValue(Number(value) ?? null, config?.decimals, config?.unit) || String(value) || '—'}
    </div>
  );
}

/**
 * Bar chart - shows multiple bars for historical values or single bar for current value
 */
function BarChartVisualization({ value, values, config }: { value: number; values?: (string | number | null)[]; config?: VisualizationConfig }) {
  const min = config?.min ?? 0;
  const max = config?.max ?? 100;
  
  // Use historical values if available, otherwise just show current value
  const dataPoints = values && values.length > 0 
    ? values.map(v => typeof v === 'string' ? parseFloat(v) : v).filter(v => v !== null) as number[]
    : [value];
  
  const barWidth = Math.max(6, Math.floor(80 / dataPoints.length));
  const spacing = Math.max(1, Math.floor((90 - barWidth * dataPoints.length) / (dataPoints.length - 1)));
  const totalWidth = barWidth * dataPoints.length + spacing * (dataPoints.length - 1);
  const startX = 50 - totalWidth / 2;

  return (
    <div className="flex items-end gap-2 h-24">
      <svg width="100" height="100" viewBox="0 0 100 120" className="flex-1">
        {/* Grid lines */}
        <line x1="5" y1="100" x2="95" y2="100" stroke="#e5e7eb" strokeWidth="1" />
        <line x1="5" y1="70" x2="95" y2="70" stroke="#e5e7eb" strokeWidth="1" strokeDasharray="2" />
        <line x1="5" y1="40" x2="95" y2="40" stroke="#e5e7eb" strokeWidth="1" strokeDasharray="2" />
        {/* Bars */}
        {dataPoints.map((val, i) => {
          const clampedVal = Math.max(min, Math.min(max, val));
          const percentage = ((clampedVal - min) / (max - min)) * 100;
          const barColor = getThresholdColor(val, config?.thresholds);
          const barHeight = (percentage / 100) * 60;
          const x = startX + i * (barWidth + spacing);
          return (
            <rect
              key={i}
              x={x}
              y={100 - barHeight}
              width={barWidth}
              height={barHeight}
              fill={barColor}
              opacity={i === dataPoints.length - 1 ? 1 : 0.6}
              rx="1"
            />
          );
        })}
        {/* Axis */}
        <line x1="5" y1="100" x2="5" y2="20" stroke="#d1d5db" strokeWidth="1" />
        <line x1="5" y1="100" x2="95" y2="100" stroke="#d1d5db" strokeWidth="1" />
      </svg>
      <div className="flex flex-col items-end gap-1">
        <div className="text-lg font-semibold" style={{ color: getThresholdColor(value, config?.thresholds) }}>
          {formatValue(value, config?.decimals, '')}
        </div>
        {config?.unit && <div className="text-xs text-gray-500">{config.unit}</div>}
      </div>
    </div>
  );
}

/**
 * Line chart - shows trend line for historical values or single point for current value
 */
function LineChartVisualization({ value, values, config }: { value: number; values?: (string | number | null)[]; config?: VisualizationConfig }) {
  const min = config?.min ?? 0;
  const max = config?.max ?? 100;
  
  // Use historical values if available, otherwise just show current value
  const dataPoints = values && values.length > 0 
    ? values.map(v => typeof v === 'string' ? parseFloat(v) : v).filter(v => v !== null) as number[]
    : [value];
  
  // Map data points to SVG coordinates (distributed across width)
  const numPoints = Math.min(dataPoints.length, 10); // Limit to 10 points for readability
  const lastPoints = dataPoints.slice(-numPoints);
  const xStep = 80 / Math.max(numPoints - 1, 1);
  const points = lastPoints.map((v, i) => {
    const clampedValue = Math.max(min, Math.min(max, v));
    const percentage = ((clampedValue - min) / (max - min)) * 100;
    return {
      x: 10 + i * xStep,
      y: (percentage / 100) * 60,
      value: v,
    };
  });

  const pathData = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${100 - p.y}`).join(' ');
  const fillPath = pathData + ` L ${points[points.length - 1]?.x ?? 90} 100 L 10 100 Z`;
  const fillColor = getThresholdColor(dataPoints[dataPoints.length - 1] ?? value, config?.thresholds);

  return (
    <div className="flex flex-col gap-2 items-center">
      <svg width="140" height="100" viewBox="0 0 100 120" className="drop-shadow-sm">
        {/* Grid lines */}
        <line x1="5" y1="100" x2="95" y2="100" stroke="#e5e7eb" strokeWidth="1" />
        <line x1="5" y1="70" x2="95" y2="70" stroke="#e5e7eb" strokeWidth="1" strokeDasharray="2" />
        <line x1="5" y1="40" x2="95" y2="40" stroke="#e5e7eb" strokeWidth="1" strokeDasharray="2" />
        {/* Fill under line */}
        <path d={fillPath} fill={fillColor} opacity="0.15" />
        {/* Line */}
        <path d={pathData} fill="none" stroke={fillColor} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        {/* Dots */}
        {points.map((p, i) => (
          <circle key={i} cx={p.x} cy={100 - p.y} r="2" fill={fillColor} />
        ))}
        {/* Axis */}
        <line x1="5" y1="100" x2="5" y2="20" stroke="#d1d5db" strokeWidth="1" />
        <line x1="5" y1="100" x2="95" y2="100" stroke="#d1d5db" strokeWidth="1" />
      </svg>
      <div className="text-center">
        <div className="text-lg font-semibold" style={{ color: fillColor }}>
          {formatValue(value, config?.decimals, config?.unit)}
        </div>
        <div className="text-xs text-gray-500">
          {dataPoints.length > 1 ? `${dataPoints.length} points` : 'current'}
        </div>
      </div>
    </div>
  );
}

/**
 * Main visualizer component
 */
export const ModuleVariableVisualizer: React.FC<ModuleVariableVisualizerProps> = ({
  type,
  config,
  value,
  values,
  displayName,
}) => {
  // Parse numeric value
  const numValue = typeof value === 'string' ? parseFloat(value) : value;

  if (numValue === null || isNaN(numValue as number)) {
    return (
      <div className="text-center text-sm text-gray-500">
        No valid data: {value === null ? 'null' : String(value)}
      </div>
    );
  }

  const visualizationConfig = config ? (typeof config === 'string' ? JSON.parse(config) : config) : undefined;

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
      <h4 className="mb-3 text-sm font-medium text-gray-700">{displayName}</h4>
      {type === 'gauge' && <GaugeVisualization value={numValue} config={visualizationConfig} />}
      {type === 'progress_bar' && <ProgressBarVisualization value={numValue} config={visualizationConfig} />}
      {type === 'number_display' && <NumberDisplayVisualization value={numValue} config={visualizationConfig} />}
      {type === 'text_display' && <TextDisplayVisualization value={value} config={visualizationConfig} />}
      {type === 'bar_chart' && <BarChartVisualization value={numValue} values={values} config={visualizationConfig} />}
      {type === 'line_chart' && <LineChartVisualization value={numValue} values={values} config={visualizationConfig} />}
      {!type && (
        <div className="text-center text-sm text-gray-500">
          Unknown visualization type
        </div>
      )}
    </div>
  );
};
