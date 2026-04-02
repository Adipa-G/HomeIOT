using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record DeviceDetailResponse(
    [property: JsonPropertyName("device_id")] string DeviceId,
    [property: JsonPropertyName("platform")] string? Platform,
    [property: JsonPropertyName("version")] string? Version,
    [property: JsonPropertyName("ip")] string? Ip,
    [property: JsonPropertyName("mode")] string Mode,
    [property: JsonPropertyName("last_heartbeat_at_utc")] string? LastHeartbeatAtUtc,
    [property: JsonPropertyName("created_at_utc")] string CreatedAtUtc,
    [property: JsonPropertyName("updated_at_utc")] string UpdatedAtUtc,
    [property: JsonPropertyName("latest_heartbeat")] HeartbeatListItem? LatestHeartbeat);
