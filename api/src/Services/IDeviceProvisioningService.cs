using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services.Models;

namespace HomeIOT.Api.Services;

public interface IDeviceProvisioningService
{
    /// <summary>Pre-registers a new device with a freshly generated API key and returns its first-boot main.py.</summary>
    Task<DeviceProvisioningResult> CreateDeviceAsync(CreateDeviceRequest request, CancellationToken ct = default);

    /// <summary>Rotates the API key of an existing device and returns a new first-boot main.py.</summary>
    Task<DeviceProvisioningResult> ReprovisionDeviceAsync(string deviceId, ReprovisionDeviceRequest request, CancellationToken ct = default);
}
