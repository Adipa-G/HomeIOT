using HomeIOT.Api.Contracts;
using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Route("api/ping")]
public sealed class PingController : EdgeApiControllerBase
{
    [HttpGet]
    public ActionResult<PingResponse> Get()
    {
        var now = DateTimeOffset.UtcNow;
        var response = new PingResponse(
            "ok",
            "HomeIOT API",
            ToUtcZ(now));

        return Ok(response);
    }
}
