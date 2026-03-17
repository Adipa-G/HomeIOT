using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ErrorResponse(
    [property: JsonPropertyName("error")] string Error,
    [property: JsonPropertyName("message")] string? Message = null);

public sealed class RegisterRequest
{
    [JsonPropertyName("device_id")]
    public string? DeviceId { get; set; }

    [JsonPropertyName("platform")]
    public string? Platform { get; set; }

    [JsonPropertyName("version")]
    public string? Version { get; set; }

    [JsonPropertyName("ip")]
    public string? Ip { get; set; }

    [JsonPropertyName("timestamp")]
    public long? Timestamp { get; set; }
}

public sealed record RegisterResponse(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("device_id")] string DeviceId);

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

public sealed record HeartbeatResponse(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("server_time_utc")] string ServerTimeUtc,
    [property: JsonPropertyName("mode")] string Mode,
    [property: JsonPropertyName("dev_poll_interval_ms")] int DevPollIntervalMs,
    [property: JsonPropertyName("module_assignment_poll_interval_ms")] int ModuleAssignmentPollIntervalMs,
    [property: JsonPropertyName("next_heartbeat_ms")] int NextHeartbeatMs);

public sealed class LogEntryRequest
{
    [JsonPropertyName("ts")]
    public long? Ts { get; set; }

    [JsonPropertyName("level")]
    public string? Level { get; set; }

    [JsonPropertyName("message")]
    public string? Message { get; set; }

    [JsonPropertyName("context")]
    public Dictionary<string, object?> Context { get; set; } = new();
}

public sealed class LogBatchRequest
{
    [JsonPropertyName("device_id")]
    public string? DeviceId { get; set; }

    [JsonPropertyName("reason")]
    public string? Reason { get; set; }

    [JsonPropertyName("sentAt")]
    public long? SentAt { get; set; }

    [JsonPropertyName("dropped_count")]
    public int? DroppedCount { get; set; }

    [JsonPropertyName("truncated")]
    public bool? Truncated { get; set; }

    [JsonPropertyName("logs")]
    public List<LogEntryRequest> Logs { get; set; } = new();
}

public sealed record StatusResponse(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("received")] int? Received = null);
