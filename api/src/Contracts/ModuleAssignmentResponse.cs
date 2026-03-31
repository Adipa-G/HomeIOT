using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ModuleAssignmentResponse(
    [property: JsonPropertyName("assignment_hash")] string AssignmentHash,
    [property: JsonPropertyName("modules")] List<ModuleAssignmentItem> Modules);

