using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/admin/ota")]
public sealed class AdminOtaController : UserApiControllerBase
{
    private readonly IOtaReleaseService _otaService;

    public AdminOtaController(IOtaReleaseService otaService)
    {
        _otaService = otaService;
    }

    [HttpGet]
    public ActionResult<List<OtaPlatformListItem>> ListPlatforms()
    {
        return Ok(_otaService.ListPlatforms());
    }

    [HttpGet("{platform}")]
    public ActionResult<List<OtaReleaseListItem>> ListReleases(string platform)
    {
        if (!IsSafeToken(platform))
            return BadRequest(new ErrorResponse("invalid_request", "platform contains unsupported characters."));

        return Ok(_otaService.ListReleases(platform));
    }

    [HttpGet("{platform}/{version}")]
    public ActionResult<OtaReleaseDetailResponse> GetRelease(string platform, string version)
    {
        if (!IsSafeToken(platform))
            return BadRequest(new ErrorResponse("invalid_request", "platform contains unsupported characters."));

        if (!IsSafeVersion(version))
            return BadRequest(new ErrorResponse("invalid_request", "version contains unsupported characters."));

        var detail = _otaService.GetReleaseDetail(platform, version);
        if (detail is null)
            return NotFound(new ErrorResponse("not_found", "Release not found."));

        return Ok(detail);
    }

    [HttpPost("{platform}/{version}")]
    [RequestSizeLimit(100 * 1024 * 1024)] // 100 MB
    public async Task<IActionResult> UploadRelease(
        string platform, string version, IFormFile? file, CancellationToken ct)
    {
        if (!IsSafeToken(platform))
            return BadRequest(new ErrorResponse("invalid_request", "platform contains unsupported characters."));

        if (!IsSafeVersion(version))
            return BadRequest(new ErrorResponse("invalid_request", "version contains unsupported characters."));

        if (file is null || file.Length == 0)
            return BadRequest(new ErrorResponse("invalid_request", "A zip file is required."));

        if (!file.FileName.EndsWith(".zip", StringComparison.OrdinalIgnoreCase))
            return BadRequest(new ErrorResponse("invalid_request", "File must be a .zip archive."));

        using var stream = file.OpenReadStream();
        await _otaService.UploadReleaseAsync(platform, version, stream, ct);

        var detail = _otaService.GetReleaseDetail(platform, version);
        return Created($"/api/admin/ota/{platform}/{version}", detail);
    }

    [HttpDelete("{platform}/{version}")]
    public IActionResult DeleteRelease(string platform, string version)
    {
        if (!IsSafeToken(platform))
            return BadRequest(new ErrorResponse("invalid_request", "platform contains unsupported characters."));

        if (!IsSafeVersion(version))
            return BadRequest(new ErrorResponse("invalid_request", "version contains unsupported characters."));

        var deleted = _otaService.DeleteRelease(platform, version);
        if (!deleted)
            return NotFound(new ErrorResponse("not_found", "Release not found."));

        return Ok(new StatusResponse("ok"));
    }

    private static bool IsSafeToken(string value)
    {
        foreach (var ch in value)
        {
            if (char.IsLetterOrDigit(ch) || ch == '-' || ch == '_' || ch == '.')
                continue;
            return false;
        }

        return true;
    }

    private static bool IsSafeVersion(string value)
    {
        return value.Length <= 64 && IsSafeToken(value);
    }
}
