using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class ModulePrefetchRequest
{
    [JsonPropertyName("modules")]
    public List<ModulePrefetchItem>? Modules { get; set; }
}

public sealed class ModulePrefetchItem
{
    [JsonPropertyName("module_id")]
    public string? ModuleId { get; set; }

    [JsonPropertyName("version")]
    public string? Version { get; set; }
}
