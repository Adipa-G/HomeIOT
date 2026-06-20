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
        string? defaultValue = null, string? serverCode = null, string? controlType = null)
    {
        var v = new ModuleVariableDefRecord
        {
            Id = Guid.NewGuid(),
            ModuleDefinitionId = moduleDefId,
            Name = name,
            Type = type,
            DefaultValue = defaultValue,
            ServerCode = serverCode,
            ControlType = controlType,
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

    // ── GetVisualizationsForVariable ──────────────────────────────────────

    [Fact]
    public async Task GetVisualizations_UnknownModule_ReturnsEmpty()
    {
        var result = await _service.GetVisualizationsForVariableAsync("no-module", "temp");
        Assert.Empty(result);
    }

    [Fact]
    public async Task GetVisualizations_UnknownVariable_ReturnsEmpty()
    {
        await SeedModuleAsync("mod-viz");
        var result = await _service.GetVisualizationsForVariableAsync("mod-viz", "unknown");
        Assert.Empty(result);
    }

    [Fact]
    public async Task GetVisualizations_ReturnsOrderedByDisplayName()
    {
        var def = await SeedModuleAsync("mod-viz2");
        var varDef = await SeedVarDefAsync(def.Id, "temp", "number");

        // Seed visualizations in non-alphabetical order
        _db.ModuleVariableVisualizations.Add(new ModuleVariableVisualizationRecord
        {
            Id = Guid.NewGuid(),
            ModuleVariableDefId = varDef.Id,
            JsonPath = "temp",
            DisplayName = "Zebra",
            VisualizationType = "gauge",
            VisualizationConfig = null,
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        });
        _db.ModuleVariableVisualizations.Add(new ModuleVariableVisualizationRecord
        {
            Id = Guid.NewGuid(),
            ModuleVariableDefId = varDef.Id,
            JsonPath = "temp",
            DisplayName = "Apple",
            VisualizationType = "gauge",
            VisualizationConfig = null,
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        });
        await _db.SaveChangesAsync();

        var result = await _service.GetVisualizationsForVariableAsync("mod-viz2", "temp");

        Assert.Equal(2, result.Count);
        Assert.Equal("Apple", result[0].DisplayName);
        Assert.Equal("Zebra", result[1].DisplayName);
    }

    // ── UpsertVisualization ───────────────────────────────────────────────

    [Fact]
    public async Task UpsertVisualization_UnknownModule_ReturnsNull()
    {
        var req = new UpsertModuleVariableVisualizationRequest(
            "temp",
            "Temp Gauge",
            "gauge",
            new { min = 0, max = 100 }
        );
        var result = await _service.UpsertVisualizationAsync("no-module", "temp", "new", req);
        Assert.Null(result);
    }

    [Fact]
    public async Task UpsertVisualization_UnknownVariable_ReturnsNull()
    {
        await SeedModuleAsync("mod-viz3");
        var req = new UpsertModuleVariableVisualizationRequest(
            "temp",
            "Temp",
            "gauge",
            null
        );
        var result = await _service.UpsertVisualizationAsync("mod-viz3", "unknown", "new", req);
        Assert.Null(result);
    }

    [Fact]
    public async Task UpsertVisualization_CreateNew_ReturnsRecord()
    {
        var def = await SeedModuleAsync("mod-viz4");
        await SeedVarDefAsync(def.Id, "temperature", "number");

        var req = new UpsertModuleVariableVisualizationRequest(
            "temperature",
            "Temperature Gauge",
            "gauge",
            new { min = 0, max = 100, unit = "°C" }
        );

        var result = await _service.UpsertVisualizationAsync("mod-viz4", "temperature", "new", req);

        Assert.NotNull(result);
        Assert.Equal("temperature", result!.JsonPath);
        Assert.Equal("Temperature Gauge", result.DisplayName);
        Assert.Equal("gauge", result.VisualizationType);
        Assert.NotNull(result.VisualizationConfig);
    }

    [Fact]
    public async Task UpsertVisualization_UpdateExisting_ChangesValues()
    {
        var def = await SeedModuleAsync("mod-viz5");
        var varDef = await SeedVarDefAsync(def.Id, "temp", "number");

        var vizId = Guid.NewGuid();
        _db.ModuleVariableVisualizations.Add(new ModuleVariableVisualizationRecord
        {
            Id = vizId,
            ModuleVariableDefId = varDef.Id,
            JsonPath = "temp",
            DisplayName = "Old Name",
            VisualizationType = "gauge",
            VisualizationConfig = null,
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        });
        await _db.SaveChangesAsync();

        var req = new UpsertModuleVariableVisualizationRequest(
            "temperature.current",
            "Updated Name",
            "line_chart",
            new { historyPoints = 5 }
        );

        var result = await _service.UpsertVisualizationAsync("mod-viz5", "temp", vizId.ToString(), req);

        Assert.NotNull(result);
        Assert.Equal("temperature.current", result!.JsonPath);
        Assert.Equal("Updated Name", result.DisplayName);
        Assert.Equal("line_chart", result.VisualizationType);

        // Verify only one record exists
        var count = await _db.ModuleVariableVisualizations.CountAsync();
        Assert.Equal(1, count);
    }

    // ── DeleteVisualization ───────────────────────────────────────────────

    [Fact]
    public async Task DeleteVisualization_Existing_ReturnsTrue()
    {
        var def = await SeedModuleAsync("mod-del");
        var varDef = await SeedVarDefAsync(def.Id, "temp");
        var vizId = Guid.NewGuid();

        _db.ModuleVariableVisualizations.Add(new ModuleVariableVisualizationRecord
        {
            Id = vizId,
            ModuleVariableDefId = varDef.Id,
            JsonPath = "temp",
            DisplayName = "Temp",
            VisualizationType = "gauge",
            VisualizationConfig = null,
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        });
        await _db.SaveChangesAsync();

        var ok = await _service.DeleteVisualizationAsync("mod-del", "temp", vizId);

        Assert.True(ok);
        Assert.Equal(0, await _db.ModuleVariableVisualizations.CountAsync());
    }

    [Fact]
    public async Task DeleteVisualization_UnknownModule_ReturnsFalse()
    {
        var ok = await _service.DeleteVisualizationAsync("no-module", "temp", Guid.NewGuid());
        Assert.False(ok);
    }

    [Fact]
    public async Task DeleteVisualization_UnknownVariable_ReturnsFalse()
    {
        await SeedModuleAsync("mod-del2");
        var ok = await _service.DeleteVisualizationAsync("mod-del2", "unknown", Guid.NewGuid());
        Assert.False(ok);
    }

    [Fact]
    public async Task DeleteVisualization_UnknownVisualization_ReturnsFalse()
    {
        var def = await SeedModuleAsync("mod-del3");
        await SeedVarDefAsync(def.Id, "temp");
        var ok = await _service.DeleteVisualizationAsync("mod-del3", "temp", Guid.NewGuid());
        Assert.False(ok);
    }

    // ── InferJsonSchema ───────────────────────────────────────────────────

    [Fact]
    public async Task InferJsonSchema_UnknownModule_ReturnsNull()
    {
        var result = await _service.InferJsonSchemaAsync("no-module", "temp");
        Assert.Null(result);
    }

    [Fact]
    public async Task InferJsonSchema_UnknownVariable_ReturnsNull()
    {
        await SeedModuleAsync("mod-schema");
        var result = await _service.InferJsonSchemaAsync("mod-schema", "unknown");
        Assert.Null(result);
    }

    [Fact]
    public async Task InferJsonSchema_NoModuleResults_ReturnsNull()
    {
        var def = await SeedModuleAsync("mod-schema2");
        await SeedVarDefAsync(def.Id, "temp", "number");

        var result = await _service.InferJsonSchemaAsync("mod-schema2", "temp");

        Assert.Null(result);
    }

    [Fact]
    public async Task InferJsonSchema_WithModuleResult_InfersSchema()
    {
        var def = await SeedModuleAsync("mod-schema3");
        await SeedVarDefAsync(def.Id, "sensor", "json");

        // Add module result with output data (OUTPUT variable since ControlType is null)
        // The inferred schema should be the schema of the entire output, not just the variable's value
        var moduleResult = new ModuleResultRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = "mod-schema3",
            ModuleVersion = "1.0.0",
            DeviceId = "dev-1",
            RunId = "run-1",
            Status = "success",
            ElapsedMs = 100,
            ErrorMessage = null,
            Output = System.Text.Json.JsonSerializer.Serialize(new { sensor = new { temperature = 25.5, humidity = 60 } }),
            VariableValues = null,
            StartedAtUtc = DateTimeOffset.UtcNow,
            FinishedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleResults.Add(moduleResult);
        await _db.SaveChangesAsync();

        var result = await _service.InferJsonSchemaAsync("mod-schema3", "sensor");

        Assert.NotNull(result);
        // Verify the schema is an object with the full output structure
        Assert.True(result is Dictionary<string, object>);
        var schemaDict = (Dictionary<string, object>)result;
        Assert.Contains("sensor", schemaDict.Keys);
        
        // Verify the variable def was updated with the inferred schema
        var updatedVarDef = await _db.ModuleVariableDefs.FirstAsync(v => v.Name == "sensor");
        Assert.NotNull(updatedVarDef.InferredJsonSchema);
    }

    [Fact]
    public async Task InferJsonSchema_OutputVariable_InferrsFullOutputStructure()
    {
        var def = await SeedModuleAsync("mod-schema-full");
        await SeedVarDefAsync(def.Id, "result", "json"); // OUTPUT variable (no control_type)

        // Create output with multiple fields
        var moduleResult = new ModuleResultRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = "mod-schema-full",
            ModuleVersion = "1.0.0",
            DeviceId = "dev-1",
            RunId = "run-1",
            Status = "success",
            ElapsedMs = 100,
            ErrorMessage = null,
            Output = System.Text.Json.JsonSerializer.Serialize(new
            {
                temp = 25.5,
                status = "ok",
                humidity = 60
            }),
            VariableValues = null,
            StartedAtUtc = DateTimeOffset.UtcNow,
            FinishedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleResults.Add(moduleResult);
        await _db.SaveChangesAsync();

        var result = await _service.InferJsonSchemaAsync("mod-schema-full", "result");

        Assert.NotNull(result);
        Assert.True(result is Dictionary<string, object>);
        var schemaDict = (Dictionary<string, object>)result;
        // Should have all fields from the output
        Assert.Contains("temp", schemaDict.Keys);
        Assert.Contains("status", schemaDict.Keys);
        Assert.Contains("humidity", schemaDict.Keys);
        // Verify types
        Assert.Equal("number", schemaDict["temp"]);
        Assert.Equal("string", schemaDict["status"]);
        Assert.Equal("number", schemaDict["humidity"]);
    }

    [Fact]
    public async Task InferJsonSchema_InputVariable_InfersFromVariableValues()
    {
        var def = await SeedModuleAsync("mod-schema-input");
        await SeedVarDefAsync(def.Id, "threshold", "number", null, null, "text"); // INPUT variable (has control_type)

        // Create result with variable values (configuration)
        var moduleResult = new ModuleResultRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = "mod-schema-input",
            ModuleVersion = "1.0.0",
            DeviceId = "dev-1",
            RunId = "run-1",
            Status = "success",
            ElapsedMs = 100,
            ErrorMessage = null,
            Output = null,
            VariableValues = System.Text.Json.JsonSerializer.Serialize(new { threshold = 50 }),
            StartedAtUtc = DateTimeOffset.UtcNow,
            FinishedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleResults.Add(moduleResult);
        await _db.SaveChangesAsync();

        var result = await _service.InferJsonSchemaAsync("mod-schema-input", "threshold");

        Assert.NotNull(result);
        Assert.Equal("number", result);
    }

    [Fact]
    public async Task InferJsonSchema_NestedObject_InfersNestedStructure()
    {
        var def = await SeedModuleAsync("mod-schema-nested");
        await SeedVarDefAsync(def.Id, "data", "json");

        var moduleResult = new ModuleResultRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = "mod-schema-nested",
            ModuleVersion = "1.0.0",
            DeviceId = "dev-1",
            RunId = "run-1",
            Status = "success",
            ElapsedMs = 100,
            ErrorMessage = null,
            Output = System.Text.Json.JsonSerializer.Serialize(new
            {
                sensors = new
                {
                    temperature = 22.5,
                    location = "room1"
                },
                metadata = new
                {
                    timestamp = "2026-06-21T00:00:00Z"
                }
            }),
            VariableValues = null,
            StartedAtUtc = DateTimeOffset.UtcNow,
            FinishedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleResults.Add(moduleResult);
        await _db.SaveChangesAsync();

        var result = await _service.InferJsonSchemaAsync("mod-schema-nested", "data");

        Assert.NotNull(result);
        Assert.True(result is Dictionary<string, object>);
        var schemaDict = (Dictionary<string, object>)result;
        Assert.Contains("sensors", schemaDict.Keys);
        Assert.Contains("metadata", schemaDict.Keys);
        
        // Verify nested structures are inferred
        Assert.True(schemaDict["sensors"] is Dictionary<string, object>);
        var sensorsSchema = (Dictionary<string, object>)schemaDict["sensors"];
        Assert.Contains("temperature", sensorsSchema.Keys);
        Assert.Contains("location", sensorsSchema.Keys);
    }

    [Fact]
    public async Task InferJsonSchema_WithArrayField_InfersArrayType()
    {
        var def = await SeedModuleAsync("mod-schema-array");
        await SeedVarDefAsync(def.Id, "readings", "json");

        var moduleResult = new ModuleResultRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = "mod-schema-array",
            ModuleVersion = "1.0.0",
            DeviceId = "dev-1",
            RunId = "run-1",
            Status = "success",
            ElapsedMs = 100,
            ErrorMessage = null,
            Output = System.Text.Json.JsonSerializer.Serialize(new
            {
                values = new int[] { 1, 2, 3, 4, 5 },
                status = "ok"
            }),
            VariableValues = null,
            StartedAtUtc = DateTimeOffset.UtcNow,
            FinishedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleResults.Add(moduleResult);
        await _db.SaveChangesAsync();

        var result = await _service.InferJsonSchemaAsync("mod-schema-array", "readings");

        Assert.NotNull(result);
        Assert.True(result is Dictionary<string, object>);
        var schemaDict = (Dictionary<string, object>)result;
        Assert.Equal("array", schemaDict["values"]);
        Assert.Equal("string", schemaDict["status"]);
    }

    [Fact]
    public async Task InferJsonSchema_NoRecentExecution_ReturnsNull()
    {
        var def = await SeedModuleAsync("mod-schema-no-exec");
        await SeedVarDefAsync(def.Id, "result", "json");

        // No module result created

        var result = await _service.InferJsonSchemaAsync("mod-schema-no-exec", "result");

        Assert.Null(result);
    }

    [Fact]
    public async Task InferJsonSchema_EmptyOutput_ReturnsNull()
    {
        var def = await SeedModuleAsync("mod-schema-empty");
        await SeedVarDefAsync(def.Id, "result", "json");

        var moduleResult = new ModuleResultRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = "mod-schema-empty",
            ModuleVersion = "1.0.0",
            DeviceId = "dev-1",
            RunId = "run-1",
            Status = "success",
            ElapsedMs = 100,
            ErrorMessage = null,
            Output = System.Text.Json.JsonSerializer.Serialize(new { }),
            VariableValues = null,
            StartedAtUtc = DateTimeOffset.UtcNow,
            FinishedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleResults.Add(moduleResult);
        await _db.SaveChangesAsync();

        var result = await _service.InferJsonSchemaAsync("mod-schema-empty", "result");

        Assert.Null(result);
    }

    [Fact]
    public async Task InferJsonSchema_InvalidJson_ReturnsNull()
    {
        var def = await SeedModuleAsync("mod-schema-invalid");
        await SeedVarDefAsync(def.Id, "result", "json");

        var moduleResult = new ModuleResultRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = "mod-schema-invalid",
            ModuleVersion = "1.0.0",
            DeviceId = "dev-1",
            RunId = "run-1",
            Status = "success",
            ElapsedMs = 100,
            ErrorMessage = null,
            Output = "not-valid-json",
            VariableValues = null,
            StartedAtUtc = DateTimeOffset.UtcNow,
            FinishedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleResults.Add(moduleResult);
        await _db.SaveChangesAsync();

        var result = await _service.InferJsonSchemaAsync("mod-schema-invalid", "result");

        Assert.Null(result);
    }

    [Fact]
    public async Task InferJsonSchema_UpdatesDatabase()
    {
        var def = await SeedModuleAsync("mod-schema-db");
        var varDef = await SeedVarDefAsync(def.Id, "result", "json");
        Assert.Null(varDef.InferredJsonSchema);

        var moduleResult = new ModuleResultRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = "mod-schema-db",
            ModuleVersion = "1.0.0",
            DeviceId = "dev-1",
            RunId = "run-1",
            Status = "success",
            ElapsedMs = 100,
            ErrorMessage = null,
            Output = System.Text.Json.JsonSerializer.Serialize(new { value = 42 }),
            VariableValues = null,
            StartedAtUtc = DateTimeOffset.UtcNow,
            FinishedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.ModuleResults.Add(moduleResult);
        await _db.SaveChangesAsync();

        await _service.InferJsonSchemaAsync("mod-schema-db", "result");

        var updatedVarDef = await _db.ModuleVariableDefs.FirstAsync(v => v.Id == varDef.Id);
        Assert.NotNull(updatedVarDef.InferredJsonSchema);
        Assert.Contains("value", updatedVarDef.InferredJsonSchema);
    }
}
