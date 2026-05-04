using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ModuleVariableValueItem(
    [property: JsonPropertyName("variable_name")] string VariableName,
    [property: JsonPropertyName("value")] string? Value,
    [property: JsonPropertyName("source")] string Source,
    [property: JsonPropertyName("last_computed_at_utc")] string? LastComputedAtUtc);
