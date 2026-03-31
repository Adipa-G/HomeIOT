using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class CreateModuleRequest
{
    [JsonPropertyName("module_id")]
    public string? ModuleId { get; set; }

    [JsonPropertyName("description")]
    public string? Description { get; set; }

    [JsonPropertyName("default_entrypoint")]
    public string? DefaultEntrypoint { get; set; }

    [JsonPropertyName("version")]
    public string? Version { get; set; }

    [JsonPropertyName("code")]
    public string? Code { get; set; }
}
