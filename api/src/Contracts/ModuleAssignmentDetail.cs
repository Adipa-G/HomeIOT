using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ModuleAssignmentDetail(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("device_id")] string DeviceId,
    [property: JsonPropertyName("module_id")] string ModuleId,
    [property: JsonPropertyName("version")] string Version,
    [property: JsonPropertyName("interval_ms")] int IntervalMs,
    [property: JsonPropertyName("timeout_ms")] int TimeoutMs,
    [property: JsonPropertyName("entrypoint")] string Entrypoint,
    [property: JsonPropertyName("enabled")] bool Enabled,
    [property: JsonPropertyName("created_at_utc")] string CreatedAtUtc,
    [property: JsonPropertyName("updated_at_utc")] string UpdatedAtUtc,
    [property: JsonPropertyName("show_in_dashboard")] bool ShowInDashboard = false);
