using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record UpdateAssignmentResponse(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("id")] Guid Id);
