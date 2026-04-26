using HomeIOT.Api.Contracts;
using HomeIOT.Api.Infrastructure;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/admin/dev-commands")]
public sealed class AdminDevCommandController : UserApiControllerBase
{
    private readonly IDevCommandQueue _queue;

    public AdminDevCommandController(IDevCommandQueue queue)
    {
        _queue = queue;
    }

    /// <summary>
    /// Operator: queue a dev command to be executed on a target device.
    /// The code is executed remotely via exec() — it is never stored on the device.
    /// </summary>
    [HttpPost]
    public ActionResult<DevCommandEnqueueResponse> Enqueue([FromBody] DevCommandEnqueueRequest? request)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        if (string.IsNullOrWhiteSpace(request.DeviceId))
            return BadRequest(new ErrorResponse("invalid_request", "device_id is required."));

        if (string.IsNullOrWhiteSpace(request.Code))
            return BadRequest(new ErrorResponse("invalid_request", "code is required."));

        var entry = _queue.Enqueue(request.DeviceId, request.Code, request.TimeoutMs);

        return Accepted(new DevCommandEnqueueResponse(entry.CommandId, entry.DeviceId, entry.QueuedAt));
    }

    /// <summary>
    /// Operator: fetch the stored result for a previously submitted command.
    /// </summary>
    [HttpGet("{commandId}/result")]
    public ActionResult GetResult(string commandId)
    {
        var result = _queue.GetResult(commandId);
        if (result is null)
            return NotFound(new ErrorResponse("not_found", "No result found for command_id."));

        return Ok(new
        {
            command_id      = result.CommandId,
            code            = result.Code,
            status          = result.Status,
            exit_code       = result.ExitCode,
            elapsed_ms      = result.ElapsedMs,
            started_at_utc  = result.StartedAtUtc,
            finished_at_utc = result.FinishedAtUtc,
            stdout          = result.Stdout,
            stderr          = result.Stderr,
            data            = result.Data,
            received_at     = result.ReceivedAt,
        });
    }

    /// <summary>
    /// Operator: list all pending (not yet acknowledged) commands.
    /// </summary>
    [HttpGet("pending")]
    public ActionResult ListPending()
    {
        var pending = _queue.ListPending();
        return Ok(pending.Select(e => new
        {
            command_id = e.CommandId,
            device_id = e.DeviceId,
            code = e.Code,
            timeout_ms = e.TimeoutMs,
            queued_at_utc = EndpointValidation.ToUtcZ(e.QueuedAt),
        }));
    }

    /// <summary>
    /// Operator: list all stored command results (most recent first).
    /// </summary>
    [HttpGet("results")]
    public ActionResult ListResults()
    {
        var results = _queue.ListResults();
        return Ok(results.Select(r => new
        {
            command_id = r.CommandId,
            code = r.Code,
            status = r.Status,
            exit_code = r.ExitCode,
            elapsed_ms = r.ElapsedMs,
            started_at_utc = r.StartedAtUtc,
            finished_at_utc = r.FinishedAtUtc,
            stdout = r.Stdout,
            stderr = r.Stderr,
            data = r.Data,
            received_at = r.ReceivedAt,
        }));
    }
}
