using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record HeartbeatResponse(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("server_time_utc")] string ServerTimeUtc,
    [property: JsonPropertyName("mode")] string Mode,
    [property: JsonPropertyName("dev_poll_interval_ms")] int DevPollIntervalMs,
    [property: JsonPropertyName("module_assignment_poll_interval_ms")] int ModuleAssignmentPollIntervalMs,
    [property: JsonPropertyName("next_heartbeat_ms")] int NextHeartbeatMs);
