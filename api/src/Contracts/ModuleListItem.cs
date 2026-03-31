using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ModuleListItem(
    [property: JsonPropertyName("module_id")] string ModuleId,
    [property: JsonPropertyName("description")] string? Description,
    [property: JsonPropertyName("default_entrypoint")] string DefaultEntrypoint,
    [property: JsonPropertyName("version_count")] int VersionCount,
    [property: JsonPropertyName("assignment_count")] int AssignmentCount,
    [property: JsonPropertyName("created_at_utc")] string CreatedAtUtc);
