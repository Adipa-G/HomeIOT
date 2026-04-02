using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record DashboardResponse(
    [property: JsonPropertyName("total_devices")] int TotalDevices,
    [property: JsonPropertyName("devices_online_24h")] int DevicesOnline24h,
    [property: JsonPropertyName("total_modules")] int TotalModules,
    [property: JsonPropertyName("total_assignments")] int TotalAssignments,
    [property: JsonPropertyName("total_users")] int TotalUsers,
    [property: JsonPropertyName("heartbeats_24h")] int Heartbeats24h,
    [property: JsonPropertyName("log_batches_24h")] int LogBatches24h,
    [property: JsonPropertyName("module_runs_24h")] int ModuleRuns24h,
    [property: JsonPropertyName("module_failures_24h")] int ModuleFailures24h);
