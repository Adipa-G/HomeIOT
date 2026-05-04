using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ModuleVariableDefItem(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("type")] string Type,
    [property: JsonPropertyName("default_value")] string? DefaultValue,
    [property: JsonPropertyName("description")] string? Description,
    [property: JsonPropertyName("has_server_code")] bool HasServerCode,
    [property: JsonPropertyName("server_code")] string? ServerCode = null);
