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

        return Ok(new StatusResponse("ok"));
    }

    [HttpDelete("{deviceId}")]
    public async Task<IActionResult> DeleteDevice(string deviceId, CancellationToken ct)
    {
        var deleted = await _deviceService.DeleteDeviceAsync(deviceId, ct);
        if (!deleted)
            return NotFound(new ErrorResponse("not_found", "Device not found."));

        return Ok(new StatusResponse("ok"));
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

    [HttpGet("{deviceId}/heartbeats/activity")]
    public async Task<IActionResult> GetHeartbeatActivity(
        string deviceId,
        [FromQuery] string? bucket,
        [FromQuery] DateTimeOffset? from,
        [FromQuery] DateTimeOffset? to,
        CancellationToken ct = default)
    {
        var validation = ValidateActivityQuery(bucket, from, to, out var normalizedBucket);
        if (validation is not null)
            return validation;

        var result = await _deviceService.GetHeartbeatActivityAsync(deviceId, normalizedBucket!, from!.Value, to!.Value, ct);
        return Ok(result);
    }

    [HttpGet("{deviceId}/logs/activity")]
    public async Task<IActionResult> GetLogActivity(
        string deviceId,
        [FromQuery] string? bucket,
        [FromQuery] DateTimeOffset? from,
        [FromQuery] DateTimeOffset? to,
        CancellationToken ct = default)
    {
        var validation = ValidateActivityQuery(bucket, from, to, out var normalizedBucket);
        if (validation is not null)
            return validation;

        var result = await _deviceService.GetLogActivityAsync(deviceId, normalizedBucket!, from!.Value, to!.Value, ct);
        return Ok(result);
    }

    private static readonly HashSet<string> ValidActivityBuckets = new(StringComparer.OrdinalIgnoreCase)
    {
        "day", "hour", "five_minute",
    };

    private const int MaxActivityBuckets = 500;

    private IActionResult? ValidateActivityQuery(
        string? bucket, DateTimeOffset? from, DateTimeOffset? to, out string? normalizedBucket)
    {
        normalizedBucket = null;

        if (string.IsNullOrWhiteSpace(bucket) || !ValidActivityBuckets.Contains(bucket))
            return BadRequest(new ErrorResponse("invalid_request", "bucket must be 'day', 'hour', or 'five_minute'."));

        if (from is null || to is null)
            return BadRequest(new ErrorResponse("invalid_request", "from and to are required."));

        if (from >= to)
            return BadRequest(new ErrorResponse("invalid_request", "from must be before to."));

        normalizedBucket = bucket.ToLowerInvariant();
        var span = normalizedBucket switch
        {
            "day" => TimeSpan.FromDays(1),
            "hour" => TimeSpan.FromHours(1),
            _ => TimeSpan.FromMinutes(5),
        };

        var bucketCount = (to.Value - from.Value).Ticks / span.Ticks;
        if (bucketCount > MaxActivityBuckets)
            return BadRequest(new ErrorResponse("invalid_request", $"Requested range exceeds max of {MaxActivityBuckets} buckets."));

        return null;
    }
}
