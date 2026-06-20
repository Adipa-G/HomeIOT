import React from 'react';
import type { ModuleVariableVisualizationItem, ModuleResultListItem } from '../types/api';

interface VisualizationCardProps {
  visualization: ModuleVariableVisualizationItem;
  value: string | null | undefined;
  executionHistory?: ModuleResultListItem[];
}

const parseVisualizationConfig = (config: unknown): Record<string, unknown> => {
  if (!config) return {};
  if (typeof config === 'string') {
    try {
      return JSON.parse(config);
    } catch {
      return {};
    }
  }
  if (typeof config === 'object') return config as Record<string, unknown>;
  return {};
};

const extractNumericValue = (value: string | null | undefined): number | null => {
  if (!value) return null;
  try {
    const num = parseFloat(value);
    return isNaN(num) ? null : num;
  } catch {
    return null;
  }
};

export const VisualizationCard: React.FC<VisualizationCardProps> = ({
  visualization,
  value,
  executionHistory = [],
}) => {
  const config = parseVisualizationConfig(visualization.visualization_config);
  const vizType = visualization.visualization_type;
  const numValue = extractNumericValue(value);

  // Gauge visualization
  if (vizType === 'gauge') {
    const min = typeof config.min === 'number' ? config.min : 0;
    const max = typeof config.max === 'number' ? config.max : 100;
    const displayValue = numValue ?? 0;
    const percentage = Math.max(0, Math.min(100, ((displayValue - min) / (max - min)) * 100));
    const units = typeof config.units === 'string' ? config.units : '';

    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h4 className="mb-3 text-sm font-medium text-gray-900">{visualization.display_name}</h4>
        <div className="flex flex-col items-center">
          <div className="relative h-32 w-32 rounded-full border-4 border-gray-200 flex items-center justify-center bg-gray-50">
            <div className="absolute inset-0 rounded-full" style={{
              background: `conic-gradient(#3b82f6 0deg ${percentage * 3.6}deg, #e5e7eb ${percentage * 3.6}deg 360deg)`,
              clipPath: 'polygon(50% 50%, 50% 0, 100% 0, 100% 100%, 0 100%, 0 0)',
            }} />
            <div className="relative flex flex-col items-center">
              <span className="text-2xl font-bold text-gray-900">{displayValue.toFixed(1)}</span>
              {units && <span className="text-xs text-gray-500">{units}</span>}
            </div>
          </div>
          <div className="mt-3 text-center text-xs text-gray-500">
            Range: {min} – {max}
          </div>
        </div>
      </div>
    );
  }

  // Progress bar visualization
  if (vizType === 'progress_bar') {
    const min = typeof config.min === 'number' ? config.min : 0;
    const max = typeof config.max === 'number' ? config.max : 100;
    const displayValue = numValue ?? 0;
    const percentage = Math.max(0, Math.min(100, ((displayValue - min) / (max - min)) * 100));
    const units = typeof config.units === 'string' ? config.units : '';

    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h4 className="mb-3 text-sm font-medium text-gray-900">{visualization.display_name}</h4>
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <div className="h-4 w-full overflow-hidden rounded-full bg-gray-200">
              <div
                className="h-full bg-blue-600 transition-all duration-300"
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>
          <span className="text-sm font-medium text-gray-900">{percentage.toFixed(0)}%</span>
        </div>
        {units && <p className="mt-2 text-xs text-gray-500">{units}</p>}
      </div>
    );
  }

  // Number display visualization
  if (vizType === 'number_display') {
    const units = typeof config.units === 'string' ? config.units : '';
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h4 className="mb-3 text-sm font-medium text-gray-900">{visualization.display_name}</h4>
        <div className="rounded-lg bg-blue-50 p-4">
          <div className="text-center">
            <span className="text-3xl font-bold text-blue-900">{value ?? '—'}</span>
            {units && <span className="ml-2 text-lg text-blue-700">{units}</span>}
          </div>
        </div>
      </div>
    );
  }

  // Text display visualization
  if (vizType === 'text_display') {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h4 className="mb-3 text-sm font-medium text-gray-900">{visualization.display_name}</h4>
        <div className="rounded bg-gray-50 p-3">
          <p className="font-mono text-sm text-gray-700">{value ?? '—'}</p>
        </div>
      </div>
    );
  }

  // Line chart visualization (basic placeholder)
  if (vizType === 'line_chart') {
    // For MVP, show placeholder chart
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h4 className="mb-3 text-sm font-medium text-gray-900">{visualization.display_name}</h4>
        <div className="h-48 w-full rounded-lg bg-gray-50 flex items-center justify-center">
          <p className="text-xs text-gray-500">Chart visualization (coming soon)</p>
        </div>
        {executionHistory.length > 0 && (
          <p className="mt-2 text-xs text-gray-500">{executionHistory.length} data points available</p>
        )}
      </div>
    );
  }

  // Bar chart visualization (basic placeholder)
  if (vizType === 'bar_chart') {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h4 className="mb-3 text-sm font-medium text-gray-900">{visualization.display_name}</h4>
        <div className="h-48 w-full rounded-lg bg-gray-50 flex items-center justify-center">
          <p className="text-xs text-gray-500">Bar chart visualization (coming soon)</p>
        </div>
        {executionHistory.length > 0 && (
          <p className="mt-2 text-xs text-gray-500">{executionHistory.length} data points available</p>
        )}
      </div>
    );
  }

  // Default visualization
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h4 className="mb-3 text-sm font-medium text-gray-900">{visualization.display_name}</h4>
      <div className="rounded bg-gray-50 p-3">
        <p className="font-mono text-sm text-gray-700">{value ?? '—'}</p>
      </div>
    </div>
  );
};
