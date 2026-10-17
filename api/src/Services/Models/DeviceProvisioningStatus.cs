namespace HomeIOT.Api.Services.Models;

public enum DeviceProvisioningStatus
{
    Success,
    DeviceExists,
    DeviceNotFound,
    PlatformRequired,
    NoRelease,
    ReleaseIncomplete,
}
