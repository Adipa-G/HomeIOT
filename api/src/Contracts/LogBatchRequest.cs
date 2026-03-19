using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

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
