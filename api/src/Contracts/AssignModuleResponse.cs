using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record AssignModuleResponse(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("module_id")] string ModuleId,
    [property: JsonPropertyName("device_id")] string DeviceId,
    [property: JsonPropertyName("version")] string Version,
    [property: JsonPropertyName("interval_ms")] int IntervalMs,
    [property: JsonPropertyName("timeout_ms")] int TimeoutMs,
    [property: JsonPropertyName("entrypoint")] string Entrypoint,
    [property: JsonPropertyName("enabled")] bool Enabled);
