using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record DevCommandResultAcceptedResponse(
    [property: JsonPropertyName("command_id")] string CommandId,
    [property: JsonPropertyName("status")] string Status);
