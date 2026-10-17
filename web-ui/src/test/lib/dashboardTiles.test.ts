import { describe, it, expect } from 'vitest';
import { buildTiles, isChartTile, type DashboardTile } from '../../lib/dashboardTiles';
import type { DashboardModuleItem } from '../../types/api';

const item = (overrides: Partial<DashboardModuleItem> = {}): DashboardModuleItem => ({
  assignment_id: 'a1',
  device_id: 'dev-1',
  module_id: 'mod-1',
  status: 'ok',
  output: '{"temp":21,"hum":40}',
  error_message: null,
  finished_at_utc: '2026-05-10T00:10:00Z',
  variable_defs: [
    {
      name: 'r',
      type: 'json',
      default_value: null,
      description: null,
      has_server_code: false,
      visualizations: [
        { id: 'v1', json_path: 'temp', display_name: 'Temp', visualization_type: 'line_chart' },
        { id: 'v2', json_path: 'hum', display_name: 'Humidity', visualization_type: null },
      ],
    },
  ],
  ...overrides,
} as DashboardModuleItem);

describe('buildTiles', () => {
  it('creates one viz tile per visualization, defaulting the type to number_display', () => {
    const tiles = buildTiles([item()]);
    expect(tiles.map((t) => t.kind)).toEqual(['viz', 'viz']);
    const [temp, hum] = tiles as Extract<DashboardTile, { kind: 'viz' }>[];
    expect(temp).toMatchObject({ value: 21, visualizationType: 'line_chart', displayName: 'Temp' });
    expect(hum.visualizationType).toBe('number_display');
  });

  it('attaches the chart series matching each visualization id', () => {
    const points = [{ start_utc: 't1', end_utc: 't2', avg: 19.5, min: 19, max: 20, count: 2 }];
    const tiles = buildTiles([
      item({
        chart_series: [
          { visualization_id: 'other', points: [] },
          { visualization_id: 'v1', points },
        ],
      }),
    ]);
    const [temp, hum] = tiles as Extract<DashboardTile, { kind: 'viz' }>[];
    expect(temp.series).toBe(points);
    expect(hum.series).toBeUndefined();
  });

  it('leaves the series undefined when the API sent none', () => {
    const temp = buildTiles([item()])[0] as Extract<DashboardTile, { kind: 'viz' }>;
    expect(temp.series).toBeUndefined();
  });

  it('skips visualizations whose value is missing from the output', () => {
    const tiles = buildTiles([item({ output: '{"temp":21}' })]);
    expect(tiles).toHaveLength(1);
  });

  it('falls back to a status tile when output is missing or invalid', () => {
    expect(buildTiles([item({ output: null })])[0]).toMatchObject({ kind: 'status', text: 'Status: ok' });
    expect(buildTiles([item({ output: 'oops', status: null })])[0]).toMatchObject({ kind: 'status', text: 'No data yet' });
  });

  it('adds an error tile when the run reported an error', () => {
    const tiles = buildTiles([item({ error_message: 'boom' })]);
    expect(tiles[tiles.length - 1]).toMatchObject({ kind: 'error', text: 'boom' });
  });
});

describe('isChartTile', () => {
  it('is true only for bar/line chart viz tiles', () => {
    const [chart, number] = buildTiles([item()]);
    expect(isChartTile(chart)).toBe(true);
    expect(isChartTile(number)).toBe(false);
    expect(isChartTile({ kind: 'status', key: 'k', moduleId: 'm', text: 't' })).toBe(false);
  });
});
