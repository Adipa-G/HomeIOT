using HomeIOT.Api.Configuration;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Hosting;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public class ModuleServiceTests : IDisposable
{
    private readonly ApiDbContext _db;
    private readonly string _tempDir;
    private readonly ModuleService _service;

    public ModuleServiceTests()
    {
        var options = new DbContextOptionsBuilder<ApiDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        _db = new ApiDbContext(options);

        _tempDir = Path.Combine(Path.GetTempPath(), $"module_test_{Guid.NewGuid():N}");
        Directory.CreateDirectory(_tempDir);

        var storageOptions = new Mock<IOptions<ModuleStorageOptions>>();
        storageOptions.Setup(x => x.Value).Returns(new ModuleStorageOptions { PackageRoot = _tempDir });

        var env = new Mock<IWebHostEnvironment>();
        env.Setup(x => x.ContentRootPath).Returns(_tempDir);

        var logger = new Mock<ILogger<ModuleService>>();
        var variableService = new Mock<IModuleVariableService>();
        variableService
            .Setup(v => v.GetResolvedVariablesAsync(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new Dictionary<string, string?>());

        _service = new ModuleService(_db, storageOptions.Object, env.Object, logger.Object, variableService.Object);
    }

    public void Dispose()
    {
        _db.Dispose();
        if (Directory.Exists(_tempDir))
            Directory.Delete(_tempDir, true);
    }

    [Fact]
    public async Task GetAssignmentForDevice_NoDevice_ReturnsNull()
    {
        var result = await _service.GetAssignmentForDeviceAsync("nonexistent", null);
        Assert.Null(result);
    }

    [Fact]
    public async Task GetAssignmentForDevice_NoAssignments_ReturnsEmptyList()
    {
        await SeedDeviceAsync("dev-001");

        var result = await _service.GetAssignmentForDeviceAsync("dev-001", null);

        Assert.NotNull(result);
        Assert.Empty(result.Modules);
        Assert.NotEmpty(result.AssignmentHash);
    }

    [Fact]
    public async Task GetAssignmentForDevice_WithAssignment_ReturnsModules()
    {
        var device = await SeedDeviceAsync("dev-001");
        var (module, version) = await SeedModuleWithVersionAsync("sensor-reader", "1.0.0");
        await SeedAssignmentAsync(device, module, version);

        var result = await _service.GetAssignmentForDeviceAsync("dev-001", null);

        Assert.NotNull(result);
        Assert.Single(result.Modules);
        var item = result.Modules[0];
        Assert.Equal("sensor-reader", item.ModuleId);
        Assert.Equal("1.0.0", item.Version);
        Assert.Equal(60000, item.IntervalMs);
        Assert.Equal("run", item.Entrypoint);
        Assert.True(item.Enabled);
    }

    [Fact]
    public async Task GetAssignmentForDevice_HashUnchanged_ReturnsNull()
    {
        var device = await SeedDeviceAsync("dev-001");
        var (module, version) = await SeedModuleWithVersionAsync("sensor-reader", "1.0.0");
        await SeedAssignmentAsync(device, module, version);

        var first = await _service.GetAssignmentForDeviceAsync("dev-001", null);
        Assert.NotNull(first);

        var second = await _service.GetAssignmentForDeviceAsync("dev-001", first.AssignmentHash);
        Assert.Null(second); // 204 dedup
    }

    [Fact]
    public void GetPackage_FileExists_ReturnsBytes()
    {
        var moduleDir = Path.Combine(_tempDir, "test-mod");
        Directory.CreateDirectory(moduleDir);
        var content = "def run(ctx): return {'ok': True}"u8.ToArray();
        File.WriteAllBytes(Path.Combine(moduleDir, "1.0.0.py"), content);

        var result = _service.GetPackage("test-mod", "1.0.0");

        Assert.NotNull(result);
        Assert.Equal(content, result);
    }

    [Fact]
    public void GetPackage_FileNotFound_ReturnsNull()
    {
        var result = _service.GetPackage("nonexistent", "1.0.0");
        Assert.Null(result);
    }

    [Fact]
    public void GetPackage_UnsafeModuleId_ReturnsNull()
    {
        var result = _service.GetPackage("../etc", "1.0.0");
        Assert.Null(result);
    }

    [Fact]
    public async Task RecordResult_StoresInDatabase()
    {
        var request = new ModuleResultRequest
        {
            DeviceId = "dev-001",
            ModuleId = "sensor-reader",
            ModuleVersion = "1.0.0",
            RunId = "sensor-reader:1.0.0:1000:1",
            StartedAtUtc = "2026-05-30T10:00:00Z",
            FinishedAtUtc = "2026-05-30T10:00:01Z",
            ElapsedMs = 1000,
            Status = "success",
            Output = new { temperature = 22.5 },
        };

        await _service.RecordResultAsync(request);

        var stored = await _db.ModuleResults.SingleAsync();
        Assert.Equal("dev-001", stored.DeviceId);
        Assert.Equal("sensor-reader", stored.ModuleId);
        Assert.Equal("success", stored.Status);
        Assert.Equal(1000, stored.ElapsedMs);
    }

    [Fact]
    public async Task RecordStatus_StoresInDatabase()
    {
        var request = new ModuleStatusRequest
        {
            DeviceId = "dev-001",
            ModuleId = "sensor-reader",
            ModuleVersion = "1.0.0",
            Disabled = true,
            DisabledReason = "Failed start count exceeded threshold",
            FailedStartCount = 3,
            DisabledAtUtc = "2026-05-30T10:00:00Z",
        };

        await _service.RecordStatusAsync(request);

        var stored = await _db.ModuleStatuses.SingleAsync();
        Assert.Equal("dev-001", stored.DeviceId);
        Assert.True(stored.Disabled);
        Assert.Equal(3, stored.FailedStartCount);
    }

    [Fact]
    public async Task CreateModule_CreatesRecord()
    {
        var request = new CreateModuleRequest
        {
            ModuleId = "new-module",
            Description = "A test module",
            DefaultEntrypoint = "execute",
        };

        var result = await _service.CreateModuleAsync(request);

        Assert.Equal("new-module", result.ModuleId);
        Assert.Equal("execute", result.DefaultEntrypoint);

        var stored = await _db.ModuleDefinitions.SingleAsync();
        Assert.Equal("new-module", stored.ModuleId);
    }

    [Fact]
    public async Task UploadVersion_CreatesFileAndRecord()
    {
        var module = new ModuleDefinitionRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = "upload-test",
            DefaultEntrypoint = "run",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleDefinitions.Add(module);
        await _db.SaveChangesAsync();

        var content = "def run(ctx): pass"u8.ToArray();
        using var stream = new MemoryStream(content);

        var result = await _service.UploadVersionAsync("upload-test", "1.0.0", stream);

        Assert.NotNull(result);
        Assert.Equal("1.0.0", result.Version);
        Assert.Equal(content.Length, result.PackageSizeBytes);
        Assert.StartsWith("sha256:", result.PackageHash);

        var filePath = Path.Combine(_tempDir, "upload-test", "1.0.0.py");
        Assert.True(File.Exists(filePath));
        Assert.Equal(content, File.ReadAllBytes(filePath));
    }

    [Fact]
    public async Task UploadVersion_NonexistentModule_ReturnsNull()
    {
        using var stream = new MemoryStream("data"u8.ToArray());
        var result = await _service.UploadVersionAsync("nonexistent", "1.0.0", stream);
        Assert.Null(result);
    }

    [Fact]
    public async Task AssignModule_CreatesAssignment()
    {
        var device = await SeedDeviceAsync("dev-001");
        var (module, version) = await SeedModuleWithVersionAsync("test-mod", "1.0.0");

        var request = new AssignModuleRequest
        {
            DeviceId = "dev-001",
            Version = "1.0.0",
            IntervalMs = 30000,
            TimeoutMs = 3000,
        };

        var result = await _service.AssignModuleAsync("test-mod", request);

        Assert.NotNull(result);
        Assert.Equal(30000, result.IntervalMs);
        Assert.Equal(3000, result.TimeoutMs);
        Assert.True(result.Enabled);
    }

    [Fact]
    public async Task AssignModule_NonexistentDevice_ReturnsNull()
    {
        await SeedModuleWithVersionAsync("test-mod", "1.0.0");

        var request = new AssignModuleRequest
        {
            DeviceId = "nonexistent",
            Version = "1.0.0",
        };

        var result = await _service.AssignModuleAsync("test-mod", request);
        Assert.Null(result);
    }

    [Fact]
    public async Task UpdateAssignment_UpdatesFields()
    {
        var device = await SeedDeviceAsync("dev-001");
        var (module, version) = await SeedModuleWithVersionAsync("test-mod", "1.0.0");
        var assignment = await SeedAssignmentAsync(device, module, version);

        var request = new UpdateAssignmentRequest
        {
            IntervalMs = 15000,
            Enabled = false,
        };

        var result = await _service.UpdateAssignmentAsync(assignment.Id, request);

        Assert.NotNull(result);
        Assert.Equal(15000, result.IntervalMs);
        Assert.False(result.Enabled);
    }

    [Fact]
    public async Task RemoveAssignment_DeletesRecord()
    {
        var device = await SeedDeviceAsync("dev-001");
        var (module, version) = await SeedModuleWithVersionAsync("test-mod", "1.0.0");
        var assignment = await SeedAssignmentAsync(device, module, version);

        var result = await _service.RemoveAssignmentAsync(assignment.Id);

        Assert.True(result);
        Assert.Empty(await _db.ModuleAssignments.ToListAsync());
    }

    [Fact]
    public async Task RemoveAssignment_NonexistentId_ReturnsFalse()
    {
        var result = await _service.RemoveAssignmentAsync(Guid.NewGuid());
        Assert.False(result);
    }

    [Fact]
    public async Task ListModules_ReturnsAll()
    {
        await SeedModuleWithVersionAsync("mod-a", "1.0.0");
        await SeedModuleWithVersionAsync("mod-b", "2.0.0");

        var result = await _service.ListModulesAsync();

        Assert.Equal(2, result.Count);
        Assert.Equal("mod-a", result[0].ModuleId);
        Assert.Equal("mod-b", result[1].ModuleId);
    }

    [Fact]
    public async Task GetModule_ReturnsDetailWithVersionsAndAssignments()
    {
        var device = await SeedDeviceAsync("dev-001");
        var (module, version) = await SeedModuleWithVersionAsync("detailed-mod", "1.0.0");
        await SeedAssignmentAsync(device, module, version);

        var result = await _service.GetModuleAsync("detailed-mod");

        Assert.NotNull(result);
        Assert.Equal("detailed-mod", result.ModuleId);
        Assert.Single(result.Versions);
        Assert.Single(result.Assignments);
        Assert.Equal("dev-001", result.Assignments[0].DeviceId);
    }

    [Fact]
    public async Task GetModule_Nonexistent_ReturnsNull()
    {
        var result = await _service.GetModuleAsync("nonexistent");
        Assert.Null(result);
    }

    // ─── Helpers ─────────────────────────────────

    private async Task<DeviceRecord> SeedDeviceAsync(string deviceId)
    {
        var device = new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = deviceId,
            ApiKey = "test-key",
            Mode = "production",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.Devices.Add(device);
        await _db.SaveChangesAsync();
        return device;
    }

    private async Task<(ModuleDefinitionRecord Module, ModuleVersionRecord Version)> SeedModuleWithVersionAsync(
        string moduleId, string versionStr)
    {
        var module = new ModuleDefinitionRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = moduleId,
            DefaultEntrypoint = "run",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleDefinitions.Add(module);

        var version = new ModuleVersionRecord
        {
            Id = Guid.NewGuid(),
            ModuleDefinitionId = module.Id,
            Version = versionStr,
            PackageHash = "sha256:abc123",
            PackageSizeBytes = 100,
            CreatedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleVersions.Add(version);
        await _db.SaveChangesAsync();
        return (module, version);
    }

    private async Task<ModuleAssignmentRecord> SeedAssignmentAsync(
        DeviceRecord device, ModuleDefinitionRecord module, ModuleVersionRecord version)
    {
        var assignment = new ModuleAssignmentRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            ModuleDefinitionId = module.Id,
            ModuleVersionId = version.Id,
            IntervalMs = 60000,
            TimeoutMs = 5000,
            Entrypoint = "run",
            Enabled = true,
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleAssignments.Add(assignment);
        await _db.SaveChangesAsync();
        return assignment;
    }
}
