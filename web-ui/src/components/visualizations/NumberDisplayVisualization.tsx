import { formatValue, getThresholdColor, type VisualizationConfig } from '../../lib/visualization';

/**
 * Number display - large formatted number
 */
export function NumberDisplayVisualization({ value, config }: { value: number; config?: VisualizationConfig }) {
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
