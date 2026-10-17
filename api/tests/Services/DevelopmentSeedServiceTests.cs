using HomeIOT.Api.Configuration;
using HomeIOT.Api.Data;
using HomeIOT.Api.Infrastructure;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Moq;
using System.Text;
using System.Text.Json;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public sealed class DevelopmentSeedServiceTests
{
    [Theory]
    [InlineData("Development", false)]
    [InlineData("Production", true)]
    public async Task SeedIfEnabledAsync_DoesNothingUnlessEnabledInDevelopment(string environmentName, bool enabled)
    {
        await using var harness = await SeedHarness.CreateAsync(environmentName, enabled);

        await harness.SeedService.SeedIfEnabledAsync();

        Assert.Empty(await harness.Db.Devices.ToListAsync());
        Assert.Empty(await harness.Db.ModuleDefinitions.ToListAsync());
    }

    [Fact]
    public async Task SeedIfEnabledAsync_CreatesSimulatorDatasetAndAllVisualizationTypes()
    {
        await using var harness = await SeedHarness.CreateAsync("Development", true);

        await harness.SeedService.SeedIfEnabledAsync();

        var device = await harness.Db.Devices.SingleAsync();
        Assert.Equal(DevelopmentSeedService.DeviceId, device.DeviceId);
        Assert.Equal(DeviceApiKeyHasher.Hash(DevelopmentSeedService.DeviceApiKey), device.ApiKeyHash);
        Assert.True(DeviceApiKeyHasher.Verify(DevelopmentSeedService.DeviceApiKey, device.ApiKeyHash));
        Assert.Equal("development", device.Mode);

        var assignment = await harness.Db.ModuleAssignments.SingleAsync();
        Assert.True(assignment.Enabled);
        Assert.True(assignment.ShowInDashboard);

        var variables = await harness.Db.ModuleVariableDefs
            .Where(v => v.ModuleDefinition.ModuleId == DevelopmentSeedService.ModuleId)
            .ToListAsync();
        Assert.Contains(variables, v => v.Type == "string");
        Assert.Contains(variables, v => v.Type == "number");
        Assert.Contains(variables, v => v.Type == "boolean");
        Assert.Contains(variables, v => v.Type == "json");
        Assert.Contains(variables, v => v.Name == "SERVER_MESSAGE" && v.ServerCode != null);

        var visualizations = await harness.Db.ModuleVariableVisualizations.ToListAsync();
        Assert.Equal(7, visualizations.Count);
        Assert.Equal(
            new[] { "bar_chart", "gauge", "line_chart", "number_display", "progress_bar", "text_display" },
            visualizations.Select(v => v.VisualizationType).Distinct().OrderBy(type => type).ToArray());
        var package = harness.ModuleService.GetPackage(DevelopmentSeedService.ModuleId, DevelopmentSeedService.ModuleVersion);
        Assert.NotNull(package);
        var expectedReadings = JsonSerializer.Serialize(DevelopmentSeedService.ThresholdCoverageReadings.Select(reading => new
        {
            temperature = reading.Temperature,
            humidity = reading.Humidity,
            load_percent = reading.LoadPercent,
        }));
        Assert.Contains(expectedReadings, Encoding.UTF8.GetString(package));

        var readingsByPath = new Dictionary<string, int[]>(StringComparer.Ordinal)
        {
            ["temperature"] = DevelopmentSeedService.ThresholdCoverageReadings.Select(reading => reading.Temperature).ToArray(),
            ["humidity"] = DevelopmentSeedService.ThresholdCoverageReadings.Select(reading => reading.Humidity).ToArray(),
            ["load_percent"] = DevelopmentSeedService.ThresholdCoverageReadings.Select(reading => reading.LoadPercent).ToArray(),
        };
        foreach (var visualization in visualizations.Where(visualization => visualization.JsonPath != "status"))
        {
            using var config = JsonDocument.Parse(visualization.VisualizationConfig!);
            var thresholds = config.RootElement.GetProperty("thresholds").EnumerateArray()
                .Select(threshold => (Value: threshold.GetProperty("value").GetInt32(), Color: threshold.GetProperty("color").GetString()!))
                .OrderBy(threshold => threshold.Value)
                .ToArray();

            var expectedColors = thresholds.Select(threshold => threshold.Color)
                .Append("#3b82f6")
                .ToHashSet(StringComparer.OrdinalIgnoreCase);
            var generatedColors = readingsByPath[visualization.JsonPath].Select(value =>
                thresholds.LastOrDefault(threshold => value >= threshold.Value).Color ?? "#3b82f6")
                .ToHashSet(StringComparer.OrdinalIgnoreCase);

            Assert.Subset(expectedColors, generatedColors);
        }

        var serverCodeService = new ModuleServerCodeService(
            harness.Db,
            new ModuleVariableService(harness.Db),
            NullLogger<ModuleServerCodeService>.Instance);
        await serverCodeService.RunForModuleAsync(DevelopmentSeedService.DeviceId, DevelopmentSeedService.ModuleId);

        var computedValue = await harness.Db.ModuleVariableValues.SingleAsync(v => v.VariableName == "SERVER_MESSAGE");
        Assert.True(computedValue.ComputedByServer);
        Assert.StartsWith("API computed at ", computedValue.Value);
    }

    [Fact]
    public async Task SeedIfEnabledAsync_RerunPreservesEditsAndRestoresMissingSeedVisualization()
    {
        await using var harness = await SeedHarness.CreateAsync("Development", true);
        await harness.SeedService.SeedIfEnabledAsync();

        var device = await harness.Db.Devices.SingleAsync();
        device.ApiKeyHash = "user-customized-key";
        var assignment = await harness.Db.ModuleAssignments.SingleAsync();
        assignment.IntervalMs = 45000;
        var module = await harness.Db.ModuleDefinitions.SingleAsync();
        module.Description = "User customized description";
        var gauge = await harness.Db.ModuleVariableVisualizations.SingleAsync(v => v.DisplayName == "Temperature gauge");
        gauge.DisplayName = "My temperature gauge";
        var missingVisualization = await harness.Db.ModuleVariableVisualizations.SingleAsync(v => v.DisplayName == "Sensor status");
        harness.Db.ModuleVariableVisualizations.Remove(missingVisualization);
        await harness.Db.SaveChangesAsync();

        await harness.SeedService.SeedIfEnabledAsync();

        Assert.Equal("user-customized-key", (await harness.Db.Devices.SingleAsync()).ApiKeyHash);
        Assert.Equal(45000, (await harness.Db.ModuleAssignments.SingleAsync()).IntervalMs);
        Assert.Equal("User customized description", (await harness.Db.ModuleDefinitions.SingleAsync()).Description);
        var visualizations = await harness.Db.ModuleVariableVisualizations.ToListAsync();
        Assert.Contains(visualizations, v => v.DisplayName == "My temperature gauge");
        Assert.Contains(visualizations, v => v.DisplayName == "Sensor status");
        Assert.Equal(7, visualizations.Count);
        Assert.Single(await harness.Db.Devices.ToListAsync());
        Assert.Single(await harness.Db.ModuleAssignments.ToListAsync());
    }

    private sealed class SeedHarness : IAsyncDisposable
    {
        private readonly SqliteConnection _connection;
        private readonly string _root;
        public ApiDbContext Db { get; }
        public DevelopmentSeedService SeedService { get; }
        public IModuleService ModuleService { get; }

        private SeedHarness(SqliteConnection connection, string root, ApiDbContext db, DevelopmentSeedService seedService, IModuleService moduleService)
        {
            _connection = connection;
            _root = root;
            Db = db;
            SeedService = seedService;
            ModuleService = moduleService;
        }

        public static async Task<SeedHarness> CreateAsync(string environmentName, bool enabled)
        {
            var connection = new SqliteConnection("Data Source=:memory:");
            await connection.OpenAsync();
            var db = new ApiDbContext(new DbContextOptionsBuilder<ApiDbContext>().UseSqlite(connection).Options);
            await db.Database.EnsureCreatedAsync();

            var root = Path.Combine(Path.GetTempPath(), $"homeiot-dev-seed-{Guid.NewGuid():N}");
            Directory.CreateDirectory(root);
            var environment = new Mock<IWebHostEnvironment>();
            environment.SetupGet(e => e.EnvironmentName).Returns(environmentName);
            environment.SetupGet(e => e.ContentRootPath).Returns(root);

            var variableService = new ModuleVariableService(db);
            var moduleService = new ModuleService(
                db,
                Options.Create(new ModuleStorageOptions { PackageRoot = "modules" }),
                environment.Object,
                NullLogger<ModuleService>.Instance,
                variableService);
            var seedService = new DevelopmentSeedService(
                db,
                moduleService,
                variableService,
                environment.Object,
                Options.Create(new DevelopmentSeedOptions { Enabled = enabled }),
                NullLogger<DevelopmentSeedService>.Instance);

            return new SeedHarness(connection, root, db, seedService, moduleService);
        }

        public async ValueTask DisposeAsync()
        {
            await Db.DisposeAsync();
            await _connection.DisposeAsync();
            if (Directory.Exists(_root))
                Directory.Delete(_root, recursive: true);
        }
    }

}