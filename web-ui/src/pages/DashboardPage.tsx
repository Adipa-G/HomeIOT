import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { api } from '../api/client';
import type { DashboardModuleItem, DashboardResponse } from '../types/api';
import { MetricCard } from '../components/MetricCard';
import { ModuleVariableVisualizer } from '../components/ModuleVariableVisualizer';
import { buildTiles, isChartTile } from '../lib/dashboardTiles';

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
              // Only use a 3-column tile grid at lg+ once there are enough tiles to
              // fill it; otherwise stick to 2 columns so a lone/pair of tiles get
              // a sensible half-width size instead of shrinking to a third.
              const tileGridClass = tiles.length >= 3 ? 'grid grid-cols-2 gap-2 lg:grid-cols-3' : 'grid grid-cols-2 gap-2';
              // Charts need horizontal room to be legible: give them a full row in the
              // tile grid and let their device card span two dashboard columns.
              const hasChart = tiles.some(isChartTile);
              return (
                <div
                  key={deviceId}
                  className={`rounded-lg border border-gray-200 bg-white p-3 shadow-sm${hasChart ? ' col-span-2' : ''}`}
                >
                  <h4
                    className="mb-2 cursor-pointer text-sm font-medium text-blue-600 hover:underline"
                    onClick={() => navigate(`/devices/${deviceId}`)}
                  >
                    {deviceId}
                  </h4>
                  <div className={tileGridClass}>
                    {tiles.map((tile) => (
                      <div
                        key={tile.key}
                        className={`cursor-pointer rounded border border-gray-100 p-2 hover:border-gray-300${isChartTile(tile) ? ' col-span-full' : ''}`}
                        onClick={() => navigate(`/devices/${deviceId}`)}
                      >
                        <div className="mb-1 truncate text-[10px] text-gray-400">{tile.moduleId}</div>
                        {tile.kind === 'viz' && (
                          <ModuleVariableVisualizer
                            type={tile.visualizationType}
                            config={tile.config}
                            value={tile.value}
                            series={tile.series}
                            displayName={tile.displayName}
                            compact
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

