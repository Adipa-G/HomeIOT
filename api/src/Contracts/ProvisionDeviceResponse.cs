using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ProvisionDeviceResponse(
    [property: JsonPropertyName("device_id")] string DeviceId,
    [property: JsonPropertyName("platform")] string Platform,
    [property: JsonPropertyName("release_version")] string ReleaseVersion,
    [property: JsonPropertyName("file_name")] string FileName,
    [property: JsonPropertyName("script")] string Script);
