using HomeIOT.Api.Configuration;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace HomeIOT.Api.Services;

public sealed class DevelopmentSeedService
{
    public const string DeviceId = "simulator-device-1";
    public const string DeviceApiKey = "your-api-key-here";
    public const string ModuleId = "demo-sensor";
    public const string ModuleVersion = "1.0.0";

    public static IReadOnlyList<(int Temperature, int Humidity, int LoadPercent)> ThresholdCoverageReadings { get; } =
        Array.AsReadOnly(new[]
        {
            (8, 15, 10),
            (20, 45, 45),
            (35, 70, 70),
            (45, 90, 90),
            (28, 55, 20),
            (32, 85, 85),
        });

    private static string ModuleCode => $$"""
        import time

        DEMO_READINGS = {{System.Text.Json.JsonSerializer.Serialize(ThresholdCoverageReadings.Select(reading => new
        {
            temperature = reading.Temperature,
            humidity = reading.Humidity,
            load_percent = reading.LoadPercent,
        }))}}

        def run(ctx):
            phase = int(time.time() / 10) % len(DEMO_READINGS)
            reading = DEMO_READINGS[phase]
            temperature = reading["temperature"]
            humidity = reading["humidity"]
            load_percent = reading["load_percent"]
            threshold = float(TEMP_THRESHOLD)
            alert_enabled = str(ALERT_ENABLED).lower() == "true"

            return {
                "temperature": round(temperature, 1),
                "humidity": humidity,
                "load_percent": load_percent,
                "status": "alert" if alert_enabled and temperature >= threshold else "normal",
                "location": LOCATION,
                "server_message": SERVER_MESSAGE,
            }
        """;

    private readonly ApiDbContext _db;
    private readonly IModuleService _moduleService;
    private readonly IModuleVariableService _variableService;
    private readonly IHostEnvironment _environment;
    private readonly DevelopmentSeedOptions _options;
    private readonly ILogger<DevelopmentSeedService> _logger;

    public DevelopmentSeedService(
        ApiDbContext db,
        IModuleService moduleService,
        IModuleVariableService variableService,
        IHostEnvironment environment,
        IOptions<DevelopmentSeedOptions> options,
        ILogger<DevelopmentSeedService> logger)
    {
        _db = db;
        _moduleService = moduleService;
        _variableService = variableService;
        _environment = environment;
        _options = options.Value;
        _logger = logger;
    }

    public async Task SeedIfEnabledAsync(CancellationToken ct = default)
    {
        if (!_environment.IsDevelopment() || !_options.Enabled)
            return;

        await EnsureDeviceAsync(ct);
        var module = await EnsureModuleAsync(ct);
        await EnsureAssignmentAsync(module, ct);
        await EnsureVariablesAsync(ct);
        await EnsureVisualizationsAsync(ct);

        _logger.LogInformation("Development simulator seed is ready for device {DeviceId}", DeviceId);
    }

