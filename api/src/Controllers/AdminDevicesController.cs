using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/admin/devices")]
public sealed class AdminDevicesController : UserApiControllerBase
{
    private readonly IDeviceAdminService _deviceService;

    public AdminDevicesController(IDeviceAdminService deviceService)
    {
        _deviceService = deviceService;
    }

    [HttpGet]
    public async Task<IActionResult> ListDevices(
        [FromQuery] int offset = 0,
        [FromQuery] int limit = 50,
        [FromQuery] string? platform = null,
        [FromQuery] string? mode = null,
        [FromQuery] string? search = null,
        CancellationToken ct = default)
    {
        limit = Math.Clamp(limit, 1, 200);
        offset = Math.Max(offset, 0);

        var result = await _deviceService.ListDevicesAsync(offset, limit, platform, mode, search, ct);
        return Ok(result);
    }

    [HttpGet("{deviceId}")]
    public async Task<IActionResult> GetDevice(string deviceId, CancellationToken ct)
    {
        var result = await _deviceService.GetDeviceAsync(deviceId, ct);
        if (result is null)
            return NotFound(new ErrorResponse("not_found", "Device not found."));

        return Ok(result);
    }

    [HttpPut("{deviceId}/mode")]
    public async Task<IActionResult> UpdateMode(
        string deviceId,
        [FromBody] UpdateDeviceModeRequest? request,
        CancellationToken ct)
    {
        if (request is null || string.IsNullOrWhiteSpace(request.Mode))
            return BadRequest(new ErrorResponse("invalid_request", "mode is required."));

        var validModes = new[] { "production", "development" };
        if (!validModes.Contains(request.Mode, StringComparer.OrdinalIgnoreCase))
            return BadRequest(new ErrorResponse("invalid_request", "mode must be 'production' or 'development'."));

        var updated = await _deviceService.UpdateDeviceModeAsync(deviceId, request.Mode.ToLowerInvariant(), ct);
        if (!updated)
            return NotFound(new ErrorResponse("not_found", "Device not found."));

        return Ok(new { status = "ok" });
    }

    [HttpDelete("{deviceId}")]
    public async Task<IActionResult> DeleteDevice(string deviceId, CancellationToken ct)
    {
        var deleted = await _deviceService.DeleteDeviceAsync(deviceId, ct);
        if (!deleted)
            return NotFound(new ErrorResponse("not_found", "Device not found."));

        return Ok(new { status = "ok" });
    }

    [HttpGet("{deviceId}/heartbeats")]
    public async Task<IActionResult> GetHeartbeats(
        string deviceId,
        [FromQuery] int offset = 0,
        [FromQuery] int limit = 50,
        [FromQuery] DateTimeOffset? from = null,
        [FromQuery] DateTimeOffset? to = null,
        CancellationToken ct = default)
    {
        limit = Math.Clamp(limit, 1, 200);
        offset = Math.Max(offset, 0);

        var result = await _deviceService.GetHeartbeatsAsync(deviceId, offset, limit, from, to, ct);
        return Ok(result);
    }

    [HttpGet("{deviceId}/logs")]
    public async Task<IActionResult> GetLogs(
        string deviceId,
        [FromQuery] int offset = 0,
        [FromQuery] int limit = 50,
        [FromQuery] DateTimeOffset? from = null,
        [FromQuery] DateTimeOffset? to = null,
        CancellationToken ct = default)
    {
        limit = Math.Clamp(limit, 1, 200);
        offset = Math.Max(offset, 0);

        var result = await _deviceService.GetLogsAsync(deviceId, offset, limit, from, to, ct);
        return Ok(result);
    }
}
