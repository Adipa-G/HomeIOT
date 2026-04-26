using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record DevCommandNextResponse(
    [property: JsonPropertyName("command_id")] string CommandId,
    [property: JsonPropertyName("revision_hash")] string RevisionHash,
    [property: JsonPropertyName("dedupe_token")] string DedupeToken,
    [property: JsonPropertyName("code")] string Code,
    [property: JsonPropertyName("timeout_ms")] int? TimeoutMs);
