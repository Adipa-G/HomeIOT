using HomeIOT.Api.Controllers;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class AdminDevicesControllerTests
{
    private readonly Mock<IDeviceAdminService> _mockService;
    private readonly AdminDevicesController _controller;

    public AdminDevicesControllerTests()
    {
        _mockService = new Mock<IDeviceAdminService>();
        _controller = new AdminDevicesController(_mockService.Object)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext(),
            },
        };
    }

    [Fact]
    public async Task ListDevices_ReturnsOk()
    {
        var response = new PaginatedResponse<DeviceListItem>(
            new List<DeviceListItem>(), 0, 0, 50);
        _mockService.Setup(s => s.ListDevicesAsync(0, 50, null, null, null, It.IsAny<CancellationToken>()))
            .ReturnsAsync(response);

        var result = await _controller.ListDevices(ct: CancellationToken.None);

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public async Task GetDevice_ReturnsOk_WhenFound()
    {
        var device = new DeviceDetailResponse(
            "dev-001", "esp32", "1.0.0", "192.168.1.1", "production",
            null, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", null);
        _mockService.Setup(s => s.GetDeviceAsync("dev-001", It.IsAny<CancellationToken>()))
            .ReturnsAsync(device);

        var result = await _controller.GetDevice("dev-001", CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        Assert.IsType<DeviceDetailResponse>(ok.Value);
    }

    [Fact]
    public async Task GetDevice_ReturnsNotFound_WhenMissing()
    {
        _mockService.Setup(s => s.GetDeviceAsync("missing", It.IsAny<CancellationToken>()))
            .ReturnsAsync((DeviceDetailResponse?)null);

        var result = await _controller.GetDevice("missing", CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task UpdateMode_ReturnsOk_WhenValid()
    {
        _mockService.Setup(s => s.UpdateDeviceModeAsync("dev-001", "development", It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);

        var result = await _controller.UpdateMode(
            "dev-001", new UpdateDeviceModeRequest { Mode = "development" }, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<StatusResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
    }

    [Fact]
    public async Task UpdateMode_ReturnsBadRequest_WhenModeNull()
    {
        var result = await _controller.UpdateMode(
            "dev-001", new UpdateDeviceModeRequest { Mode = null }, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task UpdateMode_ReturnsBadRequest_WhenInvalidMode()
    {
        var result = await _controller.UpdateMode(
            "dev-001", new UpdateDeviceModeRequest { Mode = "invalid" }, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task UpdateMode_ReturnsNotFound_WhenDeviceMissing()
    {
        _mockService.Setup(s => s.UpdateDeviceModeAsync("missing", "development", It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);

        var result = await _controller.UpdateMode(
            "missing", new UpdateDeviceModeRequest { Mode = "development" }, CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task DeleteDevice_ReturnsOk_WhenDeleted()
    {
        _mockService.Setup(s => s.DeleteDeviceAsync("dev-001", It.IsAny<CancellationToken>()))
            .ReturnsAsync(true);

        var result = await _controller.DeleteDevice("dev-001", CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var payload = Assert.IsType<StatusResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
    }

    [Fact]
    public async Task DeleteDevice_ReturnsNotFound_WhenMissing()
    {
        _mockService.Setup(s => s.DeleteDeviceAsync("missing", It.IsAny<CancellationToken>()))
            .ReturnsAsync(false);

        var result = await _controller.DeleteDevice("missing", CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task GetHeartbeats_ReturnsOk()
    {
        var response = new PaginatedResponse<HeartbeatListItem>(
            new List<HeartbeatListItem>(), 0, 0, 50);
        _mockService.Setup(s => s.GetHeartbeatsAsync("dev-001", 0, 50, null, null, It.IsAny<CancellationToken>()))
            .ReturnsAsync(response);

        var result = await _controller.GetHeartbeats("dev-001", ct: CancellationToken.None);

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public async Task GetLogs_ReturnsOk()
    {
        var response = new PaginatedResponse<LogBatchListItem>(
            new List<LogBatchListItem>(), 0, 0, 50);
        _mockService.Setup(s => s.GetLogsAsync("dev-001", 0, 50, null, null, It.IsAny<CancellationToken>()))
            .ReturnsAsync(response);

        var result = await _controller.GetLogs("dev-001", ct: CancellationToken.None);

        Assert.IsType<OkObjectResult>(result);
    }
}
