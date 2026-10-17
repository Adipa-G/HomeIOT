using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class ReprovisionDeviceRequest
{
    /// <summary>Optional; defaults to the platform already recorded for the device.</summary>
    [JsonPropertyName("platform")]
    public string? Platform { get; set; }

    [JsonPropertyName("api_url")]
    public string? ApiUrl { get; set; }

    [JsonPropertyName("wifi_ssid")]
    public string? WifiSsid { get; set; }

    [JsonPropertyName("wifi_password")]
    public string? WifiPassword { get; set; }
}
