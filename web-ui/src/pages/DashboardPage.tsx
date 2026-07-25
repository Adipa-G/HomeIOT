import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router';
import { api } from '../api/client';
import type { DashboardModuleItem, DashboardResponse } from '../types/api';
import { MetricCard } from '../components/MetricCard';
import { ModuleVariableVisualizer, extractJsonValue } from '../components/ModuleVariableVisualizer';

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
          <div className="space-y-6">
            {Array.from(modulesByDevice.entries()).map(([deviceId, items]) => (
              <div key={deviceId}>
                <h4
                  className="mb-2 cursor-pointer text-sm font-medium text-blue-600 hover:underline"
                  onClick={() => navigate(`/devices/${deviceId}`)}
                >
                  {deviceId}
                </h4>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {items.map((item) => (
                    <div
                      key={item.assignment_id}
                      className="cursor-pointer rounded-lg border border-gray-200 bg-white p-3 shadow-sm hover:shadow-md"
                      onClick={() => navigate(`/devices/${deviceId}`)}
                    >
                      <div className="mb-2 text-xs font-medium text-gray-700">{item.module_id}</div>
                      {(() => {
                        const visualizations = item.variable_defs.flatMap((v) => v.visualizations ?? []);
                        if (visualizations.length === 0 || !item.output) {
                          return (
                            <div className="text-xs text-gray-500">
                              {item.status ? `Status: ${item.status}` : 'No data yet'}
                            </div>
                          );
                        }
                        let outputData: unknown;
                        try {
                          outputData = JSON.parse(item.output);
                        } catch {
                          return <div className="text-xs text-gray-500">Status: {item.status ?? '—'}</div>;
                        }
                        return (
                          <div className="space-y-2">
                            {visualizations.map((viz, idx) => {
                              const value = extractJsonValue(outputData, viz.json_path);
                              if (value === null) return null;
                              return (
                                <ModuleVariableVisualizer
                                  key={`${item.assignment_id}-${idx}`}
                                  type={viz.visualization_type || 'number_display'}
                                  config={viz.visualization_config}
                                  value={value}
                                  displayName={viz.display_name}
                                />
                              );
                            })}
                          </div>
                        );
                      })()}
                      {item.error_message && (
                        <div className="mt-2 truncate text-xs text-red-500">{item.error_message}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

