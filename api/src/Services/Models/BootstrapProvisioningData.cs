namespace HomeIOT.Api.Services.Models;

public sealed record BootstrapProvisioningData(
    string DeviceId,
    string Platform,
    string ApiUrl,
    string ApiKey,
    string WifiSsid,
    string WifiPassword);
