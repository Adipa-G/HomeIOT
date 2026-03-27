using Microsoft.AspNetCore.Mvc;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Route("api/ota")]
public sealed class OtaController : EdgeApiControllerBase
{
    private readonly IOtaReleaseService _otaReleaseService;

    public OtaController(IOtaReleaseService otaReleaseService)
    {
        _otaReleaseService = otaReleaseService;
    }

    [HttpGet("check")]
    public ActionResult<OtaCheckResponse> Check([FromQuery] string? version)
    {
        if (string.IsNullOrWhiteSpace(version))
        {
            return BadRequest(new ErrorResponse("invalid_request", "version is required."));
        }

        var platform = ResolvePlatform();
        if (platform is null)
        {
            return BadRequest(new ErrorResponse("invalid_request", "X-Platform header is required when device platform is unknown."));
        }

        if (!IsSafeToken(platform))
        {
            return BadRequest(new ErrorResponse("invalid_request", "platform contains unsupported characters."));
        }

        var currentVersion = Request.Headers["X-Current-Version"].ToString().Trim();
        if (string.IsNullOrWhiteSpace(currentVersion))
        {
            currentVersion = version.Trim();
        }

        if (!IsSafeVersion(currentVersion))
        {
            return BadRequest(new ErrorResponse("invalid_request", "version contains unsupported characters."));
        }

        var response = _otaReleaseService.CheckForUpdate(platform, currentVersion);
        return Ok(response);
    }

    [HttpGet("file")]
    public IActionResult GetFile([FromQuery] string? version, [FromQuery] string? path)
    {
        if (string.IsNullOrWhiteSpace(version))
        {
            return BadRequest(new ErrorResponse("invalid_request", "version is required."));
        }

        if (string.IsNullOrWhiteSpace(path))
        {
            return BadRequest(new ErrorResponse("invalid_request", "path is required."));
        }

        if (!IsSafeVersion(version))
        {
            return BadRequest(new ErrorResponse("invalid_request", "version contains unsupported characters."));
        }

        var platform = ResolvePlatform();
        if (platform is null)
        {
            return BadRequest(new ErrorResponse("invalid_request", "X-Platform header is required when device platform is unknown."));
        }

        if (!IsSafeToken(platform))
        {
            return BadRequest(new ErrorResponse("invalid_request", "platform contains unsupported characters."));
        }

        var fileResult = _otaReleaseService.TryGetReleaseFile(platform, version.Trim(), path.Trim());
        if (fileResult is null)
        {
            return NotFound(new ErrorResponse("not_found", "OTA artifact not found."));
        }

        return File(fileResult.Content, "application/octet-stream", fileDownloadName: fileResult.FileName);
    }

    private string? ResolvePlatform()
    {
        var headerPlatform = Request.Headers["X-Platform"].ToString().Trim();
        if (!string.IsNullOrWhiteSpace(headerPlatform))
        {
            return headerPlatform;
        }

        return GetDeviceRequestContext()?.Device?.Platform?.Trim();
    }

    private static bool IsSafeToken(string value)
    {
        foreach (var ch in value)
        {
            if (char.IsLetterOrDigit(ch) || ch == '-' || ch == '_' || ch == '.')
            {
                continue;
            }

            return false;
        }

        return true;
    }

    private static bool IsSafeVersion(string value)
    {
        return value.Length <= 64 && IsSafeToken(value);
    }
}
