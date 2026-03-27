using HomeIOT.Api.Contracts;
using HomeIOT.Api.Infrastructure;
using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

public abstract class EdgeApiControllerBase : ControllerBase
{
    protected ActionResult? ValidateBodyDeviceId(string? bodyDeviceId)
    {
        var requestContext = HttpContext.GetDeviceRequestContext();
        if (requestContext is null)
        {
            return Unauthorized(new ErrorResponse("unauthorized", "Missing request auth context."));
        }

        if (string.IsNullOrWhiteSpace(bodyDeviceId))
        {
            return BadRequest(new ErrorResponse("invalid_request", "device_id is required."));
        }

        if (!string.Equals(bodyDeviceId, requestContext.DeviceId, StringComparison.Ordinal))
        {
            return BadRequest(new ErrorResponse("invalid_request", "Body device_id must match X-Device-ID header."));
        }

        return null;
    }

    protected DeviceRequestContext? GetDeviceRequestContext()
    {
        return HttpContext.GetDeviceRequestContext();
    }

    protected static string ToUtcZ(DateTimeOffset value)
    {
        return EndpointValidation.ToUtcZ(value);
    }
}