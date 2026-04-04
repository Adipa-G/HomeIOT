using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record OtaManifestFileItem(
    [property: JsonPropertyName("path")] string Path,
    [property: JsonPropertyName("hash")] string Hash,
    [property: JsonPropertyName("size_bytes")] long SizeBytes);
