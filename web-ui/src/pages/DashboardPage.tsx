import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { DashboardResponse } from '../types/api';
import { MetricCard } from '../components/MetricCard';

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get<DashboardResponse>('/api/admin/dashboard'),
    refetchInterval: 30000,
  });

  if (isLoading || !data) {
    return <p className="text-sm text-gray-500">Loading dashboard…</p>;
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
    </div>
  );
}
