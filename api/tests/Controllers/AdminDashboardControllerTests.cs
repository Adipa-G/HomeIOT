using HomeIOT.Api.Controllers;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class AdminDashboardControllerTests : IDisposable
{
    private readonly ApiDbContext _db;
    private readonly Mock<IModuleService> _mockModuleService;
    private readonly AdminDashboardController _controller;

    public AdminDashboardControllerTests()
    {
        var options = new DbContextOptionsBuilder<ApiDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        _db = new ApiDbContext(options);
        _mockModuleService = new Mock<IModuleService>();
        _controller = new AdminDashboardController(_db, _mockModuleService.Object)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext(),
            },
        };
    }

    public void Dispose()
    {
        _db.Dispose();
    }

    [Fact]
    public async Task GetDashboard_ReturnsZeros_WhenEmpty()
    {
        var result = await _controller.GetDashboard(CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var dashboard = Assert.IsType<DashboardResponse>(ok.Value);
        Assert.Equal(0, dashboard.TotalDevices);
        Assert.Equal(0, dashboard.TotalModules);
        Assert.Equal(0, dashboard.TotalUsers);
    }

    [Fact]
    public async Task GetDashboard_CountsDevices()
    {
        _db.Devices.Add(new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = "dev-001",
            ApiKey = "key",
            Mode = "production",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
            LastHeartbeatAtUtc = DateTimeOffset.UtcNow,
        });
        await _db.SaveChangesAsync();

        var result = await _controller.GetDashboard(CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var dashboard = Assert.IsType<DashboardResponse>(ok.Value);
        Assert.Equal(1, dashboard.TotalDevices);
        Assert.Equal(1, dashboard.DevicesOnline24h);
    }

    [Fact]
    public async Task GetDashboard_CountsHeartbeatsInLast24h()
    {
        var device = new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = "dev-001",
            ApiKey = "key",
            Mode = "production",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        _db.Devices.Add(device);
        _db.Heartbeats.Add(new HeartbeatRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            ReceivedAtUtc = DateTimeOffset.UtcNow,
        });
        _db.Heartbeats.Add(new HeartbeatRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            ReceivedAtUtc = DateTimeOffset.UtcNow.AddDays(-2), // older than 24h
        });
        await _db.SaveChangesAsync();

        var result = await _controller.GetDashboard(CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var dashboard = Assert.IsType<DashboardResponse>(ok.Value);
        Assert.Equal(1, dashboard.Heartbeats24h);
    }

    [Fact]
    public async Task GetDashboardModules_ReturnsItems_FromModuleService()
    {
        var items = new List<DashboardModuleItem>
        {
            new(
                Guid.NewGuid(),
                "device-1",
                "module-1",
                "ok",
                "output",
                null,
                DateTimeOffset.UtcNow.ToString("O"),
                new List<ModuleVariableDefItem>()),
        };
        _mockModuleService
            .Setup(s => s.GetDashboardModulesAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(items);

        var result = await _controller.GetDashboardModules(CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var returned = Assert.IsType<List<DashboardModuleItem>>(ok.Value);
        Assert.Single(returned);
        Assert.Equal("device-1", returned[0].DeviceId);
    }

    [Fact]
    public async Task GetDashboardModules_ReturnsEmptyList_WhenNoneFlagged()
    {
        _mockModuleService
            .Setup(s => s.GetDashboardModulesAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync(new List<DashboardModuleItem>());

        var result = await _controller.GetDashboardModules(CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var returned = Assert.IsType<List<DashboardModuleItem>>(ok.Value);
        Assert.Empty(returned);
    }
}
