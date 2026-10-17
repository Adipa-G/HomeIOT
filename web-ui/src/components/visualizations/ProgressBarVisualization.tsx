import { formatValue, getThresholdColor, type VisualizationConfig } from '../../lib/visualization';

/**
 * Progress bar visualization
 */
export function ProgressBarVisualization({ value, config }: { value: number; config?: VisualizationConfig }) {
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
