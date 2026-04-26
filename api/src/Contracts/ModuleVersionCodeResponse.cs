using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ModuleVersionCodeResponse(
    [property: JsonPropertyName("module_id")] string ModuleId,
    [property: JsonPropertyName("version")] string Version,
    [property: JsonPropertyName("code")] string Code);
