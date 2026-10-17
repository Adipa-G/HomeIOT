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
            ApiKeyHash = "correct-key",
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
            ApiKeyHash = "correct-key",
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

    [Fact]
    public async Task AdminPath_WithoutHeaders_AllowsRequest()
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
                Path = "/api/admin/auth/token",
                Method = HttpMethods.Post,
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
    public async Task Register_UnknownDevice_Returns401AndDoesNotCreateDevice()
    {
        await using var dbContext = CreateDbContext();
        var wasNextCalled = false;
        var middleware = new DeviceAuthMiddleware(_ =>
        {
            wasNextCalled = true;
            return Task.CompletedTask;
        });

        var httpContext = CreateDeviceRequest("/api/devices/register", "new-device", "any-key");

        await middleware.InvokeAsync(httpContext, dbContext);

        Assert.Equal(StatusCodes.Status401Unauthorized, httpContext.Response.StatusCode);
        Assert.False(wasNextCalled);
        Assert.False(await dbContext.Devices.AnyAsync());
    }

    [Fact]
    public async Task ValidCredentials_LegacyPlaintextKey_IsUpgradedToHash()
    {
        await using var dbContext = CreateDbContext();
        dbContext.Devices.Add(NewDevice("dev-001", "legacy-key"));
        await dbContext.SaveChangesAsync();

        var wasNextCalled = false;
        var middleware = new DeviceAuthMiddleware(_ =>
        {
            wasNextCalled = true;
            return Task.CompletedTask;
        });

        await middleware.InvokeAsync(CreateDeviceRequest("/api/devices/heartbeat", "dev-001", "legacy-key"), dbContext);

        Assert.True(wasNextCalled);
        var saved = await dbContext.Devices.SingleAsync();
        Assert.Equal(DeviceApiKeyHasher.Hash("legacy-key"), saved.ApiKeyHash);
    }

    [Fact]
    public async Task ValidCredentials_HashedKey_AllowsRequestAndKeepsHash()
    {
        await using var dbContext = CreateDbContext();
        var hash = DeviceApiKeyHasher.Hash("secret-key");
        dbContext.Devices.Add(NewDevice("dev-001", hash));
        await dbContext.SaveChangesAsync();

        var wasNextCalled = false;
        var middleware = new DeviceAuthMiddleware(_ =>
        {
            wasNextCalled = true;
            return Task.CompletedTask;
        });

        await middleware.InvokeAsync(CreateDeviceRequest("/api/devices/heartbeat", "dev-001", "secret-key"), dbContext);

        Assert.True(wasNextCalled);
        Assert.Equal(hash, (await dbContext.Devices.SingleAsync()).ApiKeyHash);
    }

    [Fact]
    public async Task HashedKey_PresentingTheHashItself_Returns401()
    {
        await using var dbContext = CreateDbContext();
        var hash = DeviceApiKeyHasher.Hash("secret-key");
        dbContext.Devices.Add(NewDevice("dev-001", hash));
        await dbContext.SaveChangesAsync();

        var middleware = new DeviceAuthMiddleware(_ => Task.CompletedTask);
        var httpContext = CreateDeviceRequest("/api/devices/heartbeat", "dev-001", hash);

        await middleware.InvokeAsync(httpContext, dbContext);

        Assert.Equal(StatusCodes.Status401Unauthorized, httpContext.Response.StatusCode);
    }

    private static DeviceRecord NewDevice(string deviceId, string apiKeyHash)
    {
        return new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = deviceId,
            ApiKeyHash = apiKeyHash,
            Mode = "production",
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };
    }

    private static DefaultHttpContext CreateDeviceRequest(string path, string deviceId, string apiKey)
    {
        var httpContext = new DefaultHttpContext
        {
            Request =
            {
                Path = path,
                Method = HttpMethods.Post,
            },
            Response =
            {
                Body = new MemoryStream(),
            },
        };
        httpContext.Request.Headers["X-Device-ID"] = deviceId;
        httpContext.Request.Headers["X-Api-Key"] = apiKey;
        return httpContext;
    }

    private static ApiDbContext CreateDbContext()
    {
        var options = new DbContextOptionsBuilder<ApiDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;

        return new ApiDbContext(options);
    }
}
