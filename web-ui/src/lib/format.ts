import { format, parseISO } from 'date-fns';

export function formatUtc(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  try {
    return format(parseISO(isoString), 'yyyy-MM-dd HH:mm:ss');
  } catch {
    return isoString;
  }
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

export function formatMs(ms: number | null | undefined): string {
  if (ms == null) return '—';
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}
