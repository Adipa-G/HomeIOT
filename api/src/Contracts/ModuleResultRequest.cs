using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class ModuleResultRequest
{
    [JsonPropertyName("device_id")]
    public string? DeviceId { get; set; }

    [JsonPropertyName("module_id")]
    public string? ModuleId { get; set; }

    [JsonPropertyName("module_version")]
    public string? ModuleVersion { get; set; }

    [JsonPropertyName("run_id")]
    public string? RunId { get; set; }

    [JsonPropertyName("started_at_utc")]
    public string? StartedAtUtc { get; set; }

    [JsonPropertyName("finished_at_utc")]
    public string? FinishedAtUtc { get; set; }

    [JsonPropertyName("elapsed_ms")]
    public int ElapsedMs { get; set; }

    [JsonPropertyName("status")]
    public string? Status { get; set; }

    [JsonPropertyName("output")]
    public object? Output { get; set; }

    [JsonPropertyName("variable_values")]
    public object? VariableValues { get; set; }

    [JsonPropertyName("error_message")]
    public string? ErrorMessage { get; set; }
}
