using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class UpdateDeviceModeRequest
{
    [JsonPropertyName("mode")]
    public string? Mode { get; set; }
}
