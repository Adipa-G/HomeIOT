using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record OtaReleaseListItem(
    [property: JsonPropertyName("version")] string Version,
    [property: JsonPropertyName("file_count")] int FileCount,
    [property: JsonPropertyName("total_size_bytes")] long TotalSizeBytes);
