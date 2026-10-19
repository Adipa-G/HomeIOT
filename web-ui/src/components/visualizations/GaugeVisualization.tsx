import { formatValue, getThresholdColor, type VisualizationConfig } from '../../lib/visualization';

/**
 * Gauge visualization - circular SVG gauge. The dial fills the available width up to a fixed
 * cap so gauges stay the same size whether their container is narrow or wide.
 */
export function GaugeVisualization({ value, config, compact }: { value: number; config?: VisualizationConfig; compact?: boolean }) {
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
    <div className={`flex flex-col items-center ${compact ? 'gap-1' : 'gap-3'}`}>
      {/* The arc ends at y≈86, so the viewBox is cropped to avoid dead space below the dial. */}
      <svg
        data-testid="gauge-svg"
        viewBox="0 0 100 90"
        className={`w-full drop-shadow-sm ${compact ? 'max-w-32' : 'max-w-48'}`}
      >
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
        <div className="text-lg font-semibold whitespace-nowrap" style={{ color }}>
          {formatValue(value, config?.decimals, config?.unit)}
        </div>
        <div className="text-xs whitespace-nowrap text-gray-500">
          Range: {min} — {max}
        </div>
      </div>
    </div>
  );
}
