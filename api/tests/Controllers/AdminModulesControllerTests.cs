using HomeIOT.Api.Controllers;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class AdminModulesControllerTests
{
    private readonly Mock<IModuleService> _mockService;
    private readonly Mock<IModuleVariableService> _mockVariableService;
    private readonly Mock<IModuleTemplateService> _mockTemplateService;
    private readonly AdminModulesController _controller;

    public AdminModulesControllerTests()
    {
        _mockService = new Mock<IModuleService>();
        _mockVariableService = new Mock<IModuleVariableService>();
        _mockTemplateService = new Mock<IModuleTemplateService>();
        _controller = new AdminModulesController(_mockService.Object, _mockVariableService.Object, _mockTemplateService.Object)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext(),
            },
        };
    }

    [Fact]
    public async Task GetTemplates_ReturnsOkWithTemplates_FromTemplateService()
    {
        var templates = new List<ModuleTemplateItem>
        {
            new(
                Id: "read-digital-pin",
                Name: "Read a digital pin",
                Description: "Read a button or switch.",
                SetupGuide: "Add a variable named value.",
                Variants: new List<ModuleTemplateVariantItem>
                {
                    new("esp32", "from machine import Pin"),
                }),
        };

        _mockTemplateService.Setup(s => s.GetTemplatesAsync(It.IsAny<CancellationToken>())).ReturnsAsync(templates);

        var result = await _controller.GetTemplates(CancellationToken.None);

        var okResult = Assert.IsType<OkObjectResult>(result.Result);
        var returned = Assert.IsType<List<ModuleTemplateItem>>(okResult.Value);
        Assert.Single(returned);
        Assert.Equal("read-digital-pin", returned[0].Id);
    }

    [Fact]
    public async Task ListModules_ReturnsOkWithModules()
    {
        var moduleListItems = new List<ModuleListItem>
        {
            new("sensor-reader", "Reads sensors", "run", 1, 2, "2026-05-30T10:00:00Z"),
        };

        var detailedModule = new ModuleDetailResponse(
            ModuleId: "sensor-reader",
            Description: "Reads sensors",
            DefaultEntrypoint: "run",
            CreatedAtUtc: "2026-05-30T10:00:00Z",
            UpdatedAtUtc: "2026-05-30T10:00:00Z",
            Versions: new List<ModuleVersionItem>
            {
                new(
                    Id: Guid.NewGuid(),
                    Version: "1.0.0",
                    PackageHash: "abc123",
                    PackageSizeBytes: 1024,
                    CreatedAtUtc: "2026-05-30T10:00:00Z"
                ),
            },
            Assignments: new List<ModuleAssignmentDetail>(),
            VariableDefs: new List<ModuleVariableDefItem>()
        );

        _mockService.Setup(s => s.ListModulesAsync(It.IsAny<CancellationToken>())).ReturnsAsync(moduleListItems);
        _mockService.Setup(s => s.GetModuleAsync("sensor-reader", It.IsAny<CancellationToken>())).ReturnsAsync(detailedModule);

        var result = await _controller.ListModules(CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var payload = Assert.IsType<List<ModuleDetailResponse>>(ok.Value);
        Assert.Single(payload);
        Assert.Equal("sensor-reader", payload[0].ModuleId);
    }

    [Fact]
    public async Task CreateModule_Returns201_WhenValid()
    {
        var record = new ModuleDefinitionRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = "new-mod",
            Description = "Test",
            DefaultEntrypoint = "run",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _mockService.Setup(s => s.CreateModuleAsync(It.IsAny<CreateModuleRequest>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(record);

        var result = await _controller.CreateModule(new CreateModuleRequest
        {
            ModuleId = "new-mod",
            Description = "Test",
        }, CancellationToken.None);

        var created = Assert.IsType<CreatedResult>(result);
        Assert.Equal($"/api/admin/modules/new-mod", created.Location);
        var payload = Assert.IsType<CreateModuleResponse>(created.Value);
        Assert.Equal("new-mod", payload.ModuleId);
        Assert.Null(payload.Version);
    }

    [Fact]
    public async Task CreateModule_Returns400_WhenModuleIdMissing()
    {
        var result = await _controller.CreateModule(new CreateModuleRequest(), CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Equal("invalid_request", error.Error);
    }

    [Fact]
    public async Task CreateModule_Returns400_WhenBodyNull()
    {
        var result = await _controller.CreateModule(null, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Equal("invalid_request", error.Error);
    }

    [Fact]
    public async Task GetModule_ReturnsOk_WhenFound()
    {
        var detail = new ModuleDetailResponse(
            "sensor-reader", "Reads sensors", "run",
            "2026-05-30T10:00:00Z", "2026-05-30T10:00:00Z",
            new List<ModuleVersionItem>(),
            new List<ModuleAssignmentDetail>(),
            new List<ModuleVariableDefItem>());
        _mockService.Setup(s => s.GetModuleAsync("sensor-reader", It.IsAny<CancellationToken>()))
            .ReturnsAsync(detail);

        var result = await _controller.GetModule("sensor-reader", CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<ModuleDetailResponse>(ok.Value);
        Assert.Equal("sensor-reader", payload.ModuleId);
    }

    [Fact]
    public async Task GetModule_Returns404_WhenNotFound()
    {
        _mockService.Setup(s => s.GetModuleAsync("nonexistent", It.IsAny<CancellationToken>()))
            .ReturnsAsync((ModuleDetailResponse?)null);

        var result = await _controller.GetModule("nonexistent", CancellationToken.None);

        var notFound = Assert.IsType<NotFoundObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(notFound.Value);
        Assert.Equal("not_found", error.Error);
    }

    [Fact]
    public async Task AssignModule_Returns201_WhenValid()
    {
        var record = new ModuleAssignmentRecord
        {
            Id = Guid.NewGuid(),
            IntervalMs = 60000,
            TimeoutMs = 5000,
            Entrypoint = "run",
            Enabled = true,
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _mockService.Setup(s => s.AssignModuleAsync("sensor-reader", It.IsAny<AssignModuleRequest>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(record);

        var result = await _controller.AssignModule("sensor-reader", new AssignModuleRequest
        {
            DeviceId = "dev-001",
            Version = "1.0.0",
        }, CancellationToken.None);

        var created = Assert.IsType<CreatedResult>(result);
        var payload = Assert.IsType<AssignModuleResponse>(created.Value);
        Assert.Equal("sensor-reader", payload.ModuleId);
        Assert.Equal("dev-001", payload.DeviceId);
    }

    [Fact]
    public async Task AssignModule_Returns400_WhenDeviceIdMissing()
    {
        var result = await _controller.AssignModule("sensor-reader", new AssignModuleRequest
        {
            Version = "1.0.0",
        }, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Contains("device_id", error.Message);
    }

    [Fact]
    public async Task AssignModule_Returns404_WhenNotFound()
    {
        _mockService.Setup(s => s.AssignModuleAsync("nonexistent", It.IsAny<AssignModuleRequest>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((ModuleAssignmentRecord?)null);

        var result = await _controller.AssignModule("nonexistent", new AssignModuleRequest
        {
            DeviceId = "dev-001",
            Version = "1.0.0",
        }, CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task UpdateAssignment_ReturnsOk_WhenFound()
    {
        var record = new ModuleAssignmentRecord
        {
            Id = Guid.NewGuid(),
            IntervalMs = 15000,
            Enabled = false,
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _mockService.Setup(s => s.UpdateAssignmentAsync(It.IsAny<Guid>(), It.IsAny<UpdateAssignmentRequest>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(record);

        var result = await _controller.UpdateAssignment(record.Id, new UpdateAssignmentRequest
        {
            IntervalMs = 15000,
            Enabled = false,
        }, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<UpdateAssignmentResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
        Assert.Equal(record.Id, payload.Id);
    }

    [Fact]
    public async Task UpdateAssignment_Returns404_WhenNotFound()
    {
        _mockService.Setup(s => s.UpdateAssignmentAsync(It.IsAny<Guid>(), It.IsAny<UpdateAssignmentRequest>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((ModuleAssignmentRecord?)null);

        var result = await _controller.UpdateAssignment(Guid.NewGuid(), new UpdateAssignmentRequest
        {
            IntervalMs = 10000,
        }, CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task RemoveAssignment_ReturnsOk_WhenRemoved()
    {
        _mockService.Setup(s => s.RemoveAssignmentAsync(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);

        var result = await _controller.RemoveAssignment("sensor-reader", Guid.NewGuid(), CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<StatusResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
    }

    [Fact]
    public async Task RemoveAssignment_Returns404_WhenNotFound()
    {
        _mockService.Setup(s => s.RemoveAssignmentAsync(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);

        var result = await _controller.RemoveAssignment("sensor-reader", Guid.NewGuid(), CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task UploadVersionFile_Returns400_WhenVersionMissing()
    {
        var result = await _controller.UploadVersionFile("sensor-reader", null, null, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Contains("version", error.Message);
    }

    [Fact]
    public async Task UploadVersionFile_Returns400_WhenFileMissing()
    {
        var result = await _controller.UploadVersionFile("sensor-reader", "1.0.0", null, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Contains("file", error.Message!.ToLower());
    }

    [Fact]
    public async Task UploadVersionText_Returns201_WhenValid()
    {
        var versionRecord = new ModuleVersionRecord
        {
            Id = Guid.NewGuid(),
            Version = "1.0.0",
            PackageHash = "sha256:abc",
            PackageSizeBytes = 42,
            CreatedAtUtc = DateTimeOffset.UtcNow,
        };
        _mockService.Setup(s => s.UploadVersionAsync("sensor-reader", "1.0.0", It.IsAny<Stream>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(versionRecord);

        var result = await _controller.UploadVersionText("sensor-reader", new UploadVersionRequest
        {
            Version = "1.0.0",
            Code = "def run(ctx): return {'ok': True}",
        }, CancellationToken.None);

        var created = Assert.IsType<CreatedResult>(result);
        var payload = Assert.IsType<ModuleVersionItem>(created.Value);
        Assert.Equal("1.0.0", payload.Version);
    }

    [Fact]
    public async Task UploadVersionText_Returns400_WhenCodeMissing()
    {
        var result = await _controller.UploadVersionText("sensor-reader", new UploadVersionRequest
        {
            Version = "1.0.0",
        }, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Contains("code", error.Message);
    }

    [Fact]
    public async Task UploadVersionText_Returns400_WhenVersionMissing()
    {
        var result = await _controller.UploadVersionText("sensor-reader", new UploadVersionRequest
        {
            Code = "def run(ctx): pass",
        }, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Contains("version", error.Message);
    }

    [Fact]
    public async Task UploadVersionText_Returns404_WhenModuleNotFound()
    {
        _mockService.Setup(s => s.UploadVersionAsync("nonexistent", "1.0.0", It.IsAny<Stream>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync((ModuleVersionRecord?)null);

        var result = await _controller.UploadVersionText("nonexistent", new UploadVersionRequest
        {
            Version = "1.0.0",
            Code = "def run(ctx): pass",
        }, CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task CreateModule_WithCode_Returns201WithVersion()
    {
        var record = new ModuleDefinitionRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = "new-mod",
            Description = "Test",
            DefaultEntrypoint = "run",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _mockService.Setup(s => s.CreateModuleAsync(It.IsAny<CreateModuleRequest>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(record);

        var versionRecord = new ModuleVersionRecord
        {
            Id = Guid.NewGuid(),
            Version = "1.0.0",
            PackageHash = "sha256:abc",
            PackageSizeBytes = 20,
            CreatedAtUtc = DateTimeOffset.UtcNow,
        };
        _mockService.Setup(s => s.UploadVersionAsync("new-mod", "1.0.0", It.IsAny<Stream>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(versionRecord);

        var result = await _controller.CreateModule(new CreateModuleRequest
        {
            ModuleId = "new-mod",
            Version = "1.0.0",
            Code = "def run(ctx): pass",
        }, CancellationToken.None);

        var created = Assert.IsType<CreatedResult>(result);
        _mockService.Verify(s => s.UploadVersionAsync("new-mod", "1.0.0", It.IsAny<Stream>(), It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task CreateModule_WithCodeButNoVersion_Returns400()
    {
        var result = await _controller.CreateModule(new CreateModuleRequest
        {
            ModuleId = "new-mod",
            Code = "def run(ctx): pass",
        }, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Contains("version", error.Message);
    }

    [Fact]
    public void GetVersionCode_ReturnsOk_WithCode()
    {
        var code = "def run(ctx): pass";
        _mockService.Setup(s => s.GetPackage("sensor-reader", "1.0.0"))
            .Returns(System.Text.Encoding.UTF8.GetBytes(code));

        var result = _controller.GetVersionCode("sensor-reader", "1.0.0");

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<ModuleVersionCodeResponse>(ok.Value);
        Assert.Equal("sensor-reader", payload.ModuleId);
        Assert.Equal("1.0.0", payload.Version);
        Assert.Equal(code, payload.Code);
    }

    [Fact]
    public void GetVersionCode_ReturnsNotFound_WhenPackageMissing()
    {
        _mockService.Setup(s => s.GetPackage("sensor-reader", "9.9.9"))
            .Returns((byte[]?)null);

        var result = _controller.GetVersionCode("sensor-reader", "9.9.9");

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task GetAssignmentVariables_ReturnsOk_WithItems()
    {
        var items = new List<ModuleVariableValueItem>
        {
            new("X", "1", "override", null),
        };
        _mockVariableService.Setup(s => s.GetVariableValuesWithSourceAsync(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(items);

        var result = await _controller.GetAssignmentVariables(Guid.NewGuid(), CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<List<ModuleVariableValueItem>>(ok.Value);
        Assert.Single(payload);
    }

    [Fact]
    public async Task SetAssignmentVariable_ReturnsOk_WhenSet()
    {
        _mockVariableService.Setup(s => s.SetVariableValueAsync(It.IsAny<Guid>(), "X", "1", It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);

        var result = await _controller.SetAssignmentVariable(Guid.NewGuid(), "X", new SetVariableValueRequest { Value = "1" }, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<StatusResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
    }

    [Fact]
    public async Task DeleteAssignmentVariable_ReturnsOk_WhenDeleted()
    {
        _mockVariableService.Setup(s => s.DeleteVariableValueAsync(It.IsAny<Guid>(), "X", It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);

        var result = await _controller.DeleteAssignmentVariable(Guid.NewGuid(), "X", CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<StatusResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
    }

    // ── Visualization endpoints ───────────────────────────────────────────

    [Fact]
    public async Task GetVisualizations_ReturnsOkWithVisualizations()
    {
        var vizs = new List<ModuleVariableVisualizationRecord>
        {
            new()
            {
                Id = Guid.NewGuid(),
                ModuleVariableDefId = Guid.NewGuid(),
                JsonPath = "temp",
                DisplayName = "Temperature Gauge",
                VisualizationType = "gauge",
                VisualizationConfig = System.Text.Json.JsonSerializer.Serialize(new { min = 0, max = 100 }),
                CreatedAtUtc = DateTimeOffset.UtcNow,
                UpdatedAtUtc = DateTimeOffset.UtcNow,
            },
        };
        _mockVariableService
            .Setup(s => s.GetVisualizationsForVariableAsync("mod-1", "temp", It.IsAny<CancellationToken>()))
            .ReturnsAsync(vizs);

        var result = await _controller.GetVisualizations("mod-1", "temp", CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var payload = Assert.IsType<List<ModuleVariableVisualizationItem>>(ok.Value);
        Assert.Single(payload);
        Assert.Equal("Temperature Gauge", payload[0].DisplayName);
    }

    [Fact]
    public async Task GetVisualizations_EmptyList_ReturnsOk()
    {
        _mockVariableService
            .Setup(s => s.GetVisualizationsForVariableAsync("mod-1", "temp", It.IsAny<CancellationToken>()))
            .ReturnsAsync(new List<ModuleVariableVisualizationRecord>());

        var result = await _controller.GetVisualizations("mod-1", "temp", CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var payload = Assert.IsType<List<ModuleVariableVisualizationItem>>(ok.Value);
        Assert.Empty(payload);
    }

    [Fact]
    public async Task CreateVisualization_ValidRequest_Returns201()
    {
        var vizId = Guid.NewGuid();
        var request = new UpsertModuleVariableVisualizationRequest(
            "temperature",
            "Temperature Gauge",
            "gauge",
            new { min = 0, max = 100 }
        );

        var created = new ModuleVariableVisualizationRecord
        {
            Id = vizId,
            ModuleVariableDefId = Guid.NewGuid(),
            JsonPath = "temperature",
            DisplayName = "Temperature Gauge",
            VisualizationType = "gauge",
            VisualizationConfig = System.Text.Json.JsonSerializer.Serialize(request.VisualizationConfig),
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };

        _mockVariableService
            .Setup(s => s.UpsertVisualizationAsync("mod-1", "temp", "new", request, It.IsAny<CancellationToken>()))
            .ReturnsAsync(created);

        var result = await _controller.CreateVisualization("mod-1", "temp", request, CancellationToken.None);

        var createdResult = Assert.IsType<CreatedResult>(result);
        Assert.Equal($"/api/admin/modules/mod-1/variables/temp/visualizations/{vizId}", createdResult.Location);
        var payload = Assert.IsType<ModuleVariableVisualizationItem>(createdResult.Value);
        Assert.Equal("Temperature Gauge", payload.DisplayName);
    }

    [Fact]
    public async Task CreateVisualization_NullRequest_Returns400()
    {
        var result = await _controller.CreateVisualization("mod-1", "temp", null, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task CreateVisualization_ServiceReturnsNull_Returns404()
    {
        var request = new UpsertModuleVariableVisualizationRequest(
            "temp",
            "Temp",
            "gauge",
            null
        );

        _mockVariableService
            .Setup(s => s.UpsertVisualizationAsync("no-mod", "temp", "new", request, It.IsAny<CancellationToken>()))
            .ReturnsAsync((ModuleVariableVisualizationRecord?)null);

        var result = await _controller.CreateVisualization("no-mod", "temp", request, CancellationToken.None);

        var notFound = Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task UpdateVisualization_ValidRequest_ReturnsOk()
    {
        var vizId = Guid.NewGuid();
        var request = new UpsertModuleVariableVisualizationRequest(
            "temperature.current",
            "Current Temperature",
            "line_chart",
            new { historyPoints = 5 }
        );

        var updated = new ModuleVariableVisualizationRecord
        {
            Id = vizId,
            ModuleVariableDefId = Guid.NewGuid(),
            JsonPath = "temperature.current",
            DisplayName = "Current Temperature",
            VisualizationType = "line_chart",
            VisualizationConfig = System.Text.Json.JsonSerializer.Serialize(request.VisualizationConfig),
            CreatedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-10),
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };

        _mockVariableService
            .Setup(s => s.UpsertVisualizationAsync("mod-1", "temp", vizId.ToString(), request, It.IsAny<CancellationToken>()))
            .ReturnsAsync(updated);

        var result = await _controller.UpdateVisualization("mod-1", "temp", vizId, request, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<ModuleVariableVisualizationItem>(ok.Value);
        Assert.Equal("Current Temperature", payload.DisplayName);
    }

    [Fact]
    public async Task UpdateVisualization_ServiceReturnsNull_Returns404()
    {
        var vizId = Guid.NewGuid();
        var request = new UpsertModuleVariableVisualizationRequest(
            "temp",
            "Temp",
            "gauge",
            null
        );

        _mockVariableService
            .Setup(s => s.UpsertVisualizationAsync("mod-1", "temp", vizId.ToString(), request, It.IsAny<CancellationToken>()))
            .ReturnsAsync((ModuleVariableVisualizationRecord?)null);

        var result = await _controller.UpdateVisualization("mod-1", "temp", vizId, request, CancellationToken.None);

        var notFound = Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task DeleteVisualization_Existing_ReturnsOk()
    {
        var vizId = Guid.NewGuid();
        _mockVariableService
            .Setup(s => s.DeleteVisualizationAsync("mod-1", "temp", vizId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);

        var result = await _controller.DeleteVisualization("mod-1", "temp", vizId, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<StatusResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
    }

    [Fact]
    public async Task DeleteVisualization_NotFound_Returns404()
    {
        var vizId = Guid.NewGuid();
        _mockVariableService
            .Setup(s => s.DeleteVisualizationAsync("mod-1", "temp", vizId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);

        var result = await _controller.DeleteVisualization("mod-1", "temp", vizId, CancellationToken.None);

        var notFound = Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task DeleteVersion_ValidVersion_ReturnsOk()
    {
        _mockService.Setup(s => s.DeleteVersionAsync("test-mod", "1.0.0", It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);

        var result = await _controller.DeleteVersion("test-mod", "1.0.0", CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<StatusResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
    }

    [Fact]
    public async Task DeleteVersion_NonexistentVersion_Returns404()
    {
        _mockService.Setup(s => s.DeleteVersionAsync("test-mod", "1.0.0", It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);

        var result = await _controller.DeleteVersion("test-mod", "1.0.0", CancellationToken.None);

        var notFound = Assert.IsType<NotFoundObjectResult>(result);
        var payload = Assert.IsType<ErrorResponse>(notFound.Value);
        Assert.Equal("not_found", payload.Error);
    }

    [Fact]
    public async Task InferSchema_WithResults_ReturnsOkWithSchema()
    {
        var schema = new { type = "object", properties = new { temperature = new { type = "number" } } };
        _mockVariableService
            .Setup(s => s.InferJsonSchemaAsync("mod-1", "sensor", It.IsAny<CancellationToken>()))
            .ReturnsAsync(schema);

        var result = await _controller.InferJsonSchema("mod-1", "sensor", CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        Assert.NotNull(ok.Value);
    }

    [Fact]
    public async Task InferSchema_NoResults_Returns404()
    {
        _mockVariableService
            .Setup(s => s.InferJsonSchemaAsync("mod-1", "sensor", It.IsAny<CancellationToken>()))
            .ReturnsAsync((object?)null);

        var result = await _controller.InferJsonSchema("mod-1", "sensor", CancellationToken.None);

        var notFound = Assert.IsType<NotFoundObjectResult>(result);
    }
}
