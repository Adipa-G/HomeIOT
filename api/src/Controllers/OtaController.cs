using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

[
ApiController]
[Route("api/ota")]
public sealed class OtaController : ApiControllerBase
{
    [HttpGet("check")]
    public IActionResult Check()
    {
        return Ok(new { available = false });
    }

    [HttpGet("file")]
    public IActionResult GetFile()
    {
        return NotFound();
    }
}