    private async Task EnsureDeviceAsync(CancellationToken ct)
    {
        var device = await _db.Devices.FirstOrDefaultAsync(d => d.DeviceId == DeviceId, ct);
        if (device is not null)
            return;

        var now = DateTimeOffset.UtcNow;
        _db.Devices.Add(new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = DeviceId,
            ApiKey = DeviceApiKey,
            Platform = "simulator",
            Version = "1.0.0",
            Mode = "development",
            CreatedAtUtc = now,
            UpdatedAtUtc = now,
        });
        await _db.SaveChangesAsync(ct);
    }

    private async Task<ModuleDefinitionRecord> EnsureModuleAsync(CancellationToken ct)
    {
        var module = await _db.ModuleDefinitions.FirstOrDefaultAsync(m => m.ModuleId == ModuleId, ct);
        if (module is null)
        {
            module = await _moduleService.CreateModuleAsync(new CreateModuleRequest
            {
                ModuleId = ModuleId,
                Description = "Development simulator readings with varied visualization examples.",
                DefaultEntrypoint = "run",
            }, ct);
        }

        var versionExists = await _db.ModuleVersions.AnyAsync(
            v => v.ModuleDefinitionId == module.Id && v.Version == ModuleVersion, ct);
        if (!versionExists || _moduleService.GetPackage(ModuleId, ModuleVersion) is null)
        {
            await using var content = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(ModuleCode));
            await _moduleService.UploadVersionAsync(ModuleId, ModuleVersion, content, ct);
        }

        return module;
    }

    private async Task EnsureAssignmentAsync(ModuleDefinitionRecord module, CancellationToken ct)
    {
        var device = await _db.Devices.FirstAsync(d => d.DeviceId == DeviceId, ct);
        var assignment = await _db.ModuleAssignments.FirstOrDefaultAsync(
            a => a.DeviceRecordId == device.Id && a.ModuleDefinitionId == module.Id, ct);
        if (assignment is not null)
            return;

        assignment = await _moduleService.AssignModuleAsync(ModuleId, new AssignModuleRequest
        {
            DeviceId = DeviceId,
            Version = ModuleVersion,
            IntervalMs = 10000,
            TimeoutMs = 5000,
            Enabled = true,
        }, ct);
        if (assignment is null)
            throw new InvalidOperationException($"Could not assign development module {ModuleId}.");

        assignment.ShowInDashboard = true;
        await _db.SaveChangesAsync(ct);
    }

    private async Task EnsureVariablesAsync(CancellationToken ct)
    {
        await EnsureVariableAsync("SENSOR_OUTPUT", new UpsertVariableDefRequest
        {
            Type = "json",
            Description = "Structured sensor readings returned by the simulator module.",
        }, ct);

        await EnsureVariableAsync("TEMP_THRESHOLD", new UpsertVariableDefRequest
        {
            Type = "number",
            DefaultValue = "28",
            Description = "Temperature threshold used to flag a reading.",
            ControlType = "slider",
            ControlOptions = new { min = 15, max = 40, step = 0.5 },
        }, ct);

        await EnsureVariableAsync("ALERT_ENABLED", new UpsertVariableDefRequest
        {
            Type = "boolean",
            DefaultValue = "true",
            Description = "Whether the demo module reports threshold alerts.",
            ControlType = "toggle",
        }, ct);

        await EnsureVariableAsync("LOCATION", new UpsertVariableDefRequest
        {
            Type = "string",
            DefaultValue = "Living room",
            Description = "Friendly location label for the simulated sensor.",
            ControlType = "dropdown",
            ControlOptions = new[] { "Living room", "Office", "Workshop" },
        }, ct);

        await EnsureVariableAsync("SERVER_MESSAGE", new UpsertVariableDefRequest
        {
            Type = "string",
            DefaultValue = "Waiting for server computation",
            Description = "A value computed by the API and injected into the module.",
            ServerCode = "\"API computed at \" + DateTimeOffset.UtcNow.ToString(\"HH:mm:ss\")",
            ControlType = "dropdown",
            ControlOptions = new[] { "API computed value" },
        }, ct);
    }

    private async Task EnsureVariableAsync(string name, UpsertVariableDefRequest request, CancellationToken ct)
    {
        var exists = await _db.ModuleVariableDefs
            .AnyAsync(v => v.ModuleDefinition.ModuleId == ModuleId && v.Name == name, ct);
        if (!exists)
            await _variableService.UpsertVariableDefAsync(ModuleId, name, request, ct);
    }

    private async Task EnsureVisualizationsAsync(CancellationToken ct)
    {
        var visualizations = new (string Path, string Name, string Type, object Config)[]
        {
            ("temperature", "Temperature gauge", "gauge", new { min = 0, max = 50, unit = "°C", decimals = 1, thresholds = new[] { new { value = 15, color = "#10b981" }, new { value = 30, color = "#fbbf24" }, new { value = 40, color = "#ef4444" } } }),
            ("humidity", "Humidity progress", "progress_bar", new { min = 0, max = 100, unit = "%", decimals = 0, thresholds = new[] { new { value = 30, color = "#10b981" }, new { value = 60, color = "#fbbf24" }, new { value = 80, color = "#ef4444" } } }),
            ("load_percent", "Simulated load", "number_display", new { min = 0, max = 100, unit = "%", decimals = 0, thresholds = new[] { new { value = 25, color = "#10b981" }, new { value = 60, color = "#fbbf24" }, new { value = 85, color = "#ef4444" } } }),
            ("status", "Sensor status", "text_display", new { }),
            ("load_percent", "Load band (text)", "text_display", new { min = 0, max = 100, unit = "%", decimals = 0, thresholds = new[] { new { value = 25, color = "#10b981" }, new { value = 60, color = "#fbbf24" }, new { value = 85, color = "#ef4444" } } }),
            ("humidity", "Humidity history", "bar_chart", new { min = 0, max = 100, unit = "%", decimals = 0, historyPoints = 12, thresholds = new[] { new { value = 30, color = "#10b981" }, new { value = 60, color = "#fbbf24" }, new { value = 80, color = "#ef4444" } } }),
            ("temperature", "Temperature trend", "line_chart", new { min = 0, max = 50, unit = "°C", decimals = 1, historyPoints = 12, thresholds = new[] { new { value = 15, color = "#10b981" }, new { value = 30, color = "#fbbf24" }, new { value = 40, color = "#ef4444" } } }),
        };

        foreach (var visualization in visualizations)
        {
            var existing = await _db.ModuleVariableVisualizations.AnyAsync(
                v => v.ModuleVariableDef.ModuleDefinition.ModuleId == ModuleId &&
                     v.ModuleVariableDef.Name == "SENSOR_OUTPUT" &&
                     v.JsonPath == visualization.Path &&
                     v.VisualizationType == visualization.Type, ct);
            if (existing)
                continue;

            await _variableService.UpsertVisualizationAsync(
                ModuleId,
                "SENSOR_OUTPUT",
                "new",
                new UpsertModuleVariableVisualizationRequest(
                    visualization.Path,
                    visualization.Name,
                    visualization.Type,
                    visualization.Config),
                ct);
        }
    }
}