import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { api } from '../api/client';
import type { DashboardModuleItem, DashboardResponse } from '../types/api';
import { MetricCard } from '../components/MetricCard';
import { ModuleVariableVisualizer, extractJsonValue } from '../components/ModuleVariableVisualizer';

type DashboardTile =
  | { kind: 'viz'; key: string; moduleId: string; visualizationType: string; config: unknown; value: string | number; displayName: string }
  | { kind: 'status'; key: string; moduleId: string; text: string }
  | { kind: 'error'; key: string; moduleId: string; text: string };

function buildTiles(items: DashboardModuleItem[]): DashboardTile[] {
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
        tiles.push({
          kind: 'viz',
          key: `${item.assignment_id}-viz-${idx}`,
          moduleId: item.module_id,
          visualizationType: viz.visualization_type || 'number_display',
          config: viz.visualization_config,
          value,
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

export default function DashboardPage() {
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get<DashboardResponse>('/api/admin/dashboard'),
    refetchInterval: 30000,
  });

  const { data: dashboardModules } = useQuery({
    queryKey: ['dashboard-modules'],
    queryFn: () => api.get<DashboardModuleItem[]>('/api/admin/dashboard/modules'),
    refetchInterval: 30000,
  });

  if (isLoading || !data) {
    return <p className="text-sm text-gray-500">Loading dashboard…</p>;
  }

  const modulesByDevice = new Map<string, DashboardModuleItem[]>();
  for (const item of dashboardModules ?? []) {
    const existing = modulesByDevice.get(item.device_id);
    if (existing) {
      existing.push(item);
    } else {
      modulesByDevice.set(item.device_id, [item]);
    }
  }

  return (
    <div>
      <h2 className="mb-6 text-xl font-semibold text-gray-900">Dashboard</h2>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-4">
        <MetricCard label="Total Devices" value={data.total_devices} />
        <MetricCard label="Online (24h)" value={data.devices_online_24h} />
        <MetricCard label="Modules" value={data.total_modules} />
        <MetricCard label="Assignments" value={data.total_assignments} />
        <MetricCard label="Users" value={data.total_users} />
        <MetricCard label="Heartbeats (24h)" value={data.heartbeats_24h} />
        <MetricCard label="Log Batches (24h)" value={data.log_batches_24h} />
        <MetricCard label="Module Runs (24h)" value={data.module_runs_24h} />
        <MetricCard label="Module Failures (24h)" value={data.module_failures_24h} sub={data.module_runs_24h > 0 ? `${((data.module_failures_24h / data.module_runs_24h) * 100).toFixed(1)}% failure rate` : undefined} />
      </div>

      {modulesByDevice.size > 0 && (
        <div className="mt-8">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Modules</h3>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-4">
            {Array.from(modulesByDevice.entries()).map(([deviceId, items]) => {
              const tiles = buildTiles(items);
              return (
                <div key={deviceId} className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
                  <h4
                    className="mb-2 cursor-pointer text-sm font-medium text-blue-600 hover:underline"
                    onClick={() => navigate(`/devices/${deviceId}`)}
                  >
                    {deviceId}
                  </h4>
                  <div className="grid grid-cols-2 gap-2 lg:grid-cols-3">
                    {tiles.map((tile) => (
                      <div
                        key={tile.key}
                        className="cursor-pointer rounded border border-gray-100 p-2 hover:border-gray-300"
                        onClick={() => navigate(`/devices/${deviceId}`)}
                      >
                        <div className="mb-1 truncate text-[10px] text-gray-400">{tile.moduleId}</div>
                        {tile.kind === 'viz' && (
                          <ModuleVariableVisualizer
                            type={tile.visualizationType}
                            config={tile.config}
                            value={tile.value}
                            displayName={tile.displayName}
                          />
                        )}
                        {tile.kind === 'status' && <div className="text-xs text-gray-500">{tile.text}</div>}
                        {tile.kind === 'error' && <div className="truncate text-xs text-red-500">{tile.text}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

