import { formatValue, getThresholdColor, type VisualizationConfig } from '../../lib/visualization';

/**
 * Text display - simple text value
 */
export function TextDisplayVisualization({ value, config }: { value: string | number | null; config?: VisualizationConfig }) {
  const numericValue = typeof value === 'string' && value.trim() !== '' ? Number(value) : value;
  const displayValue = typeof numericValue === 'number' && Number.isFinite(numericValue)
    ? formatValue(numericValue, config?.decimals, config?.unit)
    : value ?? '—';
  const color = typeof numericValue === 'number' && Number.isFinite(numericValue) && config?.thresholds?.length
    ? getThresholdColor(numericValue, config.thresholds)
    : undefined;

  return (
    <div className="text-lg font-medium text-gray-900" style={color ? { color } : undefined}>
      {displayValue}
    </div>
  );
}
