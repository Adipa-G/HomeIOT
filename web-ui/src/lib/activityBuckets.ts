import type { ActivityBucketGranularity } from '../types/api';

/** Returns the start of the UTC day containing `date`. */
export function startOfUtcDay(date: Date): Date {
  return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
}

/** Returns the start of the UTC hour containing `date`. */
export function startOfUtcHour(date: Date): Date {
  return new Date(Date.UTC(
    date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(), date.getUTCHours(),
  ));
}

export function addUtcDays(date: Date, days: number): Date {
  const result = new Date(date.getTime());
  result.setUTCDate(result.getUTCDate() + days);
  return result;
}

export function addUtcHours(date: Date, hours: number): Date {
  const result = new Date(date.getTime());
  result.setUTCHours(result.getUTCHours() + hours);
  return result;
}

function pad(n: number): string {
  return n.toString().padStart(2, '0');
}

/** Formats a Date as `yyyy-MM-ddTHH:mm:ssZ`, matching the backend's `EndpointValidation.ToUtcZ` format. */
export function toUtcZ(date: Date): string {
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}T${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}:${pad(date.getUTCSeconds())}Z`;
}

/** Formats a bucket's start timestamp for chart axis labels, per granularity. */
export function formatBucketLabel(isoString: string, granularity: ActivityBucketGranularity): string {
  const date = new Date(isoString);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  switch (granularity) {
    case 'day':
      return `${months[date.getUTCMonth()]} ${date.getUTCDate()}`;
    case 'hour':
      return `${pad(date.getUTCHours())}:00`;
    case 'five_minute':
      return `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`;
    default:
      return isoString;
  }
}
