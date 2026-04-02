using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class UpdateModuleRequest
{
    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("default_entrypoint")]
    public string? DefaultEntrypoint { get; set; }
}
