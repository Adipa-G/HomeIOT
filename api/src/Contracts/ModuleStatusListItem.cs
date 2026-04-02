using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ModuleStatusListItem(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("device_id")] string DeviceId,
    [property: JsonPropertyName("module_id")] string ModuleId,
    [property: JsonPropertyName("module_version")] string ModuleVersion,
    [property: JsonPropertyName("disabled")] bool Disabled,
    [property: JsonPropertyName("disabled_reason")] string? DisabledReason,
    [property: JsonPropertyName("failed_start_count")] int FailedStartCount,
    [property: JsonPropertyName("disabled_at_utc")] string? DisabledAtUtc,
    [property: JsonPropertyName("received_at_utc")] string ReceivedAtUtc);
