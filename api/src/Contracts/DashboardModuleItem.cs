using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record DashboardModuleItem(
    [property: JsonPropertyName("assignment_id")] Guid AssignmentId,
    [property: JsonPropertyName("device_id")] string DeviceId,
    [property: JsonPropertyName("module_id")] string ModuleId,
    [property: JsonPropertyName("status")] string? Status,
    [property: JsonPropertyName("output")] string? Output,
    [property: JsonPropertyName("error_message")] string? ErrorMessage,
    [property: JsonPropertyName("finished_at_utc")] string? FinishedAtUtc,
    [property: JsonPropertyName("variable_defs")] List<ModuleVariableDefItem> VariableDefs);
