export const LOG_LEVEL_COLORS = {
  info: '#3b82f6',
  warn: '#f59e0b',
  error: '#ef4444',
  debug: '#9ca3af',
  other: '#8b5cf6',
} as const;

export type LogLevelKey = keyof typeof LOG_LEVEL_COLORS;
