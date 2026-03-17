using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace HomeIOT.Api.Tests.Data;

public class ApiDbContextTests
{
    [Fact]
    public async Task SeedTestDevice_CreatesDeviceRecord()
    {
        await using var dbContext = CreateDbContext();

        var device = new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = "seed-device-001",
            ApiKey = "seed-key-001",
            Platform = "esp32",
            Version = "1.0.0",
            Mode = "production",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };

        dbContext.Devices.Add(device);
        await dbContext.SaveChangesAsync();

        var saved = await dbContext.Devices.SingleAsync(x => x.DeviceId == "seed-device-001");
        Assert.Equal("seed-key-001", saved.ApiKey);
        Assert.Equal("esp32", saved.Platform);
    }

    [Fact]
    public async Task DeviceUpsert_CreatesNewDeviceWhenNotExists()
    {
        await using var dbContext = CreateDbContext();
        const string deviceId = "upsert-device-001";

        var existing = await dbContext.Devices.FirstOrDefaultAsync(x => x.DeviceId == deviceId);
        if (existing is null)
        {
            dbContext.Devices.Add(new DeviceRecord
            {
                Id = Guid.NewGuid(),
                DeviceId = deviceId,
                ApiKey = "upsert-key-001",
                Mode = "production",
                CreatedAtUtc = DateTimeOffset.UtcNow,
                UpdatedAtUtc = DateTimeOffset.UtcNow,
            });
            await dbContext.SaveChangesAsync();
        }

        var count = await dbContext.Devices.CountAsync(x => x.DeviceId == deviceId);
        Assert.Equal(1, count);
    }

    [Fact]
    public async Task Heartbeat_CreatesRecordWithDeviceForeignKey()
    {
        await using var dbContext = CreateDbContext();

        var device = new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = "hb-device-001",
            ApiKey = "hb-key-001",
            Mode = "production",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        dbContext.Devices.Add(device);
        await dbContext.SaveChangesAsync();

        dbContext.Heartbeats.Add(new HeartbeatRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            ClientTimestamp = 1716890300,
            UptimeMs = 60000,
            FreeMemoryBytes = 204800,
            ReceivedAtUtc = DateTimeOffset.UtcNow,
        });
        await dbContext.SaveChangesAsync();

        var saved = await dbContext.Heartbeats.Include(x => x.Device).SingleAsync();
        Assert.Equal(device.Id, saved.DeviceRecordId);
        Assert.Equal("hb-device-001", saved.Device.DeviceId);
    }

    private static ApiDbContext CreateDbContext()
    {
        var options = new DbContextOptionsBuilder<ApiDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;

        return new ApiDbContext(options);
    }
}

