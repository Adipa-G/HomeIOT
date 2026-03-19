using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

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