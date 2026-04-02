using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record HeartbeatListItem(
    [property: JsonPropertyName("uptime_ms")] long? UptimeMs,
    [property: JsonPropertyName("free_memory_bytes")] long? FreeMemoryBytes,
    [property: JsonPropertyName("received_at_utc")] string ReceivedAtUtc);
