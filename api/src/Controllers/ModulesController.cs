using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

[
ApiController]
[Route("api/devices/modules")]
public sealed class ModulesController : ApiControllerBase
{
    [HttpGet("assignment")]
    public IActionResult GetAssignment()
    {
        return NoContent();
    }

    [HttpGet("package")]
    public IActionResult GetPackage()
    {
        return NotFound();
    }

    [HttpPost("results")]
    public IActionResult ReportResult()
    {
        return Accepted();
    }

    [HttpPost("status")]
    public IActionResult ReportStatus()
    {
        return Accepted();
    }
}
