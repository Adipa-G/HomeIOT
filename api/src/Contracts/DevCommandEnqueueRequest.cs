using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record DevCommandEnqueueRequest(
    [property: JsonPropertyName("device_id")] string? DeviceId,
    [property: JsonPropertyName("code")] string? Code,
    [property: JsonPropertyName("timeout_ms")] int? TimeoutMs);
