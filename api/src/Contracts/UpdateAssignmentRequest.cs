using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class UpdateAssignmentRequest
{
    [JsonPropertyName("version")]
    public string? Version { get; set; }

    [JsonPropertyName("interval_ms")]
    public int? IntervalMs { get; set; }

    [JsonPropertyName("timeout_ms")]
    public int? TimeoutMs { get; set; }

    [JsonPropertyName("entrypoint")]
    public string? Entrypoint { get; set; }

    [JsonPropertyName("enabled")]
    public bool? Enabled { get; set; }

    [JsonPropertyName("show_in_dashboard")]
    public bool? ShowInDashboard { get; set; }
}
