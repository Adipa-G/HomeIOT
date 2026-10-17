using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class CreateDeviceRequest
{
    [JsonPropertyName("device_id")]
    public string? DeviceId { get; set; }

    [JsonPropertyName("platform")]
    public string? Platform { get; set; }

    [JsonPropertyName("api_url")]
    public string? ApiUrl { get; set; }

    [JsonPropertyName("wifi_ssid")]
    public string? WifiSsid { get; set; }

    [JsonPropertyName("wifi_password")]
    public string? WifiPassword { get; set; }
}
