using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

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
