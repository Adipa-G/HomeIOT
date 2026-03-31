using HomeIOT.Api.Controllers;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Infrastructure;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class ModulesControllerTests
{
    private readonly Mock<IModuleService> _mockService;
    private readonly ModulesController _controller;

    public ModulesControllerTests()
    {
        _mockService = new Mock<IModuleService>();
        _controller = new ModulesController(_mockService.Object)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext(),
            },
        };
        _controller.HttpContext.SetDeviceRequestContext(
            new DeviceRequestContext("dev-001", "api-key", null));
    }

    [Fact]
    public async Task GetAssignment_ReturnsOk_WhenAssignmentExists()
    {
        var response = new ModuleAssignmentResponse("sha256:abc123", new List<ModuleAssignmentItem>
        {
            new("sensor-reader", "1.0.0", 60000, 5000, "run", "sha256:def456", true),
        });
        _mockService.Setup(s => s.GetAssignmentForDeviceAsync("dev-001", null, It.IsAny<CancellationToken>()))
            .ReturnsAsync(response);

        var result = await _controller.GetAssignment(null, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<ModuleAssignmentResponse>(ok.Value);
        Assert.Single(payload.Modules);
        Assert.Equal("sensor-reader", payload.Modules[0].ModuleId);
    }

    [Fact]
    public async Task GetAssignment_Returns204_WhenHashUnchanged()
    {
        _mockService.Setup(s => s.GetAssignmentForDeviceAsync("dev-001", "sha256:abc", It.IsAny<CancellationToken>()))
            .ReturnsAsync((ModuleAssignmentResponse?)null);

        var result = await _controller.GetAssignment("sha256:abc", CancellationToken.None);

        Assert.IsType<NoContentResult>(result);
    }

    [Fact]
    public async Task GetAssignment_Returns401_WhenNoAuthContext()
    {
        _controller.HttpContext.Items.Clear();

        var result = await _controller.GetAssignment(null, CancellationToken.None);

        var unauthorized = Assert.IsType<UnauthorizedObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(unauthorized.Value);
        Assert.Equal("unauthorized", error.Error);
    }

    [Fact]
    public void GetPackage_ReturnsFile_WhenExists()
    {
        var content = "def run(ctx): pass"u8.ToArray();
        _mockService.Setup(s => s.GetPackage("sensor-reader", "1.0.0")).Returns(content);

        var result = _controller.GetPackage("sensor-reader", "1.0.0");

        var fileResult = Assert.IsType<FileContentResult>(result);
        Assert.Equal("application/octet-stream", fileResult.ContentType);
        Assert.Equal(content, fileResult.FileContents);
    }

    [Fact]
    public void GetPackage_Returns404_WhenNotFound()
    {
        _mockService.Setup(s => s.GetPackage("missing", "1.0.0")).Returns((byte[]?)null);

        var result = _controller.GetPackage("missing", "1.0.0");

        var notFound = Assert.IsType<NotFoundObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(notFound.Value);
        Assert.Equal("not_found", error.Error);
    }

    [Fact]
    public void GetPackage_Returns400_WhenModuleIdMissing()
    {
        var result = _controller.GetPackage(null, "1.0.0");

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Equal("invalid_request", error.Error);
    }

    [Fact]
    public void GetPackage_Returns400_WhenVersionMissing()
    {
        var result = _controller.GetPackage("sensor-reader", null);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Equal("invalid_request", error.Error);
    }

    [Fact]
    public async Task ReportResult_Returns202_WhenValid()
    {
        var request = new ModuleResultRequest
        {
            DeviceId = "dev-001",
            ModuleId = "sensor-reader",
            ModuleVersion = "1.0.0",
            RunId = "run-1",
            Status = "success",
            StartedAtUtc = "2026-05-30T10:00:00Z",
            FinishedAtUtc = "2026-05-30T10:00:01Z",
            ElapsedMs = 1000,
        };

        var result = await _controller.ReportResult(request, CancellationToken.None);

        Assert.IsType<AcceptedResult>(result);
        _mockService.Verify(s => s.RecordResultAsync(request, It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task ReportResult_Returns400_WhenDeviceIdMismatch()
    {
        var request = new ModuleResultRequest
        {
            DeviceId = "other-device",
            ModuleId = "sensor-reader",
            Status = "success",
        };

        var result = await _controller.ReportResult(request, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Equal("invalid_request", error.Error);
    }

    [Fact]
    public async Task ReportResult_Returns400_WhenBodyNull()
    {
        var result = await _controller.ReportResult(null, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Equal("invalid_request", error.Error);
    }

    [Fact]
    public async Task ReportResult_Returns400_WhenModuleIdMissing()
    {
        var request = new ModuleResultRequest
        {
            DeviceId = "dev-001",
            Status = "success",
        };

        var result = await _controller.ReportResult(request, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Contains("module_id", error.Message);
    }

    [Fact]
    public async Task ReportStatus_Returns202_WhenValid()
    {
        var request = new ModuleStatusRequest
        {
            DeviceId = "dev-001",
            ModuleId = "sensor-reader",
            ModuleVersion = "1.0.0",
            Disabled = true,
            DisabledReason = "Too many failures",
            FailedStartCount = 3,
        };

        var result = await _controller.ReportStatus(request, CancellationToken.None);

        Assert.IsType<AcceptedResult>(result);
        _mockService.Verify(s => s.RecordStatusAsync(request, It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task ReportStatus_Returns400_WhenDeviceIdMismatch()
    {
        var request = new ModuleStatusRequest
        {
            DeviceId = "wrong-device",
            ModuleId = "sensor-reader",
        };

        var result = await _controller.ReportStatus(request, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Equal("invalid_request", error.Error);
    }

    [Fact]
    public async Task ReportStatus_Returns400_WhenBodyNull()
    {
        var result = await _controller.ReportStatus(null, CancellationToken.None);

        var bad = Assert.IsType<BadRequestObjectResult>(result);
        var error = Assert.IsType<ErrorResponse>(bad.Value);
        Assert.Equal("invalid_request", error.Error);
    }
}
