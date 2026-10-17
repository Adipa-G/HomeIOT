import React, { useId } from 'react';
import { fitBuckets, fromSeriesPoints, isAggregated, maxBucketsForWidth, type ChartBucket } from '../../lib/chartAggregation';
import { computeYScale, decimalsFor, formatChartTime } from '../../lib/chartScale';
import { useElementWidth } from '../../lib/useElementWidth';
import { DEFAULT_COLOR, formatValue, getThresholdColor, type VisualizationConfig } from '../../lib/visualization';
import type { ChartSeriesPoint } from '../../types/api';

export interface TimeSeriesChartProps {
  kind: 'bar' | 'line';
  value: number;
  series?: ChartSeriesPoint[];
  config?: VisualizationConfig;
  compact?: boolean;
}

type FilledBucket = ChartBucket & { avg: number };
const isFilled = (b: ChartBucket): b is FilledBucket => b.avg !== null;

/**
 * Bar / line chart over a (possibly server-aggregated) series with a labelled y-axis, time
 * labels, per-point threshold colours and hover tooltips. Adjacent slots are merged so the
 * number of bars / points suits the available width; when slots average several samples the
 * min–max range is drawn as whiskers (bars) or a shaded band (line). Empty slots render as gaps.
 */
export function TimeSeriesChart({ kind, value, series, config, compact }: TimeSeriesChartProps) {
  const [containerRef, width] = useElementWidth<HTMLDivElement>(300);
  const gradientId = `chart-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;

  // Y-axis labels aren't measured yet, so size the slot count from an estimated plot width.
  const fitted = fitBuckets(fromSeriesPoints(series), maxBucketsForWidth(kind, Math.max(10, width - 50)));
  const buckets: ChartBucket[] = fitted.some(isFilled)
    ? fitted
    : [{ avg: value, min: value, max: value, count: 1, start: null, end: null }];
  const filled = buckets.filter(isFilled);
  const aggregated = isAggregated(buckets);
  const lastFilled = buckets.findLastIndex(isFilled);

  const data = filled.flatMap((b) => (aggregated ? [b.avg, b.min ?? b.avg, b.max ?? b.avg] : [b.avg]));
  const { lo, hi, ticks } = computeYScale(data, config, kind === 'bar');
  const thresholds = config?.thresholds;
  const baseColor = (kind === 'bar' ? config?.barColor : config?.lineColor) ?? config?.color ?? DEFAULT_COLOR;
  const colorOf = (v: number) => getThresholdColor(v, thresholds, baseColor);

  const tickDecimals = Math.max(0, ...ticks.map(decimalsFor));
  const tickLabels = ticks.map((t) => t.toFixed(tickDecimals));
  const firstTime = buckets[0].start;
  const lastTime = buckets[buckets.length - 1].end;
  const spanMs = firstTime && lastTime ? new Date(lastTime).getTime() - new Date(firstTime).getTime() : 0;

  const height = compact ? 120 : 180;
  const padLeft = Math.max(...tickLabels.map((l) => l.length)) * 6 + 10;
  const padRight = 8;
  const padTop = 8;
  const padBottom = firstTime ? 18 : 6;
  const plotW = Math.max(10, width - padLeft - padRight);
  const plotH = height - padTop - padBottom;
  const yOf = (v: number) => padTop + plotH * (1 - (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo));

  const fmt = (v: number | null) => formatValue(v, config?.decimals, config?.unit);
  const fmtTime = (iso: string) => new Date(iso).toLocaleString();
  const tooltip = (b: FilledBucket) => {
    const val = b.count > 1 ? `avg ${fmt(b.avg)} (min ${fmt(b.min)} / max ${fmt(b.max)}, ${b.count} samples)` : fmt(b.avg);
    const when = b.start ? (b.end && b.end !== b.start ? `${fmtTime(b.start)} – ${fmtTime(b.end)}` : fmtTime(b.start)) : '';
    return when ? `${val} · ${when}` : val;
  };
  const hasRange = (b: FilledBucket) => aggregated && b.count > 1 && b.min !== null && b.max !== null && b.max > b.min;

  let plot: React.ReactNode;
  if (kind === 'bar') {
    const slot = plotW / buckets.length;
    const barW = Math.max(1, Math.min(slot * 0.7, 40));
    const baseY = yOf(Math.max(lo, Math.min(hi, 0)));
    plot = buckets.map((b, i) => {
      if (!isFilled(b)) return null;
      const y = yOf(b.avg);
      const cx = padLeft + i * slot + slot / 2;
      return (
        <g key={i}>
          <rect
            data-testid="chart-bar"
            x={cx - barW / 2}
            y={Math.min(y, baseY)}
            width={barW}
            height={Math.max(1, Math.abs(baseY - y))}
            fill={colorOf(b.avg)}
            opacity={i === lastFilled ? 1 : 0.75}
            rx={1}
          >
            <title>{tooltip(b)}</title>
          </rect>
          {hasRange(b) && (
            <line
              data-testid="chart-range"
              x1={cx}
              x2={cx}
              y1={yOf(b.max!)}
              y2={yOf(b.min!)}
              stroke="#374151"
              strokeOpacity={0.45}
              strokeWidth={1}
            />
          )}
        </g>
      );
    });
  } else {
    const xOf = (i: number) => (buckets.length === 1 ? padLeft + plotW / 2 : padLeft + (i * plotW) / (buckets.length - 1));
    type Coord = { x: number; b: FilledBucket; i: number };
    // Consecutive filled slots form a segment; empty slots break the line into a gap.
    const segments: Coord[][] = [];
    let current: Coord[] = [];
    buckets.forEach((b, i) => {
      if (isFilled(b)) {
        current.push({ x: xOf(i), b, i });
      } else if (current.length > 0) {
        segments.push(current);
        current = [];
      }
    });
    if (current.length > 0) segments.push(current);

    const drawn = segments.filter((s) => s.length > 1);
    const pathOf = (seg: Coord[], pick: (b: FilledBucket) => number) =>
      seg.map((c, j) => `${j === 0 ? 'M' : 'L'} ${c.x} ${yOf(pick(c.b))}`).join(' ');
    const linePath = drawn.map((seg) => pathOf(seg, (b) => b.avg)).join(' ');
    const bottom = padTop + plotH;
    const areaPath = drawn
      .map((seg) => `${pathOf(seg, (b) => b.avg)} L ${seg[seg.length - 1].x} ${bottom} L ${seg[0].x} ${bottom} Z`)
      .join(' ');
    const rangePath = drawn
      .map((seg) => {
        const upper = pathOf(seg, (b) => b.max ?? b.avg);
        const lower = [...seg].reverse().map((c) => `L ${c.x} ${yOf(c.b.min ?? c.b.avg)}`).join(' ');
        return `${upper} ${lower} Z`;
      })
      .join(' ');
    const hasThresholds = !!thresholds && thresholds.length > 0;
    const strokePaint = hasThresholds ? `url(#${gradientId})` : baseColor;

    // Hard-stop vertical gradient so the line changes colour exactly where it crosses a threshold.
    const stops: Array<{ offset: number; color: string }> = [{ offset: 0, color: colorOf(lo) }];
    if (hasThresholds) {
      for (const t of [...thresholds].sort((a, b) => a.value - b.value)) {
        if (t.value > lo && t.value < hi) {
          const offset = (t.value - lo) / (hi - lo);
          stops.push({ offset, color: stops[stops.length - 1].color });
          stops.push({ offset, color: colorOf(t.value) });
        }
      }
    }
    stops.push({ offset: 1, color: stops[stops.length - 1].color });

    const pointRadius = filled.length > 40 ? 1.5 : 2.5;

    plot = (
      <>
        {hasThresholds && (
          <defs>
            <linearGradient id={gradientId} gradientUnits="userSpaceOnUse" x1={0} y1={yOf(lo)} x2={0} y2={yOf(hi)}>
              {stops.map((s, i) => (
                <stop key={i} offset={s.offset} stopColor={s.color} />
              ))}
            </linearGradient>
          </defs>
        )}
        {drawn.length > 0 && aggregated && (
          <path data-testid="chart-range" d={rangePath} fill={config?.fillColor ?? strokePaint} opacity={0.2} />
        )}
        {drawn.length > 0 && !aggregated && (
          <path
            data-testid="chart-area"
            d={areaPath}
            fill={config?.fillColor ?? strokePaint}
            opacity={config?.fillColor ? 1 : 0.15}
          />
        )}
        {drawn.length > 0 && (
          <path
            data-testid="chart-line"
            d={linePath}
            fill="none"
            stroke={strokePaint}
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        )}
        {segments.flat().map((c) => (
          <circle
            key={c.i}
            data-testid="chart-point"
            cx={c.x}
            cy={yOf(c.b.avg)}
            r={c.i === lastFilled ? 3.5 : pointRadius}
            fill={colorOf(c.b.avg)}
          >
            <title>{tooltip(c.b)}</title>
          </circle>
        ))}
      </>
    );
  }

  const totalSamples = filled.reduce((sum, b) => sum + b.count, 0);
  const summary = aggregated
    ? `${filled.length} ${kind === 'bar' ? 'bars' : 'points'} · ${totalSamples} samples`
    : filled.length > 1
      ? `${filled.length} points`
      : 'current';

  return (
    <div className="flex flex-col gap-2 w-full">
      <div ref={containerRef} className="w-full">
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${kind} chart`}>
          {ticks.map((t, i) => (
            <g key={t}>
              <line x1={padLeft} x2={padLeft + plotW} y1={yOf(t)} y2={yOf(t)} stroke="#e5e7eb" strokeWidth={1} strokeDasharray={i === 0 ? undefined : '3 3'} />
              <text data-testid="chart-y-tick" x={padLeft - 4} y={yOf(t)} textAnchor="end" dominantBaseline="middle" fontSize={10} fill="#6b7280">
                {tickLabels[i]}
              </text>
            </g>
          ))}
          <line x1={padLeft} x2={padLeft} y1={padTop} y2={padTop + plotH} stroke="#d1d5db" strokeWidth={1} />
          {plot}
          {firstTime && (
            <>
              <text data-testid="chart-x-label" x={padLeft} y={height - 4} textAnchor="start" fontSize={10} fill="#6b7280">
                {formatChartTime(firstTime, spanMs)}
              </text>
              {lastTime && lastTime !== firstTime && (
                <text data-testid="chart-x-label" x={padLeft + plotW} y={height - 4} textAnchor="end" fontSize={10} fill="#6b7280">
                  {formatChartTime(lastTime, spanMs)}
                </text>
              )}
            </>
          )}
        </svg>
      </div>
      <div className="text-center">
        <div data-testid="chart-current-value" className="text-lg font-semibold" style={{ color: colorOf(value) }}>
          {fmt(value)}
        </div>
        <div className="text-xs text-gray-500">{summary}</div>
      </div>
    </div>
  );
}
