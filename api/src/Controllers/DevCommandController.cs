using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

[
ApiController]
[Route("api/devices/dev-commands")]
public sealed class DevCommandController : ApiControllerBase
{
    [HttpGet("next")]
    public IActionResult GetNext()
    {
        return NoContent();
    }

    [HttpPost("{commandId}/result")]
    public IActionResult ReportResult(string commandId)
    {
        return Accepted(new { command_id = commandId, status = "accepted" });
    }
}
