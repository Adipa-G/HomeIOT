using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace HomeIOT.Api.Tests.Fixtures;

public class DatabaseFixture : IAsyncLifetime
{
    private DbContextOptions<ApiDbContext>? _options;
    public ApiDbContext DbContext { get; private set; } = null!;

    public async Task InitializeAsync()
    {
        // Use in-memory SQLite for test isolation
        _options = new DbContextOptionsBuilder<ApiDbContext>()
            .UseSqlite("Data Source=:memory:;")
            .Options;

        DbContext = new ApiDbContext(_options);
        
        // Create the database schema using EF Core model, not migrations
        // For in-memory SQLite, EnsureCreated() is preferred over Migrate()
        await DbContext.Database.EnsureCreatedAsync();
    }

    public async Task DisposeAsync()
    {
        if (DbContext != null)
        {
            await DbContext.Database.EnsureDeletedAsync();
            await DbContext.DisposeAsync();
        }
    }

    public async Task<DeviceRecord> SeedTestDeviceAsync(
        string deviceId = "test-device-001",
        string apiKey = "test-key-secret",
        string? platform = "esp32",
        string? version = "1.0.0")
    {
        var device = new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = deviceId,
            ApiKey = apiKey,
            Platform = platform,
            Version = version,
            Mode = "production",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };

        DbContext.Devices.Add(device);
        await DbContext.SaveChangesAsync();
        return device;
    }
}
