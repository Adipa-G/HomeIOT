import type { VisualizationConfig } from './visualization';

function niceStep(rough: number): number {
  const exp = Math.floor(Math.log10(rough));
  const base = Math.pow(10, exp);
  const f = rough / base;
  const nice = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10;
  return nice * base;
}

const roundFloat = (n: number) => Number(n.toPrecision(12));

/**
 * Y-axis domain and tick values. Uses config min/max when both are set, otherwise
 * auto-scales to the data (bar charts always include zero so bar heights stay honest).
 */
export function computeYScale(
  data: number[],
  config: VisualizationConfig | undefined,
  includeZero: boolean,
): { lo: number; hi: number; ticks: number[] } {
  const cfgMin = typeof config?.min === 'number' ? config.min : undefined;
  const cfgMax = typeof config?.max === 'number' ? config.max : undefined;

  if (cfgMin !== undefined && cfgMax !== undefined && cfgMax > cfgMin) {
    const ticks = Array.from({ length: 5 }, (_, i) => roundFloat(cfgMin + (i * (cfgMax - cfgMin)) / 4));
    return { lo: cfgMin, hi: cfgMax, ticks };
  }

  let lo = cfgMin ?? Math.min(...data);
  let hi = cfgMax ?? Math.max(...data);
  if (includeZero) {
    if (cfgMin === undefined) lo = Math.min(lo, 0);
    if (cfgMax === undefined) hi = Math.max(hi, 0);
  }
  if (hi <= lo) {
    const pad = Math.abs(lo) * 0.1 || 1;
    if (cfgMin === undefined) lo -= pad;
    if (cfgMax === undefined || hi <= lo) hi = lo + 2 * pad;
  } else {
    const pad = (hi - lo) * 0.05;
    if (cfgMin === undefined && !(includeZero && lo === 0)) lo -= pad;
    if (cfgMax === undefined && !(includeZero && hi === 0)) hi += pad;
  }

  const step = niceStep((hi - lo) / 4);
  const niceLo = cfgMin ?? roundFloat(Math.floor(lo / step) * step);
  const niceHi = cfgMax ?? roundFloat(Math.ceil(hi / step) * step);
  const ticks: number[] = [];
  for (let t = Math.ceil(niceLo / step) * step; t <= niceHi + step * 1e-9; t += step) {
    ticks.push(roundFloat(t));
  }
  if (ticks.length === 0 || ticks[0] > niceLo) ticks.unshift(niceLo);
  if (ticks[ticks.length - 1] < niceHi) ticks.push(niceHi);
  return { lo: niceLo, hi: niceHi, ticks };
}

/**
 * Smallest number of decimals (max 2) needed to print `n` without losing precision.
 */
export function decimalsFor(n: number): number {
  let d = 0;
  while (d < 2 && Math.abs(Math.round(n * 10 ** d) - n * 10 ** d) > 1e-9) d++;
  return d;
}

/**
 * Short axis label for a timestamp; includes the date when the series spans more than a day.
 */
export function formatChartTime(iso: string, spanMs: number): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return spanMs > 24 * 60 * 60 * 1000
    ? d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
