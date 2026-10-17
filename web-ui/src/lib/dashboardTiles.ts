import type { ChartSeriesPoint, DashboardModuleItem } from '../types/api';
import { extractJsonValue, isChartVisualization } from './visualization';

export type DashboardTile =
  | {
      kind: 'viz';
      key: string;
      moduleId: string;
      visualizationType: string;
      config: unknown;
      value: string | number;
      series?: ChartSeriesPoint[];
      displayName: string;
    }
  | { kind: 'status'; key: string; moduleId: string; text: string }
  | { kind: 'error'; key: string; moduleId: string; text: string };

export function isChartTile(tile: DashboardTile): boolean {
  return tile.kind === 'viz' && isChartVisualization(tile.visualizationType);
}

/**
 * Flattens dashboard module items into display tiles: one per visualization with a value
 * (plus its chart series), a status tile when nothing can be visualised, and an error tile.
 */
export function buildTiles(items: DashboardModuleItem[]): DashboardTile[] {
  const tiles: DashboardTile[] = [];

  for (const item of items) {
    const visualizations = item.variable_defs.flatMap((v) => v.visualizations ?? []);

    let outputData: unknown;
    let parseFailed = false;
    if (item.output) {
      try {
        outputData = JSON.parse(item.output);
      } catch {
        parseFailed = true;
      }
    }

    if (visualizations.length === 0 || !item.output || parseFailed) {
      tiles.push({
        kind: 'status',
        key: `${item.assignment_id}-status`,
        moduleId: item.module_id,
        text: item.status ? `Status: ${item.status}` : 'No data yet',
      });
    } else {
      for (const [idx, viz] of visualizations.entries()) {
        const value = extractJsonValue(outputData, viz.json_path);
        if (value === null) continue;
        const series = item.chart_series?.find((c) => c.visualization_id === viz.id)?.points;
        tiles.push({
          kind: 'viz',
          key: `${item.assignment_id}-viz-${idx}`,
          moduleId: item.module_id,
          visualizationType: viz.visualization_type || 'number_display',
          config: viz.visualization_config,
          value,
          series,
          displayName: viz.display_name,
        });
      }
    }

    if (item.error_message) {
      tiles.push({
        kind: 'error',
        key: `${item.assignment_id}-error`,
        moduleId: item.module_id,
        text: item.error_message,
      });
    }
  }

  return tiles;
}
