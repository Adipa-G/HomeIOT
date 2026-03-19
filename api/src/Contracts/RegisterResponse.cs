using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record RegisterResponse(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("device_id")] string DeviceId);