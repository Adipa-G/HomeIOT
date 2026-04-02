using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record LogBatchListItem(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("reason")] string Reason,
    [property: JsonPropertyName("received_count")] int ReceivedCount,
    [property: JsonPropertyName("dropped_count")] int DroppedCount,
    [property: JsonPropertyName("truncated")] bool Truncated,
    [property: JsonPropertyName("logs_json")] string LogsJson,
    [property: JsonPropertyName("received_at_utc")] string ReceivedAtUtc);
