using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class HeartbeatRequest
{
    [JsonPropertyName("device_id")]
    public string? DeviceId { get; set; }

    [JsonPropertyName("timestamp")]
    public long? Timestamp { get; set; }

    [JsonPropertyName("uptime_ms")]
    public long? UptimeMs { get; set; }

    [JsonPropertyName("free_memory_bytes")]
    public long? FreeMemoryBytes { get; set; }
}