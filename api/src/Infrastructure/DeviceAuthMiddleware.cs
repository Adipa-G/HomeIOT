using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using Microsoft.EntityFrameworkCore;

namespace HomeIOT.Api.Infrastructure;

public sealed class DeviceAuthMiddleware(RequestDelegate next)
{
    public async Task InvokeAsync(HttpContext context, ApiDbContext dbContext)
    {
        if (!context.Request.Path.StartsWithSegments("/api", StringComparison.OrdinalIgnoreCase))
        {
            await next(context);
            return;
        }

        if (context.Request.Path.Equals("/api/ping", StringComparison.OrdinalIgnoreCase))
        {
            await next(context);
            return;
        }

        if (context.Request.Path.StartsWithSegments("/api/admin", StringComparison.OrdinalIgnoreCase))
        {
            await next(context);
            return;
        }

        var deviceId = context.Request.Headers["X-Device-ID"].ToString().Trim();
        var apiKey = context.Request.Headers["X-Api-Key"].ToString().Trim();

        if (string.IsNullOrWhiteSpace(deviceId) || string.IsNullOrWhiteSpace(apiKey))
        {
            await WriteErrorAsync(context, StatusCodes.Status401Unauthorized, "unauthorized", "Missing device auth headers.");
            return;
        }

        var device = await dbContext.Devices.FirstOrDefaultAsync(x => x.DeviceId == deviceId, context.RequestAborted);
        if (device is null)
        {
            await WriteErrorAsync(context, StatusCodes.Status401Unauthorized, "unauthorized", "Unknown device.");
            return;
        }

        if (!DeviceApiKeyHasher.Verify(apiKey, device.ApiKeyHash))
        {
            await WriteErrorAsync(context, StatusCodes.Status401Unauthorized, "unauthorized", "Invalid API key.");
            return;
        }

        if (!DeviceApiKeyHasher.IsHashed(device.ApiKeyHash))
        {
            device.ApiKeyHash = DeviceApiKeyHasher.Hash(apiKey);
            await dbContext.SaveChangesAsync(context.RequestAborted);
        }

        context.SetDeviceRequestContext(new DeviceRequestContext(deviceId, apiKey, device));
        await next(context);
    }

    private static async Task WriteErrorAsync(HttpContext context, int statusCode, string error, string message)
    {
        context.Response.StatusCode = statusCode;
        context.Response.ContentType = "application/json";
        await context.Response.WriteAsJsonAsync(new ErrorResponse(error, message));
    }
}
