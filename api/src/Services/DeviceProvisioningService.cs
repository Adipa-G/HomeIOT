using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Infrastructure;
using HomeIOT.Api.Services.Models;
using Microsoft.EntityFrameworkCore;

namespace HomeIOT.Api.Services;

public sealed class DeviceProvisioningService : IDeviceProvisioningService
{
    public const string BootstrapFileName = "main.py";

    private readonly ApiDbContext _db;
    private readonly IBootstrapScriptBuilder _scriptBuilder;
    private readonly ILogger<DeviceProvisioningService> _logger;

    public DeviceProvisioningService(
        ApiDbContext db,
        IBootstrapScriptBuilder scriptBuilder,
        ILogger<DeviceProvisioningService> logger)
    {
        _db = db;
        _scriptBuilder = scriptBuilder;
        _logger = logger;
    }

    public async Task<DeviceProvisioningResult> CreateDeviceAsync(CreateDeviceRequest request, CancellationToken ct = default)
    {
        var deviceId = request.DeviceId!.Trim();
        var platform = request.Platform!.Trim();

        if (await _db.Devices.AnyAsync(d => d.DeviceId == deviceId, ct))
        {
            return DeviceProvisioningResult.Failed(DeviceProvisioningStatus.DeviceExists, $"Device '{deviceId}' already exists.");
        }

        var apiKey = DeviceApiKeyHasher.GenerateKey();
        var built = BuildScript(new BootstrapProvisioningData(
            deviceId, platform, NormalizeApiUrl(request.ApiUrl!), apiKey, request.WifiSsid!, request.WifiPassword ?? string.Empty));
        if (built.Script is null)
        {
            return built.Failure!;
        }

        var now = DateTimeOffset.UtcNow;
        _db.Devices.Add(new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = deviceId,
            ApiKeyHash = DeviceApiKeyHasher.Hash(apiKey),
            Platform = platform,
            Mode = "production",
            CreatedAtUtc = now,
            UpdatedAtUtc = now,
        });
        await _db.SaveChangesAsync(ct);

        _logger.LogInformation("Provisioned new device {DeviceId} ({Platform}) for release {Version}", deviceId, platform, built.Script.ReleaseVersion);
        return Success(deviceId, platform, built.Script);
    }

    public async Task<DeviceProvisioningResult> ReprovisionDeviceAsync(string deviceId, ReprovisionDeviceRequest request, CancellationToken ct = default)
    {
        var device = await _db.Devices.FirstOrDefaultAsync(d => d.DeviceId == deviceId, ct);
        if (device is null)
        {
            return DeviceProvisioningResult.Failed(DeviceProvisioningStatus.DeviceNotFound, "Device not found.");
        }

        var platform = string.IsNullOrWhiteSpace(request.Platform) ? device.Platform?.Trim() : request.Platform.Trim();
        if (!DevicePlatforms.IsProvisionable(platform))
        {
            return DeviceProvisioningResult.Failed(
                DeviceProvisioningStatus.PlatformRequired,
                $"platform must be one of: {string.Join(", ", DevicePlatforms.Provisionable)}.");
        }

        var apiKey = DeviceApiKeyHasher.GenerateKey();
        var built = BuildScript(new BootstrapProvisioningData(
            device.DeviceId, platform!, NormalizeApiUrl(request.ApiUrl!), apiKey, request.WifiSsid!, request.WifiPassword ?? string.Empty));
        if (built.Script is null)
        {
            return built.Failure!;
        }

        device.ApiKeyHash = DeviceApiKeyHasher.Hash(apiKey);
        device.Platform = platform;
        device.UpdatedAtUtc = DateTimeOffset.UtcNow;
        await _db.SaveChangesAsync(ct);

        _logger.LogInformation("Re-provisioned device {DeviceId} ({Platform}); API key rotated", device.DeviceId, platform);
        return Success(device.DeviceId, platform!, built.Script);
    }

    private (BootstrapScript? Script, DeviceProvisioningResult? Failure) BuildScript(BootstrapProvisioningData data)
    {
        try
        {
            var script = _scriptBuilder.Build(data);
            if (script is null)
            {
                return (null, DeviceProvisioningResult.Failed(
                    DeviceProvisioningStatus.NoRelease,
                    $"No firmware release uploaded for platform '{data.Platform}'. Upload a release first."));
            }

            return (script, null);
        }
        catch (InvalidOperationException ex)
        {
            _logger.LogWarning(ex, "Unable to build bootstrap script for {Platform}", data.Platform);
            return (null, DeviceProvisioningResult.Failed(DeviceProvisioningStatus.ReleaseIncomplete, ex.Message));
        }
    }

    private static DeviceProvisioningResult Success(string deviceId, string platform, BootstrapScript script)
    {
        return new DeviceProvisioningResult(
            DeviceProvisioningStatus.Success,
            new ProvisionDeviceResponse(deviceId, platform, script.ReleaseVersion, BootstrapFileName, script.Content));
    }

    private static string NormalizeApiUrl(string apiUrl)
    {
        return apiUrl.Trim().TrimEnd('/');
    }
}
