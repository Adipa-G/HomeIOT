interface Segment {
  value: number;
  color: string;
  label: string;
}

export interface ActivityBarChartProps<T> {
  title: string;
  buckets: T[];
  getSegments: (bucket: T) => Segment[];
  getBucketKey: (bucket: T) => string;
  formatLabel: (bucket: T) => string;
  onBarClick?: (bucket: T) => void;
  selectedBucketKey?: string | null;
  isLoading?: boolean;
  legend?: { label: string; color: string }[];
}

const CHART_HEIGHT = 120;
const BAR_GAP_RATIO = 0.4;
const MAX_BAR_WIDTH = 2;

export function ActivityBarChart<T>({
  title,
  buckets,
  getSegments,
  getBucketKey,
  formatLabel,
  onBarClick,
  selectedBucketKey,
  isLoading,
  legend,
}: ActivityBarChartProps<T>) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-3">
        <div className="mb-2 text-xs font-semibold text-gray-700">{title}</div>
        <p className="text-xs text-gray-400">Loading…</p>
      </div>
    );
  }

  if (buckets.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-3">
        <div className="mb-2 text-xs font-semibold text-gray-700">{title}</div>
        <p className="text-xs text-gray-400">No data</p>
      </div>
    );
  }

  const totals = buckets.map((b) => getSegments(b).reduce((sum, s) => sum + s.value, 0));
  const maxTotal = Math.max(1, ...totals);

  const viewWidth = 100;
  const barSlot = viewWidth / buckets.length;
  const barWidth = Math.min(barSlot * (1 - BAR_GAP_RATIO), MAX_BAR_WIDTH);

  const labelIndices = new Set([0, Math.floor((buckets.length - 1) / 2), buckets.length - 1]);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3">
      <div className="mb-2 text-xs font-semibold text-gray-700">{title}</div>
      <svg
        viewBox={`0 0 ${viewWidth} ${CHART_HEIGHT}`}
        width="100%"
        height={CHART_HEIGHT}
        preserveAspectRatio="none"
        role="img"
        aria-label={title}
      >
        {buckets.map((bucket, i) => {
          const key = getBucketKey(bucket);
          const segments = getSegments(bucket);
          const total = totals[i];
          const x = i * barSlot + (barSlot - barWidth) / 2;
          const isSelected = selectedBucketKey === key;

          let yCursor = CHART_HEIGHT;
          const rects = segments.map((seg, si) => {
            const segHeight = maxTotal > 0 ? (seg.value / maxTotal) * CHART_HEIGHT : 0;
            yCursor -= segHeight;
            return (
              <rect
                key={si}
                x={x}
                y={yCursor}
                width={barWidth}
                height={segHeight}
                fill={seg.color}
              />
            );
          });

          return (
            <g key={key} data-testid={`bar-${key}`}>
              {rects}
              {isSelected && (
                <rect
                  x={x}
                  y={0.5}
                  width={barWidth}
                  height={CHART_HEIGHT - 1}
                  fill="none"
                  stroke="#1d4ed8"
                  strokeWidth={1.5}
                  vectorEffect="non-scaling-stroke"
                />
              )}
              <rect
                x={x}
                y={0}
                width={barWidth}
                height={CHART_HEIGHT}
                fill="transparent"
                onClick={() => onBarClick?.(bucket)}
                style={{ cursor: onBarClick ? 'pointer' : 'default' }}
                aria-label={`${formatLabel(bucket)}: ${total}`}
                role={onBarClick ? 'button' : undefined}
              />
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex justify-between text-[10px] text-gray-400">
        {buckets.map((bucket, i) =>
          labelIndices.has(i) ? <span key={i}>{formatLabel(bucket)}</span> : null,
        )}
      </div>
      {legend && (
        <div className="mt-2 flex flex-wrap gap-3 text-[10px] text-gray-500">
          {legend.map((item) => (
            <span key={item.label} className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-sm" style={{ backgroundColor: item.color }} />
              {item.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
