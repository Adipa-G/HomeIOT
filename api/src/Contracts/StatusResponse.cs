using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record StatusResponse(
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("received")] int? Received = null);
