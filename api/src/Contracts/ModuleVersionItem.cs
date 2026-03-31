using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ModuleVersionItem(
    [property: JsonPropertyName("id")] Guid Id,
    [property: JsonPropertyName("version")] string Version,
    [property: JsonPropertyName("package_hash")] string PackageHash,
    [property: JsonPropertyName("package_size_bytes")] long PackageSizeBytes,
    [property: JsonPropertyName("created_at_utc")] string CreatedAtUtc);
