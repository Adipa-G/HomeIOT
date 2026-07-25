using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ServerCodeTemplateItem(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("description")] string Description,
    [property: JsonPropertyName("setup_guide")] string SetupGuide,
    [property: JsonPropertyName("code")] string Code);
