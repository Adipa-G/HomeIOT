using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record CreateModuleResponse(
    [property: JsonPropertyName("module_id")] string ModuleId,
    [property: JsonPropertyName("description")] string? Description,
    [property: JsonPropertyName("default_entrypoint")] string DefaultEntrypoint,
    [property: JsonPropertyName("created_at_utc")] string CreatedAtUtc,
    [property: JsonPropertyName("version")] ModuleVersionItem? Version);
