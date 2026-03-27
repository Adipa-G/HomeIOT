using HomeIOT.Api.Configuration;
using HomeIOT.Api.Controllers;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Infrastructure;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Moq;
using Microsoft.Extensions.Logging;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class DevicesControllerTests
{
    [Fact]
    public async Task Register_NewDevice_Returns201Created()
    {
        await using var dbContext = CreateDbContext();
        var controller = CreateController(dbContext, new DeviceRequestContext("dev-001", "api-key-001", null));

        var result = await controller.HandleRegister(new RegisterRequest
        {
            DeviceId = "dev-001",
            Platform = "esp32",
            Version = "1.0.0",
            Ip = "192.168.1.10",
            Timestamp = 1716890000,
        }, CancellationToken.None);

        var objectResult = Assert.IsType<ObjectResult>(result.Result);
        Assert.Equal(StatusCodes.Status201Created, objectResult.StatusCode);

        var payload = Assert.IsType<RegisterResponse>(objectResult.Value);
        Assert.Equal("ok", payload.Status);
        Assert.Equal("dev-001", payload.DeviceId);

        var savedDevice = await dbContext.Devices.SingleAsync(x => x.DeviceId == "dev-001");
        Assert.Equal("api-key-001", savedDevice.ApiKey);
        Assert.Equal("esp32", savedDevice.Platform);
        Assert.Equal("1.0.0", savedDevice.Version);
    }

    [Fact]
    public async Task Register_ExistingDevice_Returns200OK()
    {
        await using var dbContext = CreateDbContext();
        dbContext.Devices.Add(new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = "dev-001",
            ApiKey = "old-key",
            Platform = "esp32",
            Version = "0.9.0",
            Mode = "production",
            CreatedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-30),
            UpdatedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-30),
        });
        await dbContext.SaveChangesAsync();

        var controller = CreateController(dbContext, new DeviceRequestContext("dev-001", "new-key", null));

        var result = await controller.HandleRegister(new RegisterRequest
        {
            DeviceId = "dev-001",
            Version = "1.1.0",
            Ip = "192.168.1.11",
        }, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var payload = Assert.IsType<RegisterResponse>(ok.Value);
        Assert.Equal("dev-001", payload.DeviceId);

        var savedDevice = await dbContext.Devices.SingleAsync(x => x.DeviceId == "dev-001");
        Assert.Equal("new-key", savedDevice.ApiKey);
        Assert.Equal("1.1.0", savedDevice.Version);
        Assert.Equal("192.168.1.11", savedDevice.Ip);
    }

    [Fact]
    public async Task Register_MismatchedDeviceId_Returns400BadRequest()
    {
        await using var dbContext = CreateDbContext();
        var controller = CreateController(dbContext, new DeviceRequestContext("dev-001", "api-key-001", null));

        var result = await controller.HandleRegister(new RegisterRequest
        {
            DeviceId = "dev-002",
            Version = "1.0.0",
        }, CancellationToken.None);

        var badRequest = Assert.IsType<BadRequestObjectResult>(result.Result);
        var payload = Assert.IsType<ErrorResponse>(badRequest.Value);
        Assert.Equal("invalid_request", payload.Error);
    }

    [Fact]
    public async Task Heartbeat_ValidPayload_Returns200WithRuntimeControl()
    {
        await using var dbContext = CreateDbContext();
        var device = new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = "dev-001",
            ApiKey = "api-key-001",
            Mode = "production",
            CreatedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-10),
            UpdatedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-10),
        };
        dbContext.Devices.Add(device);
        await dbContext.SaveChangesAsync();

        var controller = CreateController(dbContext, new DeviceRequestContext("dev-001", "api-key-001", device));

        var result = await controller.HandleHeartbeat(new HeartbeatRequest
        {
            DeviceId = "dev-001",
            Timestamp = 1716890100,
            UptimeMs = 120000,
            FreeMemoryBytes = 204800,
        }, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var payload = Assert.IsType<HeartbeatResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
        Assert.Equal(30000, payload.NextHeartbeatMs);

        var hbCount = await dbContext.Heartbeats.CountAsync();
        Assert.Equal(1, hbCount);
    }

    [Fact]
    public async Task Heartbeat_UnknownDevice_Returns401Unauthorized()
    {
        await using var dbContext = CreateDbContext();
        var controller = CreateController(dbContext, new DeviceRequestContext("dev-001", "api-key-001", null));

        var result = await controller.HandleHeartbeat(new HeartbeatRequest
        {
            DeviceId = "dev-001",
            Timestamp = 1716890100,
        }, CancellationToken.None);

        var unauthorized = Assert.IsType<UnauthorizedObjectResult>(result.Result);
        var payload = Assert.IsType<ErrorResponse>(unauthorized.Value);
        Assert.Equal("unauthorized", payload.Error);
    }

    [Fact]
    public async Task Logs_BatchUpload_Returns200WithReceivedCount()
    {
        await using var dbContext = CreateDbContext();
        var device = new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = "dev-001",
            ApiKey = "api-key-001",
            Mode = "production",
            CreatedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-10),
            UpdatedAtUtc = DateTimeOffset.UtcNow.AddMinutes(-10),
        };
        dbContext.Devices.Add(device);
        await dbContext.SaveChangesAsync();

        var controller = CreateController(dbContext, new DeviceRequestContext("dev-001", "api-key-001", device));

        var result = await controller.HandleLogs(new LogBatchRequest
        {
            DeviceId = "dev-001",
            Reason = "timer",
            SentAt = 1716890200,
            Logs = new List<LogEntryRequest>
            {
                new() { Ts = 1716890190, Level = "INFO", Message = "tick" },
                new() { Ts = 1716890195, Level = "WARN", Message = "slow" },
            },
        }, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var payload = Assert.IsType<StatusResponse>(ok.Value);
        Assert.Equal("ok", payload.Status);
        Assert.Equal(2, payload.Received);

        var batches = await dbContext.LogBatches.ToListAsync();
        Assert.Single(batches);
        Assert.Equal(2, batches[0].ReceivedCount);
    }

    private static ApiDbContext CreateDbContext()
    {
        var options = new DbContextOptionsBuilder<ApiDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;

        return new ApiDbContext(options);
    }

    private static DevicesController CreateController(ApiDbContext dbContext, DeviceRequestContext requestContext)
    {
        var optionsMock = new Mock<IOptions<RuntimeControlOptions>>();
        optionsMock.Setup(x => x.Value).Returns(new RuntimeControlOptions
        {
            NextHeartbeatMs = 30000,
            DevPollIntervalMs = 2000,
            ModuleAssignmentPollIntervalMs = 60000,
        });

        var loggerMock = new Mock<ILogger<DevicesController>>();
        var controller = new DevicesController(dbContext, optionsMock.Object, loggerMock.Object)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext(),
            },
        };

        controller.HttpContext.SetDeviceRequestContext(requestContext);
        return controller;
    }
}
