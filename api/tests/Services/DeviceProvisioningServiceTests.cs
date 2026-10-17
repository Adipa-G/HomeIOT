using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Infrastructure;
using HomeIOT.Api.Services;
using HomeIOT.Api.Services.Models;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public class DeviceProvisioningServiceTests
{
    [Fact]
    public async Task CreateDeviceAsync_RegistersDeviceWithHashedKeyAndReturnsScript()
    {
        await using var db = CreateDb();
        BootstrapProvisioningData? captured = null;
        var builder = new Mock<IBootstrapScriptBuilder>();
        builder.Setup(x => x.Build(It.IsAny<BootstrapProvisioningData>()))
            .Callback<BootstrapProvisioningData>(d => captured = d)
            .Returns(new BootstrapScript("1.2.0", "script-body"));

        var result = await CreateService(db, builder).CreateDeviceAsync(new CreateDeviceRequest
        {
            DeviceId = " dev-001 ",
            Platform = "pico",
            ApiUrl = "http://host:8080/",
            WifiSsid = "ssid",
            WifiPassword = null,
        });

        Assert.Equal(DeviceProvisioningStatus.Success, result.Status);
        Assert.Equal(new ProvisionDeviceResponse("dev-001", "pico", "1.2.0", "main.py", "script-body"), result.Response);

        Assert.NotNull(captured);
        Assert.Equal("dev-001", captured!.DeviceId);
        Assert.Equal("http://host:8080", captured.ApiUrl);
        Assert.Equal(string.Empty, captured.WifiPassword);
        Assert.False(string.IsNullOrWhiteSpace(captured.ApiKey));

        var device = await db.Devices.SingleAsync();
        Assert.Equal("dev-001", device.DeviceId);
        Assert.Equal("pico", device.Platform);
        Assert.Equal("production", device.Mode);
        Assert.Null(device.Version);
        Assert.Equal(DeviceApiKeyHasher.Hash(captured.ApiKey), device.ApiKeyHash);
        Assert.DoesNotContain(captured.ApiKey, device.ApiKeyHash);
    }

    [Fact]
    public async Task CreateDeviceAsync_ExistingDevice_ReturnsDeviceExists()
    {
        await using var db = CreateDb();
        db.Devices.Add(NewDevice("dev-001", "esp32"));
        await db.SaveChangesAsync();
        var builder = new Mock<IBootstrapScriptBuilder>();

        var result = await CreateService(db, builder).CreateDeviceAsync(CreateRequest("dev-001"));

        Assert.Equal(DeviceProvisioningStatus.DeviceExists, result.Status);
        builder.Verify(x => x.Build(It.IsAny<BootstrapProvisioningData>()), Times.Never);
    }

    [Fact]
    public async Task CreateDeviceAsync_NoRelease_DoesNotCreateDevice()
    {
        await using var db = CreateDb();
        var builder = new Mock<IBootstrapScriptBuilder>();
        builder.Setup(x => x.Build(It.IsAny<BootstrapProvisioningData>())).Returns((BootstrapScript?)null);

        var result = await CreateService(db, builder).CreateDeviceAsync(CreateRequest("dev-001"));

        Assert.Equal(DeviceProvisioningStatus.NoRelease, result.Status);
        Assert.Contains("esp32", result.Message);
        Assert.False(await db.Devices.AnyAsync());
    }

    [Fact]
    public async Task CreateDeviceAsync_IncompleteRelease_DoesNotCreateDevice()
    {
        await using var db = CreateDb();
        var builder = new Mock<IBootstrapScriptBuilder>();
        builder.Setup(x => x.Build(It.IsAny<BootstrapProvisioningData>()))
            .Throws(new InvalidOperationException("missing updater.py"));

        var result = await CreateService(db, builder).CreateDeviceAsync(CreateRequest("dev-001"));

        Assert.Equal(DeviceProvisioningStatus.ReleaseIncomplete, result.Status);
        Assert.Equal("missing updater.py", result.Message);
        Assert.False(await db.Devices.AnyAsync());
    }

    [Fact]
    public async Task ReprovisionDeviceAsync_RotatesKeyAndUsesStoredPlatform()
    {
        await using var db = CreateDb();
        db.Devices.Add(NewDevice("dev-001", "esp32"));
        await db.SaveChangesAsync();
        BootstrapProvisioningData? captured = null;
        var builder = new Mock<IBootstrapScriptBuilder>();
        builder.Setup(x => x.Build(It.IsAny<BootstrapProvisioningData>()))
            .Callback<BootstrapProvisioningData>(d => captured = d)
            .Returns(new BootstrapScript("2.0.0", "script"));

        var result = await CreateService(db, builder).ReprovisionDeviceAsync("dev-001", new ReprovisionDeviceRequest
        {
            ApiUrl = "https://example.com",
            WifiSsid = "ssid",
            WifiPassword = "pw",
        });

        Assert.Equal(DeviceProvisioningStatus.Success, result.Status);
        Assert.Equal("esp32", captured!.Platform);
        var device = await db.Devices.SingleAsync();
        Assert.Equal(DeviceApiKeyHasher.Hash(captured.ApiKey), device.ApiKeyHash);
        Assert.False(DeviceApiKeyHasher.Verify("old-key", device.ApiKeyHash));
    }

    [Fact]
    public async Task ReprovisionDeviceAsync_PlatformOverride_UpdatesDevicePlatform()
    {
        await using var db = CreateDb();
        db.Devices.Add(NewDevice("dev-001", null));
        await db.SaveChangesAsync();
        var builder = new Mock<IBootstrapScriptBuilder>();
        builder.Setup(x => x.Build(It.IsAny<BootstrapProvisioningData>())).Returns(new BootstrapScript("2.0.0", "script"));

        var result = await CreateService(db, builder).ReprovisionDeviceAsync("dev-001", new ReprovisionDeviceRequest
        {
            Platform = "pico",
            ApiUrl = "https://example.com",
            WifiSsid = "ssid",
        });

        Assert.Equal(DeviceProvisioningStatus.Success, result.Status);
        Assert.Equal("pico", (await db.Devices.SingleAsync()).Platform);
    }

    [Fact]
    public async Task ReprovisionDeviceAsync_UnknownPlatform_ReturnsPlatformRequired()
    {
        await using var db = CreateDb();
        db.Devices.Add(NewDevice("dev-001", "simulator"));
        await db.SaveChangesAsync();
        var builder = new Mock<IBootstrapScriptBuilder>();

        var result = await CreateService(db, builder).ReprovisionDeviceAsync("dev-001", new ReprovisionDeviceRequest
        {
            ApiUrl = "https://example.com",
            WifiSsid = "ssid",
        });

        Assert.Equal(DeviceProvisioningStatus.PlatformRequired, result.Status);
        Assert.Equal("old-key", (await db.Devices.SingleAsync()).ApiKeyHash);
    }

    [Fact]
    public async Task ReprovisionDeviceAsync_NoRelease_KeepsExistingKey()
    {
        await using var db = CreateDb();
        db.Devices.Add(NewDevice("dev-001", "esp32"));
        await db.SaveChangesAsync();
        var builder = new Mock<IBootstrapScriptBuilder>();
        builder.Setup(x => x.Build(It.IsAny<BootstrapProvisioningData>())).Returns((BootstrapScript?)null);

        var result = await CreateService(db, builder).ReprovisionDeviceAsync("dev-001", new ReprovisionDeviceRequest
        {
            ApiUrl = "https://example.com",
            WifiSsid = "ssid",
        });

        Assert.Equal(DeviceProvisioningStatus.NoRelease, result.Status);
        Assert.Equal("old-key", (await db.Devices.SingleAsync()).ApiKeyHash);
    }

    [Fact]
    public async Task ReprovisionDeviceAsync_UnknownDevice_ReturnsNotFound()
    {
        await using var db = CreateDb();

        var result = await CreateService(db, new Mock<IBootstrapScriptBuilder>()).ReprovisionDeviceAsync("missing", new ReprovisionDeviceRequest
        {
            ApiUrl = "https://example.com",
            WifiSsid = "ssid",
        });

        Assert.Equal(DeviceProvisioningStatus.DeviceNotFound, result.Status);
    }

    private static CreateDeviceRequest CreateRequest(string deviceId) => new()
    {
        DeviceId = deviceId,
        Platform = "esp32",
        ApiUrl = "http://host:8080",
        WifiSsid = "ssid",
        WifiPassword = "pw",
    };

    private static DeviceRecord NewDevice(string deviceId, string? platform) => new()
    {
        Id = Guid.NewGuid(),
        DeviceId = deviceId,
        ApiKeyHash = "old-key",
        Platform = platform,
        Mode = "production",
        CreatedAtUtc = DateTimeOffset.UtcNow,
        UpdatedAtUtc = DateTimeOffset.UtcNow,
    };

    private static DeviceProvisioningService CreateService(ApiDbContext db, Mock<IBootstrapScriptBuilder> builder) =>
        new(db, builder.Object, NullLogger<DeviceProvisioningService>.Instance);

    private static ApiDbContext CreateDb() =>
        new(new DbContextOptionsBuilder<ApiDbContext>().UseInMemoryDatabase(Guid.NewGuid().ToString("N")).Options);
}
