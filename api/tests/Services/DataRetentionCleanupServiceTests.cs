using HomeIOT.Api.Configuration;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Services;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public class DataRetentionCleanupServiceTests : IDisposable
{
    private readonly ServiceProvider _provider;
    private readonly string _dbName = Guid.NewGuid().ToString("N");

    public DataRetentionCleanupServiceTests()
    {
        var services = new ServiceCollection();
        services.AddDbContext<ApiDbContext>(options => options.UseInMemoryDatabase(_dbName));
        _provider = services.BuildServiceProvider();
    }

    public void Dispose()
    {
        _provider.Dispose();
    }

    private async Task<Guid> SeedDeviceAsync(ApiDbContext db)
    {
        var device = new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = "dev-001",
            ApiKey = "key",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        db.Devices.Add(device);
        await db.SaveChangesAsync();
        return device.Id;
    }

    private DataRetentionCleanupService CreateService(int retentionDays, int cleanupIntervalMinutes = 60)
    {
        var scopeFactory = _provider.GetRequiredService<IServiceScopeFactory>();
        var options = Options.Create(new DataRetentionOptions
        {
            RetentionDays = retentionDays,
            CleanupIntervalMinutes = cleanupIntervalMinutes,
        });
        return new DataRetentionCleanupService(scopeFactory, options, NullLogger<DataRetentionCleanupService>.Instance);
    }

    [Fact]
    public async Task RunCleanupOnceAsync_RemovesHeartbeatsOlderThanRetention()
    {
        using var db = _provider.GetRequiredService<ApiDbContext>();
        var deviceId = await SeedDeviceAsync(db);

        db.Heartbeats.Add(new HeartbeatRecord { Id = Guid.NewGuid(), DeviceRecordId = deviceId, ReceivedAtUtc = DateTimeOffset.UtcNow.AddDays(-40) });
        db.Heartbeats.Add(new HeartbeatRecord { Id = Guid.NewGuid(), DeviceRecordId = deviceId, ReceivedAtUtc = DateTimeOffset.UtcNow.AddDays(-1) });
        await db.SaveChangesAsync();

        var service = CreateService(retentionDays: 30);
        await service.RunCleanupOnceAsync(CancellationToken.None);

        var remaining = await db.Heartbeats.ToListAsync();
        Assert.Single(remaining);
        Assert.True(remaining[0].ReceivedAtUtc > DateTimeOffset.UtcNow.AddDays(-30));
    }

    [Fact]
    public async Task RunCleanupOnceAsync_RemovesLogBatchesOlderThanRetention()
    {
        using var db = _provider.GetRequiredService<ApiDbContext>();
        var deviceId = await SeedDeviceAsync(db);

        db.LogBatches.Add(new LogBatchRecord { Id = Guid.NewGuid(), DeviceRecordId = deviceId, Reason = "periodic", ReceivedAtUtc = DateTimeOffset.UtcNow.AddDays(-40) });
        db.LogBatches.Add(new LogBatchRecord { Id = Guid.NewGuid(), DeviceRecordId = deviceId, Reason = "periodic", ReceivedAtUtc = DateTimeOffset.UtcNow.AddDays(-1) });
        await db.SaveChangesAsync();

        var service = CreateService(retentionDays: 30);
        await service.RunCleanupOnceAsync(CancellationToken.None);

        var remaining = await db.LogBatches.ToListAsync();
        Assert.Single(remaining);
        Assert.True(remaining[0].ReceivedAtUtc > DateTimeOffset.UtcNow.AddDays(-30));
    }

    [Fact]
    public async Task RunCleanupOnceAsync_RetentionDaysZero_DoesNotDeleteAnything()
    {
        using var db = _provider.GetRequiredService<ApiDbContext>();
        var deviceId = await SeedDeviceAsync(db);

        db.Heartbeats.Add(new HeartbeatRecord { Id = Guid.NewGuid(), DeviceRecordId = deviceId, ReceivedAtUtc = DateTimeOffset.UtcNow.AddDays(-999) });
        await db.SaveChangesAsync();

        var service = CreateService(retentionDays: 0);
        await service.RunCleanupOnceAsync(CancellationToken.None);

        Assert.Equal(1, await db.Heartbeats.CountAsync());
    }

    [Fact]
    public async Task RunCleanupOnceAsync_NegativeRetentionDays_DoesNotDeleteAnything()
    {
        using var db = _provider.GetRequiredService<ApiDbContext>();
        var deviceId = await SeedDeviceAsync(db);

        db.LogBatches.Add(new LogBatchRecord { Id = Guid.NewGuid(), DeviceRecordId = deviceId, Reason = "periodic", ReceivedAtUtc = DateTimeOffset.UtcNow.AddDays(-999) });
        await db.SaveChangesAsync();

        var service = CreateService(retentionDays: -1);
        await service.RunCleanupOnceAsync(CancellationToken.None);

        Assert.Equal(1, await db.LogBatches.CountAsync());
    }
}
