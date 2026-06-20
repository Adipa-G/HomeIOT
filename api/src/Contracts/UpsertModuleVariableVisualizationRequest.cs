using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record UpsertModuleVariableVisualizationRequest(
    [property: JsonPropertyName("json_path")] string JsonPath,
    [property: JsonPropertyName("display_name")] string DisplayName,
    [property: JsonPropertyName("visualization_type")] string? VisualizationType = null,
    [property: JsonPropertyName("visualization_config")] object? VisualizationConfig = null);
