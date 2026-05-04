using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ModuleDetailResponse(
    [property: JsonPropertyName("module_id")] string ModuleId,
    [property: JsonPropertyName("description")] string? Description,
    [property: JsonPropertyName("default_entrypoint")] string DefaultEntrypoint,
    [property: JsonPropertyName("created_at_utc")] string CreatedAtUtc,
    [property: JsonPropertyName("updated_at_utc")] string UpdatedAtUtc,
    [property: JsonPropertyName("versions")] List<ModuleVersionItem> Versions,
    [property: JsonPropertyName("assignments")] List<ModuleAssignmentDetail> Assignments,
    [property: JsonPropertyName("variable_defs")] List<ModuleVariableDefItem> VariableDefs);
