using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Services;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public sealed class ModuleServerCodeServiceTests
{
    [Fact]
    public async Task RunForModuleAsync_EvaluatesServerExpressionAndStoresComputedValue()
    {
        await using var connection = new SqliteConnection("Data Source=:memory:");
        await connection.OpenAsync();
        await using var db = new ApiDbContext(
            new DbContextOptionsBuilder<ApiDbContext>().UseSqlite(connection).Options);
        await db.Database.EnsureCreatedAsync();

        var device = new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = "server-code-device",
            ApiKey = "test-key",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        var module = new ModuleDefinitionRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = "server-code-module",
            DefaultEntrypoint = "run",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        var version = new ModuleVersionRecord
        {
            Id = Guid.NewGuid(),
            ModuleDefinitionId = module.Id,
            Version = "1.0.0",
            PackageHash = "test-hash",
            PackageSizeBytes = 0,
            CreatedAtUtc = DateTimeOffset.UtcNow,
        };
        var assignment = new ModuleAssignmentRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            ModuleDefinitionId = module.Id,
            ModuleVersionId = version.Id,
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        var variable = new ModuleVariableDefRecord
        {
            Id = Guid.NewGuid(),
            ModuleDefinitionId = module.Id,
            Name = "SERVER_MESSAGE",
            Type = "string",
            ServerCode = "\"computed value\"",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };

        db.Devices.Add(device);
        db.ModuleDefinitions.Add(module);
        db.ModuleVersions.Add(version);
        db.ModuleAssignments.Add(assignment);
        db.ModuleVariableDefs.Add(variable);
        await db.SaveChangesAsync();

        var service = new ModuleServerCodeService(
            db,
            new ModuleVariableService(db),
            NullLogger<ModuleServerCodeService>.Instance);

        await service.RunForModuleAsync(device.DeviceId, module.ModuleId);

        var computedValue = Assert.Single(db.ModuleVariableValues);
        Assert.Equal("SERVER_MESSAGE", computedValue.VariableName);
        Assert.Equal("computed value", computedValue.Value);
        Assert.True(computedValue.ComputedByServer);
    }
}