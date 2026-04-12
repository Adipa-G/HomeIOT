using System.Text.Json;
using HomeIOT.Api.Configuration;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Microsoft.Extensions.Logging;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Route("api/devices")]
public sealed class DevicesController : EdgeApiControllerBase
{
    private readonly ApiDbContext _dbContext;
    private readonly IOptions<RuntimeControlOptions> _runtimeOptions;
    private readonly ILogger<DevicesController> _logger;

    public DevicesController(ApiDbContext dbContext, IOptions<RuntimeControlOptions> runtimeOptions, ILogger<DevicesController> logger)
    {
        _dbContext = dbContext;
        _runtimeOptions = runtimeOptions;
        _logger = logger;
    }

    [HttpPost("register")]
    public async Task<ActionResult<RegisterResponse>> HandleRegister(
        [FromBody] RegisterRequest? request,
        CancellationToken cancellationToken)
    {
        if (request is null)
        {
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));
        }

        var deviceIdValidation = ValidateBodyDeviceId(request.DeviceId);
        if (deviceIdValidation is not null)
        {
            return deviceIdValidation;
        }

        if (string.IsNullOrWhiteSpace(request.Version))
        {
            return BadRequest(new ErrorResponse("invalid_request", "version is required."));
        }

        var requestContext = GetDeviceRequestContext()!;
        var now = DateTimeOffset.UtcNow;
        var existing = await _dbContext.Devices.FirstOrDefaultAsync(x => x.DeviceId == requestContext.DeviceId, cancellationToken);
        var created = existing is null;

        var device = existing ?? new DeviceRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = requestContext.DeviceId,
            ApiKey = requestContext.ApiKey,
            CreatedAtUtc = now,
            Mode = "production",
        };

        device.ApiKey = requestContext.ApiKey;
        device.Platform = string.IsNullOrWhiteSpace(request.Platform) ? device.Platform : request.Platform;
        device.Version = request.Version;
        device.Ip = request.Ip;
        device.UpdatedAtUtc = now;

        if (created)
        {
            _dbContext.Devices.Add(device);
        }

        await _dbContext.SaveChangesAsync(cancellationToken);

        var response = new RegisterResponse("ok", requestContext.DeviceId);
        return created
            ? StatusCode(StatusCodes.Status201Created, response)
            : Ok(response);
    }

    [HttpPost("heartbeat")]
    public async Task<ActionResult<HeartbeatResponse>> HandleHeartbeat(
        [FromBody] HeartbeatRequest? request,
        CancellationToken cancellationToken)
    {
        if (request is null)
        {
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));
        }

        var deviceIdValidation = ValidateBodyDeviceId(request.DeviceId);
        if (deviceIdValidation is not null)
        {
            return deviceIdValidation;
        }

        if (request.Timestamp is null)
        {
            return BadRequest(new ErrorResponse("invalid_request", "timestamp is required."));
        }

        var requestContext = GetDeviceRequestContext()!;
        var device = requestContext.Device;
        if (device is null)
        {
            return Unauthorized(new ErrorResponse("unauthorized", "Unknown device."));
        }

        

        var now = DateTimeOffset.UtcNow;
        device.LastHeartbeatAtUtc = now;
        device.UpdatedAtUtc = now;

        _dbContext.Heartbeats.Add(new HeartbeatRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            ClientTimestamp = request.Timestamp,
            UptimeMs = request.UptimeMs,
            FreeMemoryBytes = request.FreeMemoryBytes,
            ReceivedAtUtc = now,
        });

        await _dbContext.SaveChangesAsync(cancellationToken);

        var runtime = _runtimeOptions.Value;
        var response = new HeartbeatResponse(
            "ok",
            ToUtcZ(now),
            device.Mode,
            runtime.DevPollIntervalMs,
            runtime.ModuleAssignmentPollIntervalMs,
            runtime.NextHeartbeatMs);

        return Ok(response);
    }

    [HttpPost("logs")]
    public async Task<ActionResult<StatusResponse>> HandleLogs(
        [FromBody] LogBatchRequest? request,
        CancellationToken cancellationToken)
    {
        if (request is null)
        {
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));
        }

        var deviceIdValidation = ValidateBodyDeviceId(request.DeviceId);
        if (deviceIdValidation is not null)
        {
            return deviceIdValidation;
        }

        if (string.IsNullOrWhiteSpace(request.Reason))
        {
            return BadRequest(new ErrorResponse("invalid_request", "reason is required."));
        }

        if (request.SentAt is null)
        {
            return BadRequest(new ErrorResponse("invalid_request", "sentAt is required."));
        }

        var requestContext = GetDeviceRequestContext()!;
        var device = requestContext.Device;
        if (device is null)
        {
            return Unauthorized(new ErrorResponse("unauthorized", "Unknown device."));
        }

        _logger.LogInformation("Received log batch from {DeviceId} (ip={Ip}) reason={Reason} entries={Count} dropped={Dropped}", requestContext.DeviceId, device.Ip, request.Reason, request.Logs?.Count ?? 0, request.DroppedCount ?? 0);

        var now = DateTimeOffset.UtcNow;
        device.UpdatedAtUtc = now;

        _dbContext.LogBatches.Add(new LogBatchRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            Reason = request.Reason,
            SentAt = request.SentAt.Value,
            DroppedCount = request.DroppedCount ?? 0,
            Truncated = request.Truncated ?? false,
            ReceivedCount = request.Logs.Count,
            LogsJson = JsonSerializer.Serialize(request.Logs),
            ReceivedAtUtc = now,
        });

        await _dbContext.SaveChangesAsync(cancellationToken);
        return Ok(new StatusResponse("ok", request.Logs.Count));
    }
}
