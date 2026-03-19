using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record PingResponse(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("service")] string Service,
    [property: JsonPropertyName("server_time_utc")] string ServerTimeUtc);
