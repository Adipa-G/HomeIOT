// ── Auth ──
export interface AdminLoginRequest {
  username: string;
  password: string;
}

export interface AdminLoginResponse {
  token: string;
  expires_at: string;
}

// ── Pagination ──
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
}

// ── Dashboard ──
export interface DashboardResponse {
  total_devices: number;
  devices_online_24h: number;
  total_modules: number;
  total_assignments: number;
  total_users: number;
  heartbeats_24h: number;
  log_batches_24h: number;
  module_runs_24h: number;
  module_failures_24h: number;
}

// ── Devices ──
export interface DeviceListItem {
  device_id: string;
  platform: string | null;
  version: string | null;
  ip: string | null;
  mode: string;
  last_heartbeat_at_utc: string | null;
  created_at_utc: string;
}

export interface DeviceDetailResponse extends DeviceListItem {
  updated_at_utc: string;
  latest_heartbeat: HeartbeatListItem | null;
}

export interface HeartbeatListItem {
  uptime_ms: number | null;
  free_memory_bytes: number | null;
  received_at_utc: string;
}

export interface LogEntry {
  ts: number | null;
  level: string | null;
  message: string | null;
  context: Record<string, unknown>;
}

export interface LogBatchListItem {
  id: string;
  reason: string;
  received_count: number;
  dropped_count: number;
  truncated: boolean;
  logs_json: string;
  received_at_utc: string;
}

export interface UpdateDeviceModeRequest {
  mode: string;
}

// ── Activity ──
export type ActivityBucketGranularity = 'day' | 'hour' | 'five_minute';

export interface HeartbeatActivityBucket {
  bucket_start_utc: string;
  bucket_end_utc: string;
  count: number;
}

export interface LogActivityBucket {
  bucket_start_utc: string;
  bucket_end_utc: string;
  info_count: number;
  warn_count: number;
  error_count: number;
  debug_count: number;
  other_count: number;
}

// ── Modules ──
export interface ModuleListItem {
  module_id: string;
  description: string | null;
  default_entrypoint: string;
  version_count: number;
  assignment_count: number;
  created_at_utc: string;
}

export interface ModuleDetailResponse {
  module_id: string;
  description: string | null;
  default_entrypoint: string;
  created_at_utc: string;
  updated_at_utc: string;
  versions: ModuleVersionItem[];
  assignments: ModuleAssignmentDetail[];
  variable_defs: ModuleVariableDefItem[];
}

export interface ModuleVariableDefItem {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'json' | string;
  default_value: string | null;
  description: string | null;
  has_server_code: boolean;
  server_code?: string | null;
  control_type?: 'text' | 'dropdown' | 'toggle' | string | null;
  control_options?: unknown | null;
  inferred_json_schema?: unknown | null;
  visualizations?: ModuleVariableVisualizationItem[] | null;
}

export interface ModuleVariableVisualizationItem {
  id: string;
  json_path: string;
  display_name: string;
  visualization_type?: 'line_chart' | 'gauge' | 'progress_bar' | 'number_display' | 'bar_chart' | 'text_display' | string | null;
  visualization_config?: unknown | null;
}

export interface UpsertVariableDefRequest {
  type?: string;
  default_value?: string | null;
  description?: string | null;
  server_code?: string | null;
  control_type?: string | null;
  control_options?: unknown | null;
}

export interface UpsertModuleVariableVisualizationRequest {
  json_path: string;
  display_name: string;
  visualization_type?: string | null;
  visualization_config?: unknown | null;
}


export interface ModuleVersionItem {
  id: string;
  version: string;
  package_hash: string;
  package_size_bytes: number;
  created_at_utc: string;
}

export interface ModuleAssignmentDetail {
  id: string;
  device_id: string;
  module_id: string;
  version: string;
  interval_ms: number;
  timeout_ms: number;
  entrypoint: string;
  enabled: boolean;
  created_at_utc: string;
  updated_at_utc: string;
  show_in_dashboard: boolean;
}

export interface ModuleVariableValueItem {
  variable_name: string;
  value: string | null;
  source: 'override' | 'server_computed' | 'default' | string;
  last_computed_at_utc?: string | null;
}

export interface SetVariableValueRequest {
  value?: string | null;
}

export interface CreateModuleRequest {
  module_id: string;
  description?: string;
  default_entrypoint?: string;
  version?: string;
  code?: string;
}

export interface UpdateModuleRequest {
  description?: string;
  default_entrypoint?: string;
}

export interface AssignModuleRequest {
  device_id: string;
  version: string;
  interval_ms?: number;
  timeout_ms?: number;
  entrypoint?: string;
}

export interface UpdateAssignmentRequest {
  version?: string;
  interval_ms?: number;
  timeout_ms?: number;
  entrypoint?: string;
  enabled?: boolean;
  show_in_dashboard?: boolean;
}

export interface DashboardModuleItem {
  assignment_id: string;
  device_id: string;
  module_id: string;
  status: string | null;
  output: string | null;
  error_message: string | null;
  finished_at_utc: string | null;
  variable_defs: ModuleVariableDefItem[];
}

export interface UploadVersionRequest {
  version: string;
  code: string;
}

export interface ModuleResultListItem {
  id: string;
  device_id: string;
  module_id: string;
  module_version: string;
  run_id: string;
  status: string;
  elapsed_ms: number;
  error_message: string | null;
  output: string | null;
  variable_values: string | null;
  started_at_utc: string;
  finished_at_utc: string;
}

export interface ModuleStatusListItem {
  id: string;
  device_id: string;
  module_id: string;
  module_version: string;
  disabled: boolean;
  disabled_reason: string | null;
  failed_start_count: number;
  disabled_at_utc: string | null;
  received_at_utc: string;
}

// ── OTA ──
export interface OtaPlatformListItem {
  platform: string;
  release_count: number;
}

export interface OtaReleaseListItem {
  version: string;
  file_count: number;
  total_size_bytes: number;
}

export interface OtaReleaseDetailResponse {
  platform: string;
  version: string;
  file_count: number;
  total_size_bytes: number;
  manifest: OtaManifestFileItem[];
}

export interface OtaManifestFileItem {
  path: string;
  hash: string;
  size_bytes: number;
}

// ── Users ──
export interface UserListItem {
  id: number;
  username: string;
  created_at_utc: string;
}

export interface CreateUserRequest {
  username: string;
  password: string;
}

export interface ChangePasswordRequest {
  new_password: string;
}

// ── Dev Commands ──
export interface DevCommandEnqueueRequest {
  device_id: string;
  code: string;
  timeout_ms?: number;
}

export interface DevCommandEnqueueResponse {
  command_id: string;
  device_id: string;
  queued_at: string;
}

export interface DevCommandPendingItem {
  command_id: string;
  device_id: string;
  code: string;
  timeout_ms: number | null;
  queued_at_utc: string;
}

export interface DevCommandResultItem {
  command_id: string;
  code: string | null;
  status: string;
  exit_code: number;
  elapsed_ms: number;
  started_at_utc: string | null;
  finished_at_utc: string | null;
  stdout: string | null;
  stderr: string | null;
  data: unknown;
  received_at: string;
}

// ── Error ──
export interface ErrorResponse {
  code: string;
  message: string;
}
