using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ModuleAssignmentItem(
    [property: JsonPropertyName("module_id")] string ModuleId,
    [property: JsonPropertyName("version")] string Version,
    [property: JsonPropertyName("interval_ms")] int IntervalMs,
    [property: JsonPropertyName("timeout_ms")] int TimeoutMs,
    [property: JsonPropertyName("entrypoint")] string Entrypoint,
    [property: JsonPropertyName("package_hash")] string PackageHash,
    [property: JsonPropertyName("enabled")] bool Enabled,
    [property: JsonPropertyName("variables")] Dictionary<string, string?>? Variables = null);
