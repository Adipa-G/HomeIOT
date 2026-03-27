using System.Text.Json;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Route("api/devices/dev-commands")]
public sealed class DevCommandController : EdgeApiControllerBase
{
    private readonly IDevCommandQueue _queue;

    public DevCommandController(IDevCommandQueue queue)
    {
        _queue = queue;
    }

    /// <summary>
    /// Device: poll for the next pending command.
    /// Returns 204 when nothing is queued.
    /// </summary>
    [HttpGet("next")]
    public ActionResult GetNext([FromQuery(Name = "last_revision_hash")] string? lastRevisionHash)
    {
        var requestContext = GetDeviceRequestContext()!;
        var entry = _queue.PeekNext(requestContext.DeviceId);

        if (entry is null)
            return NoContent();

        // Deduplicate: if the device already saw this revision, nothing new.
        if (!string.IsNullOrWhiteSpace(lastRevisionHash)
            && string.Equals(lastRevisionHash, entry.RevisionHash, StringComparison.Ordinal))
        {
            return NoContent();
        }

        return Ok(new
        {
            command_id    = entry.CommandId,
            revision_hash = entry.RevisionHash,
            dedupe_token  = entry.DedupeToken,
            code          = entry.Code,
            timeout_ms    = entry.TimeoutMs,
        });
    }

    /// <summary>
    /// Device: submit execution result for a command.
    /// </summary>
    [HttpPost("{commandId}/result")]
    public ActionResult ReportResult(string commandId, [FromBody] JsonElement body)
    {
        var requestContext = GetDeviceRequestContext()!;

        // Acknowledge removes the command from the pending queue so the device stops receiving it.
        _queue.Acknowledge(requestContext.DeviceId, commandId);

        var opts = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
        var payload = new DevCommandResultPayload(
            CommandId:     commandId,
            RevisionHash:  body.TryGetProperty("revision_hash", out var rh) ? rh.GetString() : null,
            DedupeToken:   body.TryGetProperty("dedupe_token",  out var dt) ? dt.GetString() : null,
            Status:        body.TryGetProperty("status",        out var st) ? st.GetString() ?? "unknown" : "unknown",
            StartedAtUtc:  body.TryGetProperty("started_at_utc",  out var sa) ? sa.GetString() : null,
            FinishedAtUtc: body.TryGetProperty("finished_at_utc", out var fa) ? fa.GetString() : null,
            ElapsedMs:     body.TryGetProperty("elapsed_ms", out var em) && em.TryGetInt64(out var emv) ? emv : 0,
            ExitCode:      body.TryGetProperty("exit_code",  out var ec) && ec.TryGetInt32(out var ecv) ? ecv : 0,
            Stdout:        body.TryGetProperty("stdout", out var so) ? so.GetString() : null,
            Stderr:        body.TryGetProperty("stderr", out var se) ? se.GetString() : null,
            Data:          body.TryGetProperty("data", out var da) && da.ValueKind != System.Text.Json.JsonValueKind.Null ? da : null,
            ReceivedAt:    DateTimeOffset.UtcNow);

        _queue.StoreResult(commandId, payload);

        return Accepted(new { command_id = commandId, status = "accepted" });
    }
}

