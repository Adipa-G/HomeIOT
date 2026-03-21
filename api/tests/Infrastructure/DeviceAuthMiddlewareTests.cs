using System.Text.Json;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Infrastructure;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Xunit;

namespace HomeIOT.Api.Tests.Infrastructure;

public class DeviceAuthMiddlewareTests
{
    [Fact]
    public async Task PingEndpoint_WithoutHeaders_AllowsRequest()
    {
        await using var dbContext = CreateDbContext();
        var wasNextCalled = false;
        var middleware = new DeviceAuthMiddleware(_ =>
        {
            wasNextCalled = true;
            return Task.CompletedTask;
        });

        var httpContext = new DefaultHttpContext
        {
            Request =
            {
                Path = "/api/ping",
                Method = HttpMethods.Get,
            },
            Response =
            {
                Body = new MemoryStream(),
            },
        };

        await middleware.InvokeAsync(httpContext, dbContext);

        Assert.True(wasNextCalled);
        Assert.NotEqual(StatusCodes.Status401Unauthorized, httpContext.Response.StatusCode);
    }

    [Fact]
    public async Task MissingHeaders_Returns401Unauthorized()
    {
        await using var dbContext = CreateDbContext();
        var wasNextCalled = false;
        var middleware = new DeviceAuthMiddleware(_ =>
        {
            wasNextCalled = true;
            return Task.CompletedTask;
        });

        var httpContext = new DefaultHttpContext
        {
            Request =
            {
                Path = "/api/devices/heartbeat",
                Method = HttpMethods.Post,
            },
            Response =
            {
                Body = new MemoryStream(),
            },
        };

        await middleware.InvokeAsync(httpContext, dbContext);

        Assert.Equal(StatusCodes.Status401Unauthorized, httpContext.Response.StatusCode);
        Assert.False(wasNextCalled);

        httpContext.Response.Body.Position = 0;
        using var document = await JsonDocument.ParseAsync(httpContext.Response.Body);
        Assert.Equal("unauthorized", document.RootElement.GetProperty("error").GetString());
    }

    [Fact]
    public async Task InvalidApiKey_Returns401Unauthorized()
    {
        await using var dbContext = CreateDbContext();
        dbContext.Devices.Add(new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = "dev-001",
            ApiKey = "correct-key",
            Mode = "production",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        });
        await dbContext.SaveChangesAsync();

        var wasNextCalled = false;
        var middleware = new DeviceAuthMiddleware(_ =>
        {
            wasNextCalled = true;
            return Task.CompletedTask;
        });

        var httpContext = new DefaultHttpContext
        {
            Request =
            {
                Path = "/api/devices/heartbeat",
                Method = HttpMethods.Post,
            },
            Response =
            {
                Body = new MemoryStream(),
            },
        };
        httpContext.Request.Headers["X-Device-ID"] = "dev-001";
        httpContext.Request.Headers["X-Api-Key"] = "wrong-key";

        await middleware.InvokeAsync(httpContext, dbContext);

        Assert.Equal(StatusCodes.Status401Unauthorized, httpContext.Response.StatusCode);
        Assert.False(wasNextCalled);

        httpContext.Response.Body.Position = 0;
        using var document = await JsonDocument.ParseAsync(httpContext.Response.Body);
        Assert.Equal("unauthorized", document.RootElement.GetProperty("error").GetString());
    }

    [Fact]
    public async Task ValidCredentials_AttachesDeviceContextToHttpContext()
    {
        await using var dbContext = CreateDbContext();
        var device = new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = "dev-001",
            ApiKey = "correct-key",
            Mode = "production",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
        dbContext.Devices.Add(device);
        await dbContext.SaveChangesAsync();

        var wasNextCalled = false;
        var middleware = new DeviceAuthMiddleware(_ =>
        {
            wasNextCalled = true;
            return Task.CompletedTask;
        });

        var httpContext = new DefaultHttpContext
        {
            Request =
            {
                Path = "/api/devices/heartbeat",
                Method = HttpMethods.Post,
            },
            Response =
            {
                Body = new MemoryStream(),
            },
        };
        httpContext.Request.Headers["X-Device-ID"] = "dev-001";
        httpContext.Request.Headers["X-Api-Key"] = "correct-key";

        await middleware.InvokeAsync(httpContext, dbContext);

        Assert.True(wasNextCalled);
        var requestContext = httpContext.GetDeviceRequestContext();
        Assert.NotNull(requestContext);
        Assert.Equal("dev-001", requestContext!.DeviceId);
        Assert.NotNull(requestContext.Device);
        Assert.Equal(device.Id, requestContext.Device!.Id);
    }

    private static ApiDbContext CreateDbContext()
    {
        var options = new DbContextOptionsBuilder<ApiDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;

        return new ApiDbContext(options);
    }
}
