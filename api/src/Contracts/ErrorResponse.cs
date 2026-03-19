using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ErrorResponse(
    [property: JsonPropertyName("error")] string Error,
    [property: JsonPropertyName("message")] string? Message = null);