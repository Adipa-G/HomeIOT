using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record OtaPlatformListItem(
    [property: JsonPropertyName("platform")] string Platform,
    [property: JsonPropertyName("release_count")] int ReleaseCount);
