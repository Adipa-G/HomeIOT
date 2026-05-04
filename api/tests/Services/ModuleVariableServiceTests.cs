using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Services;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public class ModuleVariableServiceTests : IDisposable
{
    private readonly ApiDbContext _db;
    private readonly ModuleVariableService _service;

    public ModuleVariableServiceTests()
    {
        var options = new DbContextOptionsBuilder<ApiDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        _db = new ApiDbContext(options);
        _service = new ModuleVariableService(_db);
    }

    public void Dispose() => _db.Dispose();

    // ── helpers ──────────────────────────────────────────────────────────

    private async Task<ModuleDefinitionRecord> SeedModuleAsync(string moduleId = "mod-1")
    {
        var def = new ModuleDefinitionRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = moduleId,
            DefaultEntrypoint = "run",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleDefinitions.Add(def);
        await _db.SaveChangesAsync();
        return def;
    }

    private async Task<ModuleVariableDefRecord> SeedVarDefAsync(
        Guid moduleDefId, string name, string type = "string",
        string? defaultValue = null, string? serverCode = null)
    {
        var v = new ModuleVariableDefRecord
        {
            Id = Guid.NewGuid(),
            ModuleDefinitionId = moduleDefId,
            Name = name,
            Type = type,
            DefaultValue = defaultValue,
            ServerCode = serverCode,
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleVariableDefs.Add(v);
        await _db.SaveChangesAsync();
        return v;
    }

    private async Task<(ModuleDefinitionRecord def, ModuleAssignmentRecord assignment)> SeedAssignmentAsync(
        string moduleId = "mod-1", string deviceId = "dev-1")
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

        var def = new ModuleDefinitionRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = moduleId,
            DefaultEntrypoint = "run",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleDefinitions.Add(def);

        var version = new ModuleVersionRecord
        {
            Id = Guid.NewGuid(),
            ModuleDefinitionId = def.Id,
            Version = "1.0.0",
            PackageHash = "sha256:abc",
            PackageSizeBytes = 100,
            CreatedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleVersions.Add(version);

        var assignment = new ModuleAssignmentRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            ModuleDefinitionId = def.Id,
            ModuleVersionId = version.Id,
            IntervalMs = 60000,
            TimeoutMs = 10000,
            Entrypoint = "run",
            Enabled = true,
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleAssignments.Add(assignment);
        await _db.SaveChangesAsync();
        return (def, assignment);
    }

    // ── GetVariableDefs ───────────────────────────────────────────────────

    [Fact]
    public async Task GetVariableDefs_UnknownModule_ReturnsEmpty()
    {
        var result = await _service.GetVariableDefsAsync("no-such-module");
        Assert.Empty(result);
    }

    [Fact]
    public async Task GetVariableDefs_ModuleWithNoDefs_ReturnsEmpty()
    {
        await SeedModuleAsync("mod-empty");
        var result = await _service.GetVariableDefsAsync("mod-empty");
        Assert.Empty(result);
    }

    [Fact]
    public async Task GetVariableDefs_ReturnsDefs()
    {
        var def = await SeedModuleAsync("mod-x");
        await SeedVarDefAsync(def.Id, "threshold", "number", "10");
        await SeedVarDefAsync(def.Id, "label", "string", "hello");

        var result = await _service.GetVariableDefsAsync("mod-x");
        Assert.Equal(2, result.Count);
        Assert.Contains(result, v => v.Name == "threshold");
        Assert.Contains(result, v => v.Name == "label");
    }

    // ── UpsertVariableDef ─────────────────────────────────────────────────

    [Fact]
    public async Task UpsertVariableDef_UnknownModule_ReturnsNull()
    {
        var req = new UpsertVariableDefRequest { Type = "string", DefaultValue = "a" };
        var result = await _service.UpsertVariableDefAsync("no-module", "VAR", req);
        Assert.Null(result);
    }

    [Fact]
    public async Task UpsertVariableDef_CreateNew_ReturnsRecord()
    {
        await SeedModuleAsync("mod-y");
        var req = new UpsertVariableDefRequest { Type = "number", DefaultValue = "42" };

        var result = await _service.UpsertVariableDefAsync("mod-y", "LIMIT", req);

        Assert.NotNull(result);
        Assert.Equal("LIMIT", result!.Name);
        Assert.Equal("number", result.Type);
        Assert.Equal("42", result.DefaultValue);
    }

    [Fact]
    public async Task UpsertVariableDef_UpdateExisting_ChangesValues()
    {
        var def = await SeedModuleAsync("mod-z");
        await SeedVarDefAsync(def.Id, "FLAG", "boolean", "false");

        var req = new UpsertVariableDefRequest { Type = "boolean", DefaultValue = "true", Description = "updated" };
        var result = await _service.UpsertVariableDefAsync("mod-z", "FLAG", req);

        Assert.NotNull(result);
        Assert.Equal("true", result!.DefaultValue);
        Assert.Equal("updated", result.Description);

        // Confirm only one record exists in DB
        var count = await _db.ModuleVariableDefs.CountAsync(v => v.Name == "FLAG");
        Assert.Equal(1, count);
    }

    [Fact]
    public async Task UpsertVariableDef_InvalidType_DefaultsToString()
    {
        await SeedModuleAsync("mod-t");
        var req = new UpsertVariableDefRequest { Type = "unknowntype" };

        var result = await _service.UpsertVariableDefAsync("mod-t", "X", req);

        Assert.Equal("string", result!.Type);
    }

    // ── DeleteVariableDef ─────────────────────────────────────────────────

    [Fact]
    public async Task DeleteVariableDef_Existing_ReturnsTrue()
    {
        var def = await SeedModuleAsync("mod-d");
        await SeedVarDefAsync(def.Id, "MY_VAR");

        var ok = await _service.DeleteVariableDefAsync("mod-d", "MY_VAR");

        Assert.True(ok);
        Assert.Equal(0, await _db.ModuleVariableDefs.CountAsync(v => v.Name == "MY_VAR"));
    }

    [Fact]
    public async Task DeleteVariableDef_NotFound_ReturnsFalse()
    {
        await SeedModuleAsync("mod-e");
        var ok = await _service.DeleteVariableDefAsync("mod-e", "GHOST");
        Assert.False(ok);
    }

    // ── GetResolvedVariables (resolution priority) ────────────────────────

    [Fact]
    public async Task GetResolvedVariables_NoValues_UsesDefault()
    {
        var (def, assignment) = await SeedAssignmentAsync("mod-r", "dev-r");
        await SeedVarDefAsync(def.Id, "RATE", "number", "5");

        var result = await _service.GetResolvedVariablesAsync(assignment.Id);

        Assert.Equal("5", result["RATE"]);
    }

    [Fact]
    public async Task GetResolvedVariables_ManualOverride_WinsOverDefault()
    {
        var (def, assignment) = await SeedAssignmentAsync("mod-ov", "dev-ov");
        await SeedVarDefAsync(def.Id, "RATE", "number", "5");

        _db.ModuleVariableValues.Add(new ModuleVariableValueRecord
        {
            Id = Guid.NewGuid(),
            ModuleAssignmentId = assignment.Id,
            VariableName = "RATE",
            Value = "99",
            ComputedByServer = false,
        });
        await _db.SaveChangesAsync();

        var result = await _service.GetResolvedVariablesAsync(assignment.Id);

        Assert.Equal("99", result["RATE"]);
    }

    [Fact]
    public async Task GetResolvedVariables_ServerComputed_UsesComputedValue()
    {
        var (def, assignment) = await SeedAssignmentAsync("mod-sc", "dev-sc");
        await SeedVarDefAsync(def.Id, "RATE", "number", "5");

        _db.ModuleVariableValues.Add(new ModuleVariableValueRecord
        {
            Id = Guid.NewGuid(),
            ModuleAssignmentId = assignment.Id,
            VariableName = "RATE",
            Value = "77",
            ComputedByServer = true,
            LastComputedAtUtc = DateTimeOffset.UtcNow,
        });
        await _db.SaveChangesAsync();

        var result = await _service.GetResolvedVariablesAsync(assignment.Id);

        Assert.Equal("77", result["RATE"]);
    }

    // ── UpsertComputedValue – preserves manual override ───────────────────

    [Fact]
    public async Task UpsertComputedValue_ManualOverrideExists_IsNotOverwritten()
    {
        var (def, assignment) = await SeedAssignmentAsync("mod-co", "dev-co");
        await SeedVarDefAsync(def.Id, "RATE");

        // Seed a manual override
        _db.ModuleVariableValues.Add(new ModuleVariableValueRecord
        {
            Id = Guid.NewGuid(),
            ModuleAssignmentId = assignment.Id,
            VariableName = "RATE",
            Value = "manual",
            ComputedByServer = false,
        });
        await _db.SaveChangesAsync();

        await _service.UpsertComputedValueAsync(assignment.Id, "RATE", "server_value");

        var stored = await _db.ModuleVariableValues
            .FirstAsync(v => v.ModuleAssignmentId == assignment.Id && v.VariableName == "RATE");

        Assert.Equal("manual", stored.Value);
        Assert.False(stored.ComputedByServer);
    }

    [Fact]
    public async Task UpsertComputedValue_NoExistingValue_CreatesServerRecord()
    {
        var (def, assignment) = await SeedAssignmentAsync("mod-cv", "dev-cv");
        await SeedVarDefAsync(def.Id, "RATE");

        await _service.UpsertComputedValueAsync(assignment.Id, "RATE", "computed");

        var stored = await _db.ModuleVariableValues
            .FirstAsync(v => v.ModuleAssignmentId == assignment.Id && v.VariableName == "RATE");

        Assert.Equal("computed", stored.Value);
        Assert.True(stored.ComputedByServer);
    }

    [Fact]
    public async Task UpsertComputedValue_ExistingServerValue_UpdatesIt()
    {
        var (def, assignment) = await SeedAssignmentAsync("mod-cu", "dev-cu");
        await SeedVarDefAsync(def.Id, "RATE");

        _db.ModuleVariableValues.Add(new ModuleVariableValueRecord
        {
            Id = Guid.NewGuid(),
            ModuleAssignmentId = assignment.Id,
            VariableName = "RATE",
            Value = "old",
            ComputedByServer = true,
            LastComputedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-5),
        });
        await _db.SaveChangesAsync();

        await _service.UpsertComputedValueAsync(assignment.Id, "RATE", "new");

        var stored = await _db.ModuleVariableValues
            .FirstAsync(v => v.ModuleAssignmentId == assignment.Id && v.VariableName == "RATE");

        Assert.Equal("new", stored.Value);
        Assert.True(stored.ComputedByServer);
    }

    // ── SetVariableValue ──────────────────────────────────────────────────

    [Fact]
    public async Task SetVariableValue_ValidAssignmentAndVar_ReturnsTrue()
    {
        var (def, assignment) = await SeedAssignmentAsync("mod-sv", "dev-sv");
        await SeedVarDefAsync(def.Id, "LABEL", "string");

        var ok = await _service.SetVariableValueAsync(assignment.Id, "LABEL", "myvalue");

        Assert.True(ok);
        var stored = await _db.ModuleVariableValues.FirstAsync(v => v.VariableName == "LABEL");
        Assert.Equal("myvalue", stored.Value);
        Assert.False(stored.ComputedByServer);
    }

    [Fact]
    public async Task SetVariableValue_UnknownAssignment_ReturnsFalse()
    {
        var ok = await _service.SetVariableValueAsync(Guid.NewGuid(), "VAR", "x");
        Assert.False(ok);
    }

    [Fact]
    public async Task SetVariableValue_UnknownVariable_ReturnsFalse()
    {
        var (_, assignment) = await SeedAssignmentAsync("mod-sv2", "dev-sv2");
        var ok = await _service.SetVariableValueAsync(assignment.Id, "GHOST", "x");
        Assert.False(ok);
    }

    // ── DeleteVariableValue ───────────────────────────────────────────────

    [Fact]
    public async Task DeleteVariableValue_ExistingOverride_ReturnsTrue()
    {
        var (def, assignment) = await SeedAssignmentAsync("mod-dv", "dev-dv");
        await SeedVarDefAsync(def.Id, "X");

        _db.ModuleVariableValues.Add(new ModuleVariableValueRecord
        {
            Id = Guid.NewGuid(),
            ModuleAssignmentId = assignment.Id,
            VariableName = "X",
            Value = "val",
            ComputedByServer = false,
        });
        await _db.SaveChangesAsync();

        var ok = await _service.DeleteVariableValueAsync(assignment.Id, "X");

        Assert.True(ok);
        Assert.Equal(0, await _db.ModuleVariableValues.CountAsync(v => v.VariableName == "X"));
    }

    [Fact]
    public async Task DeleteVariableValue_NotFound_ReturnsFalse()
    {
        var (_, assignment) = await SeedAssignmentAsync("mod-dv2", "dev-dv2");
        var ok = await _service.DeleteVariableValueAsync(assignment.Id, "GHOST");
        Assert.False(ok);
    }
}
