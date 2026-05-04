using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class UpsertVariableDefRequest
{
    [JsonPropertyName("type")]
    public string? Type { get; set; }

    [JsonPropertyName("default_value")]
    public string? DefaultValue { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("server_code")]
    public string? ServerCode { get; set; }
}
