using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class UploadVersionRequest
{
    [JsonPropertyName("version")]
    public string? Version { get; set; }

    [JsonPropertyName("code")]
    public string? Code { get; set; }
}
