using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class ModuleStatusRequest
{
    [JsonPropertyName("device_id")]
    public string? DeviceId { get; set; }

    [JsonPropertyName("module_id")]
    public string? ModuleId { get; set; }

    [JsonPropertyName("module_version")]
    public string? ModuleVersion { get; set; }

    [JsonPropertyName("disabled")]
    public bool Disabled { get; set; }

    [JsonPropertyName("disabled_reason")]
    public string? DisabledReason { get; set; }

    [JsonPropertyName("failed_start_count")]
    public int FailedStartCount { get; set; }

    [JsonPropertyName("disabled_at_utc")]
    public string? DisabledAtUtc { get; set; }
}
