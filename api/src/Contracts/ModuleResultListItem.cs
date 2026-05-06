using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ModuleResultListItem(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("device_id")] string DeviceId,
    [property: JsonPropertyName("module_id")] string ModuleId,
    [property: JsonPropertyName("module_version")] string ModuleVersion,
    [property: JsonPropertyName("run_id")] string RunId,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("elapsed_ms")] int ElapsedMs,
    [property: JsonPropertyName("error_message")] string? ErrorMessage,
    [property: JsonPropertyName("output")] string? Output,
    [property: JsonPropertyName("variable_values")] string? VariableValues,
    [property: JsonPropertyName("started_at_utc")] string StartedAtUtc,
    [property: JsonPropertyName("finished_at_utc")] string FinishedAtUtc);
