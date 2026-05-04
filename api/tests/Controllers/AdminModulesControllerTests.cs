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
    private readonly AdminModulesController _controller;

    public AdminModulesControllerTests()
    {
        _mockService = new Mock<IModuleService>();
        _mockVariableService = new Mock<IModuleVariableService>();
        _controller = new AdminModulesController(_mockService.Object, _mockVariableService.Object)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext(),
            },
        };
    }

    [Fact]
    public async Task ListModules_ReturnsOkWithModules()
    {
        var modules = new List<ModuleListItem>
        {
            new("sensor-reader", "Reads sensors", "run", 2, 1, "2026-05-30T10:00:00Z"),
        };
        _mockService.Setup(s => s.ListModulesAsync(It.IsAny<CancellationToken>())).ReturnsAsync(modules);

        var result = await _controller.ListModules(CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var payload = Assert.IsType<List<ModuleListItem>>(ok.Value);
        Assert.Single(payload);
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

        var result = await _controller.RemoveAssignment(Guid.NewGuid(), CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<StatusResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
    }

    [Fact]
    public async Task RemoveAssignment_Returns404_WhenNotFound()
    {
        _mockService.Setup(s => s.RemoveAssignmentAsync(It.IsAny<Guid>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);

        var result = await _controller.RemoveAssignment(Guid.NewGuid(), CancellationToken.None);

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
}
