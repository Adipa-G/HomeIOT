using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Services;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public class DeviceAdminServiceTests : IDisposable
{
    private readonly ApiDbContext _db;
    private readonly DeviceAdminService _service;

    public DeviceAdminServiceTests()
    {
        var options = new DbContextOptionsBuilder<ApiDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        _db = new ApiDbContext(options);
        _service = new DeviceAdminService(_db);
    }

    public void Dispose()
    {
        _db.Dispose();
    }

    private async Task<DeviceRecord> SeedDeviceAsync(string deviceId = "dev-001", string mode = "production")
    {
        var device = new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = deviceId,
            ApiKey = "key",
            Platform = "esp32",
            Version = "1.0.0",
            Mode = mode,
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.Devices.Add(device);
        await _db.SaveChangesAsync();
        return device;
    }

    [Fact]
    public async Task ListDevices_ReturnsAll()
    {
        await SeedDeviceAsync("dev-001");
        await SeedDeviceAsync("dev-002");

        var result = await _service.ListDevicesAsync(0, 50, null, null, null);

        Assert.Equal(2, result.Total);
        Assert.Equal(2, result.Items.Count);
    }

    [Fact]
    public async Task ListDevices_FiltersByPlatform()
    {
        await SeedDeviceAsync("dev-001");

        var result = await _service.ListDevicesAsync(0, 50, "pico", null, null);

        Assert.Equal(0, result.Total);
    }

    [Fact]
    public async Task ListDevices_FiltersByMode()
    {
        await SeedDeviceAsync("dev-001", "development");
        await SeedDeviceAsync("dev-002", "production");

        var result = await _service.ListDevicesAsync(0, 50, null, "development", null);

        Assert.Equal(1, result.Total);
        Assert.Equal("dev-001", result.Items[0].DeviceId);
    }

    [Fact]
    public async Task ListDevices_SearchByDeviceId()
    {
        await SeedDeviceAsync("sensor-001");
        await SeedDeviceAsync("actuator-002");

        var result = await _service.ListDevicesAsync(0, 50, null, null, "sensor");

        Assert.Equal(1, result.Total);
        Assert.Equal("sensor-001", result.Items[0].DeviceId);
    }

    [Fact]
    public async Task ListDevices_Pagination()
    {
        await SeedDeviceAsync("dev-001");
        await SeedDeviceAsync("dev-002");
        await SeedDeviceAsync("dev-003");

        var result = await _service.ListDevicesAsync(1, 1, null, null, null);

        Assert.Equal(3, result.Total);
        Assert.Single(result.Items);
        Assert.Equal(1, result.Offset);
    }

    [Fact]
    public async Task GetDevice_ReturnsDetail()
    {
        await SeedDeviceAsync("dev-001");

        var result = await _service.GetDeviceAsync("dev-001");

        Assert.NotNull(result);
        Assert.Equal("dev-001", result.DeviceId);
        Assert.Equal("esp32", result.Platform);
    }

    [Fact]
    public async Task GetDevice_NotFound_ReturnsNull()
    {
        var result = await _service.GetDeviceAsync("nonexistent");
        Assert.Null(result);
    }

    [Fact]
    public async Task UpdateDeviceMode_UpdatesAndReturnsTrue()
    {
        await SeedDeviceAsync("dev-001", "production");

        var result = await _service.UpdateDeviceModeAsync("dev-001", "development");

        Assert.True(result);
        var device = await _db.Devices.FirstAsync(d => d.DeviceId == "dev-001");
        Assert.Equal("development", device.Mode);
    }

    [Fact]
    public async Task UpdateDeviceMode_NotFound_ReturnsFalse()
    {
        var result = await _service.UpdateDeviceModeAsync("nonexistent", "development");
        Assert.False(result);
    }

    [Fact]
    public async Task DeleteDevice_RemovesAndReturnsTrue()
    {
        await SeedDeviceAsync("dev-001");

        var result = await _service.DeleteDeviceAsync("dev-001");

        Assert.True(result);
        Assert.False(await _db.Devices.AnyAsync(d => d.DeviceId == "dev-001"));
    }

    [Fact]
    public async Task DeleteDevice_NotFound_ReturnsFalse()
    {
        var result = await _service.DeleteDeviceAsync("nonexistent");
        Assert.False(result);
    }

    [Fact]
    public async Task GetHeartbeats_ReturnsPaginated()
    {
        var device = await SeedDeviceAsync("dev-001");
        _db.Heartbeats.Add(new HeartbeatRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            UptimeMs = 60000,
            FreeMemoryBytes = 100000,
            ReceivedAtUtc = DateTimeOffset.UtcNow,
        });
        await _db.SaveChangesAsync();

        var result = await _service.GetHeartbeatsAsync("dev-001", 0, 50, null, null);

        Assert.Equal(1, result.Total);
        Assert.Single(result.Items);
        Assert.Equal(60000, result.Items[0].UptimeMs);
    }

    [Fact]
    public async Task GetHeartbeats_UnknownDevice_ReturnsEmpty()
    {
        var result = await _service.GetHeartbeatsAsync("nonexistent", 0, 50, null, null);

        Assert.Equal(0, result.Total);
        Assert.Empty(result.Items);
    }

    [Fact]
    public async Task GetLogs_ReturnsPaginated()
    {
        var device = await SeedDeviceAsync("dev-001");
        _db.LogBatches.Add(new LogBatchRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            Reason = "periodic",
            SentAt = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
            DroppedCount = 0,
            Truncated = false,
            ReceivedCount = 5,
            LogsJson = "[]",
            ReceivedAtUtc = DateTimeOffset.UtcNow,
        });
        await _db.SaveChangesAsync();

        var result = await _service.GetLogsAsync("dev-001", 0, 50, null, null);

        Assert.Equal(1, result.Total);
        Assert.Single(result.Items);
        Assert.Equal("periodic", result.Items[0].Reason);
    }

    [Fact]
    public async Task GetHeartbeatActivity_BucketsByDay_CountsCorrectly()
    {
        var device = await SeedDeviceAsync("dev-001");
        var day1 = new DateTimeOffset(2026, 6, 1, 10, 0, 0, TimeSpan.Zero);
        var day2 = new DateTimeOffset(2026, 6, 2, 10, 0, 0, TimeSpan.Zero);

        _db.Heartbeats.Add(new HeartbeatRecord { Id = Guid.NewGuid(), DeviceRecordId = device.Id, ReceivedAtUtc = day1 });
        _db.Heartbeats.Add(new HeartbeatRecord { Id = Guid.NewGuid(), DeviceRecordId = device.Id, ReceivedAtUtc = day1.AddHours(1) });
        _db.Heartbeats.Add(new HeartbeatRecord { Id = Guid.NewGuid(), DeviceRecordId = device.Id, ReceivedAtUtc = day2 });
        await _db.SaveChangesAsync();

        var from = new DateTimeOffset(2026, 6, 1, 0, 0, 0, TimeSpan.Zero);
        var to = new DateTimeOffset(2026, 6, 3, 0, 0, 0, TimeSpan.Zero);
        var result = await _service.GetHeartbeatActivityAsync("dev-001", "day", from, to);

        Assert.Equal(2, result.Count);
        Assert.Equal(2, result[0].Count);
        Assert.Equal(1, result[1].Count);
    }

    [Fact]
    public async Task GetHeartbeatActivity_ZeroFillsEmptyBuckets()
    {
        await SeedDeviceAsync("dev-001");

        var from = new DateTimeOffset(2026, 6, 1, 0, 0, 0, TimeSpan.Zero);
        var to = new DateTimeOffset(2026, 6, 4, 0, 0, 0, TimeSpan.Zero);
        var result = await _service.GetHeartbeatActivityAsync("dev-001", "day", from, to);

        Assert.Equal(3, result.Count);
        Assert.All(result, b => Assert.Equal(0, b.Count));
    }

    [Fact]
    public async Task GetHeartbeatActivity_UnknownDevice_ReturnsZeroFilled()
    {
        var from = new DateTimeOffset(2026, 6, 1, 0, 0, 0, TimeSpan.Zero);
        var to = new DateTimeOffset(2026, 6, 2, 0, 0, 0, TimeSpan.Zero);
        var result = await _service.GetHeartbeatActivityAsync("nonexistent", "hour", from, to);

        Assert.Equal(24, result.Count);
        Assert.All(result, b => Assert.Equal(0, b.Count));
    }

    [Fact]
    public async Task GetLogActivity_ClassifiesLevelsCorrectly()
    {
        var device = await SeedDeviceAsync("dev-001");
        var batchTime = new DateTimeOffset(2026, 6, 1, 10, 0, 0, TimeSpan.Zero);
        var logsJson = "[{\"level\":\"info\"},{\"level\":\"ERROR\"},{\"level\":\"warn\"},{\"level\":\"warning\"},{\"level\":\"debug\"},{\"level\":\"trace\"}]";

        _db.LogBatches.Add(new LogBatchRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            Reason = "periodic",
            LogsJson = logsJson,
            ReceivedAtUtc = batchTime,
        });
        await _db.SaveChangesAsync();

        var from = new DateTimeOffset(2026, 6, 1, 0, 0, 0, TimeSpan.Zero);
        var to = new DateTimeOffset(2026, 6, 2, 0, 0, 0, TimeSpan.Zero);
        var result = await _service.GetLogActivityAsync("dev-001", "day", from, to);

        Assert.Single(result);
        Assert.Equal(1, result[0].InfoCount);
        Assert.Equal(1, result[0].ErrorCount);
        Assert.Equal(2, result[0].WarnCount);
        Assert.Equal(1, result[0].DebugCount);
        Assert.Equal(1, result[0].OtherCount);
    }

    [Fact]
    public async Task GetLogActivity_MalformedJson_SkippedWithoutThrowing()
    {
        var device = await SeedDeviceAsync("dev-001");
        var batchTime = new DateTimeOffset(2026, 6, 1, 10, 0, 0, TimeSpan.Zero);

        _db.LogBatches.Add(new LogBatchRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            Reason = "periodic",
            LogsJson = "not-valid-json",
            ReceivedAtUtc = batchTime,
        });
        await _db.SaveChangesAsync();

        var from = new DateTimeOffset(2026, 6, 1, 0, 0, 0, TimeSpan.Zero);
        var to = new DateTimeOffset(2026, 6, 2, 0, 0, 0, TimeSpan.Zero);
        var result = await _service.GetLogActivityAsync("dev-001", "day", from, to);

        Assert.Single(result);
        Assert.Equal(0, result[0].InfoCount + result[0].WarnCount + result[0].ErrorCount + result[0].DebugCount + result[0].OtherCount);
    }

    [Fact]
    public async Task GetLogActivity_UnknownDevice_ReturnsZeroFilled()
    {
        var from = new DateTimeOffset(2026, 6, 1, 0, 0, 0, TimeSpan.Zero);
        var to = new DateTimeOffset(2026, 6, 1, 1, 0, 0, TimeSpan.Zero);
        var result = await _service.GetLogActivityAsync("nonexistent", "five_minute", from, to);

        Assert.Equal(12, result.Count);
        Assert.All(result, b => Assert.Equal(0, b.InfoCount + b.WarnCount + b.ErrorCount + b.DebugCount + b.OtherCount));
    }
}
