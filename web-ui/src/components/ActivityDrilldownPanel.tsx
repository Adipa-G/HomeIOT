import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { HeartbeatActivityBucket, LogActivityBucket } from '../types/api';
import { ActivityBarChart } from './ActivityBarChart';
import { startOfUtcDay, startOfUtcHour, addUtcDays, addUtcHours, formatBucketLabel, toUtcZ } from '../lib/activityBuckets';
import { LOG_LEVEL_COLORS } from '../lib/logLevels';

interface ActivityDrilldownPanelProps {
  deviceId: string;
  kind: 'heartbeats' | 'logs';
  onFilterChange: (from: string, to: string) => void;
}

const DAY_WINDOW_DAYS = 30;

export function ActivityDrilldownPanel({ deviceId, kind, onFilterChange }: ActivityDrilldownPanelProps) {
  const now = new Date();
  const [selectedDay, setSelectedDay] = useState<Date>(startOfUtcDay(now));
  const [selectedHour, setSelectedHour] = useState<Date>(startOfUtcHour(now));
  const [selectedFiveMin, setSelectedFiveMin] = useState<Date | null>(null);
  // Separate from selectedDay/selectedHour above: those always default to today/current-hour
  // because they drive the hour/5-min query windows. These track whether the user has actually
  // clicked a bar, so the selection border stays hidden until then (and clears on reset/remount).
  const [selectedDayKey, setSelectedDayKey] = useState<string | null>(null);
  const [selectedHourKey, setSelectedHourKey] = useState<string | null>(null);

  const dayFrom = addUtcDays(startOfUtcDay(now), -(DAY_WINDOW_DAYS - 1));
  const dayTo = addUtcDays(startOfUtcDay(now), 1);
  const hourFrom = selectedDay;
  const hourTo = addUtcDays(selectedDay, 1);
  const fiveMinFrom = selectedHour;
  const fiveMinTo = addUtcHours(selectedHour, 1);

  const activityPath = kind === 'heartbeats' ? 'heartbeats/activity' : 'logs/activity';

  const dayQuery = useQuery({
    queryKey: ['activity', kind, deviceId, 'day', toUtcZ(dayFrom), toUtcZ(dayTo)],
    queryFn: () => api.get<(HeartbeatActivityBucket | LogActivityBucket)[]>(
      `/api/admin/devices/${deviceId}/${activityPath}?bucket=day&from=${toUtcZ(dayFrom)}&to=${toUtcZ(dayTo)}`,
    ),
  });

  const hourQuery = useQuery({
    queryKey: ['activity', kind, deviceId, 'hour', toUtcZ(hourFrom), toUtcZ(hourTo)],
    queryFn: () => api.get<(HeartbeatActivityBucket | LogActivityBucket)[]>(
      `/api/admin/devices/${deviceId}/${activityPath}?bucket=hour&from=${toUtcZ(hourFrom)}&to=${toUtcZ(hourTo)}`,
    ),
  });

  const fiveMinQuery = useQuery({
    queryKey: ['activity', kind, deviceId, 'five_minute', toUtcZ(fiveMinFrom), toUtcZ(fiveMinTo)],
    queryFn: () => api.get<(HeartbeatActivityBucket | LogActivityBucket)[]>(
      `/api/admin/devices/${deviceId}/${activityPath}?bucket=five_minute&from=${toUtcZ(fiveMinFrom)}&to=${toUtcZ(fiveMinTo)}`,
    ),
  });

  const getSegments = (bucket: HeartbeatActivityBucket | LogActivityBucket) => {
    if (kind === 'heartbeats') {
      const b = bucket as HeartbeatActivityBucket;
      return [{ value: b.count, color: '#3b82f6', label: 'heartbeats' }];
    }
    const b = bucket as LogActivityBucket;
    return [
      { value: b.info_count, color: LOG_LEVEL_COLORS.info, label: 'info' },
      { value: b.warn_count, color: LOG_LEVEL_COLORS.warn, label: 'warn' },
      { value: b.error_count, color: LOG_LEVEL_COLORS.error, label: 'error' },
      { value: b.debug_count, color: LOG_LEVEL_COLORS.debug, label: 'debug' },
      { value: b.other_count, color: LOG_LEVEL_COLORS.other, label: 'other' },
    ];
  };

  const legend = kind === 'logs'
    ? [
      { label: 'info', color: LOG_LEVEL_COLORS.info },
      { label: 'warn', color: LOG_LEVEL_COLORS.warn },
      { label: 'error', color: LOG_LEVEL_COLORS.error },
      { label: 'debug', color: LOG_LEVEL_COLORS.debug },
      { label: 'other', color: LOG_LEVEL_COLORS.other },
    ]
    : undefined;

  const handleDayClick = (bucket: HeartbeatActivityBucket | LogActivityBucket) => {
    setSelectedDay(startOfUtcDay(new Date(bucket.bucket_start_utc)));
    setSelectedDayKey(bucket.bucket_start_utc);
    onFilterChange(bucket.bucket_start_utc, bucket.bucket_end_utc);
  };

  const handleHourClick = (bucket: HeartbeatActivityBucket | LogActivityBucket) => {
    setSelectedHour(startOfUtcHour(new Date(bucket.bucket_start_utc)));
    setSelectedHourKey(bucket.bucket_start_utc);
    onFilterChange(bucket.bucket_start_utc, bucket.bucket_end_utc);
  };

  const handleFiveMinClick = (bucket: HeartbeatActivityBucket | LogActivityBucket) => {
    setSelectedFiveMin(new Date(bucket.bucket_start_utc));
    onFilterChange(bucket.bucket_start_utc, bucket.bucket_end_utc);
  };

  return (
    <div className="mb-4 grid gap-3 sm:grid-cols-3">
      <ActivityBarChart
        title="By day"
        buckets={dayQuery.data ?? []}
        getSegments={getSegments}
        getBucketKey={(b) => b.bucket_start_utc}
        formatLabel={(b) => formatBucketLabel(b.bucket_start_utc, 'day')}
        onBarClick={handleDayClick}
        selectedBucketKey={selectedDayKey}
        isLoading={dayQuery.isLoading}
        legend={legend}
      />
      <ActivityBarChart
        title="By hour"
        buckets={hourQuery.data ?? []}
        getSegments={getSegments}
        getBucketKey={(b) => b.bucket_start_utc}
        formatLabel={(b) => formatBucketLabel(b.bucket_start_utc, 'hour')}
        onBarClick={handleHourClick}
        selectedBucketKey={selectedHourKey}
        isLoading={hourQuery.isLoading}
        legend={legend}
      />
      <ActivityBarChart
        title="By 5 minutes"
        buckets={fiveMinQuery.data ?? []}
        getSegments={getSegments}
        getBucketKey={(b) => b.bucket_start_utc}
        formatLabel={(b) => formatBucketLabel(b.bucket_start_utc, 'five_minute')}
        onBarClick={handleFiveMinClick}
        selectedBucketKey={selectedFiveMin ? toUtcZ(selectedFiveMin) : null}
        isLoading={fiveMinQuery.isLoading}
        legend={legend}
      />
    </div>
  );
}
