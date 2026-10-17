using HomeIOT.Api.Contracts;

namespace HomeIOT.Api.Services.Models;

public sealed record DeviceProvisioningResult(
    DeviceProvisioningStatus Status,
    ProvisionDeviceResponse? Response = null,
    string? Message = null)
{
    public static DeviceProvisioningResult Failed(DeviceProvisioningStatus status, string message) =>
        new(status, null, message);
}
