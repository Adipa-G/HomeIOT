using System.Text;
using System.Text.RegularExpressions;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Infrastructure;
using HomeIOT.Api.Services;
using HomeIOT.Api.Services.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/admin/devices")]
public sealed partial class AdminDeviceProvisioningController : UserApiControllerBase
{
    private const int MaxSsidBytes = 32;
    private const int MaxWifiPasswordLength = 64;

    private readonly IDeviceProvisioningService _provisioningService;

    public AdminDeviceProvisioningController(IDeviceProvisioningService provisioningService)
    {
        _provisioningService = provisioningService;
    }

    [HttpPost]
    public async Task<ActionResult<ProvisionDeviceResponse>> CreateDevice(
        [FromBody] CreateDeviceRequest? request,
        CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        if (string.IsNullOrWhiteSpace(request.DeviceId) || !DeviceIdPattern().IsMatch(request.DeviceId.Trim()))
            return BadRequest(new ErrorResponse("invalid_request", "device_id is required and may only contain letters, digits, '.', '_' or '-' (max 64)."));

        if (!DevicePlatforms.IsProvisionable(request.Platform?.Trim()))
            return BadRequest(new ErrorResponse("invalid_request", $"platform must be one of: {string.Join(", ", DevicePlatforms.Provisionable)}."));

        var connectionError = ValidateConnection(request.ApiUrl, request.WifiSsid, request.WifiPassword);
        if (connectionError is not null)
            return connectionError;

        var result = await _provisioningService.CreateDeviceAsync(request, ct);
        return result.Status == DeviceProvisioningStatus.Success
            ? StatusCode(StatusCodes.Status201Created, result.Response)
            : ToErrorResult(result);
    }

    [HttpPost("{deviceId}/provision")]
    public async Task<ActionResult<ProvisionDeviceResponse>> ReprovisionDevice(
        string deviceId,
        [FromBody] ReprovisionDeviceRequest? request,
        CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        if (!string.IsNullOrWhiteSpace(request.Platform) && !DevicePlatforms.IsProvisionable(request.Platform.Trim()))
            return BadRequest(new ErrorResponse("invalid_request", $"platform must be one of: {string.Join(", ", DevicePlatforms.Provisionable)}."));

        var connectionError = ValidateConnection(request.ApiUrl, request.WifiSsid, request.WifiPassword);
        if (connectionError is not null)
            return connectionError;

        var result = await _provisioningService.ReprovisionDeviceAsync(deviceId, request, ct);
        return result.Status == DeviceProvisioningStatus.Success
            ? Ok(result.Response)
            : ToErrorResult(result);
    }

    private BadRequestObjectResult? ValidateConnection(string? apiUrl, string? wifiSsid, string? wifiPassword)
    {
        if (string.IsNullOrWhiteSpace(apiUrl)
            || !Uri.TryCreate(apiUrl.Trim(), UriKind.Absolute, out var uri)
            || (uri.Scheme != Uri.UriSchemeHttp && uri.Scheme != Uri.UriSchemeHttps))
            return BadRequest(new ErrorResponse("invalid_request", "api_url must be an absolute http(s) URL reachable by the device."));

        if (string.IsNullOrEmpty(wifiSsid) || Encoding.UTF8.GetByteCount(wifiSsid) > MaxSsidBytes)
            return BadRequest(new ErrorResponse("invalid_request", $"wifi_ssid is required (max {MaxSsidBytes} bytes)."));

        if (wifiPassword is not null && wifiPassword.Length > MaxWifiPasswordLength)
            return BadRequest(new ErrorResponse("invalid_request", $"wifi_password must be at most {MaxWifiPasswordLength} characters."));

        return null;
    }

    private ActionResult ToErrorResult(DeviceProvisioningResult result)
    {
        var message = result.Message ?? "Provisioning failed.";
        return result.Status switch
        {
            DeviceProvisioningStatus.DeviceNotFound => NotFound(new ErrorResponse("not_found", message)),
            DeviceProvisioningStatus.DeviceExists => Conflict(new ErrorResponse("conflict", message)),
            DeviceProvisioningStatus.PlatformRequired => BadRequest(new ErrorResponse("invalid_request", message)),
            DeviceProvisioningStatus.NoRelease => Conflict(new ErrorResponse("no_release", message)),
            _ => Conflict(new ErrorResponse("release_incomplete", message)),
        };
    }

    [GeneratedRegex("^[A-Za-z0-9._-]{1,64}$")]
    private static partial Regex DeviceIdPattern();
}
