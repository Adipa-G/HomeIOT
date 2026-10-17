import React from 'react';
import { parseVisualizationConfig, type VisualizationConfig } from '../lib/visualization';
import type { ChartSeriesPoint } from '../types/api';
import { GaugeVisualization } from './visualizations/GaugeVisualization';
import { NumberDisplayVisualization } from './visualizations/NumberDisplayVisualization';
import { ProgressBarVisualization } from './visualizations/ProgressBarVisualization';
import { TextDisplayVisualization } from './visualizations/TextDisplayVisualization';
import { TimeSeriesChart } from './visualizations/TimeSeriesChart';

interface ModuleVariableVisualizerProps {
  type: string;
  config?: VisualizationConfig | unknown;
  value: string | number | null;
  series?: ChartSeriesPoint[]; // Chart history (oldest to newest), aggregated by the API
  displayName: string;
  compact?: boolean; // Smaller chart height for dense layouts such as dashboard tiles
}

/**
 * Main visualizer component
 */
export const ModuleVariableVisualizer: React.FC<ModuleVariableVisualizerProps> = ({
  type,
  config,
  value,
  series,
  displayName,
  compact,
}) => {
  // Parse numeric value
  const numValue = typeof value === 'number'
    ? value
    : typeof value === 'string' && value.trim() !== ''
      ? Number(value)
      : null;

  if (type !== 'text_display' && (numValue === null || typeof numValue !== 'number' || Number.isNaN(numValue))) {
    return (
      <div className="text-center text-sm text-gray-500">
        No valid data: {value === null ? 'null' : String(value)}
      </div>
    );
  }

  const visualizationConfig = parseVisualizationConfig(config);

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
      <h4 className="mb-3 text-sm font-medium text-gray-700">{displayName}</h4>
      {type === 'gauge' && <GaugeVisualization value={numValue ?? 0} config={visualizationConfig} />}
      {type === 'progress_bar' && <ProgressBarVisualization value={numValue ?? 0} config={visualizationConfig} />}
      {type === 'number_display' && <NumberDisplayVisualization value={numValue ?? 0} config={visualizationConfig} />}
      {type === 'text_display' && <TextDisplayVisualization value={value} config={visualizationConfig} />}
      {type === 'bar_chart' && <TimeSeriesChart kind="bar" value={numValue ?? 0} series={series} config={visualizationConfig} compact={compact} />}
      {type === 'line_chart' && <TimeSeriesChart kind="line" value={numValue ?? 0} series={series} config={visualizationConfig} compact={compact} />}
      {!type && (
        <div className="text-center text-sm text-gray-500">
          Unknown visualization type
        </div>
      )}
    </div>
  );
};
