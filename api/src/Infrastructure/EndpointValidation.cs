using HomeIOT.Api.Contracts;

namespace HomeIOT.Api.Infrastructure;

public static class EndpointValidation
{
    public static IResult? ValidateBodyDeviceId(HttpContext httpContext, string? bodyDeviceId)
    {
        var deviceContext = httpContext.GetDeviceRequestContext();
        if (deviceContext is null)
        {
            return Results.Json(new ErrorResponse("unauthorized", "Missing request auth context."), statusCode: StatusCodes.Status401Unauthorized);
        }

        if (string.IsNullOrWhiteSpace(bodyDeviceId))
        {
            return Results.Json(new ErrorResponse("invalid_request", "device_id is required."), statusCode: StatusCodes.Status400BadRequest);
        }

        if (!string.Equals(bodyDeviceId, deviceContext.DeviceId, StringComparison.Ordinal))
        {
            return Results.Json(new ErrorResponse("invalid_request", "Body device_id must match X-Device-ID header."), statusCode: StatusCodes.Status400BadRequest);
        }

        return null;
    }

    public static string ToUtcZ(DateTimeOffset value) => value.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'");
}
