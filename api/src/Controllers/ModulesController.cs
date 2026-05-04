using Microsoft.AspNetCore.Mvc;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Route("api/devices/modules")]
public sealed class ModulesController : EdgeApiControllerBase
{
    private readonly IModuleService _moduleService;
    private readonly IModuleVariableService _variableService;
    private readonly IModuleServerCodeService _serverCodeService;

    public ModulesController(
        IModuleService moduleService,
        IModuleVariableService variableService,
        IModuleServerCodeService serverCodeService)
    {
        _moduleService = moduleService;
        _variableService = variableService;
        _serverCodeService = serverCodeService;
    }

    [HttpGet("assignment")]
    public async Task<IActionResult> GetAssignment(
        [FromQuery(Name = "last_assignment_hash")] string? lastAssignmentHash,
        CancellationToken ct)
    {
        var context = GetDeviceRequestContext();
        if (context is null)
            return Unauthorized(new ErrorResponse("unauthorized", "Missing request auth context."));

        var response = await _moduleService.GetAssignmentForDeviceAsync(context.DeviceId, lastAssignmentHash, ct);
        if (response is null)
            return NoContent();

        return Ok(response);
    }

    [HttpGet("package")]
    public IActionResult GetPackage(
        [FromQuery(Name = "module_id")] string? moduleId,
        [FromQuery] string? version)
    {
        if (string.IsNullOrWhiteSpace(moduleId))
            return BadRequest(new ErrorResponse("invalid_request", "module_id is required."));

        if (string.IsNullOrWhiteSpace(version))
            return BadRequest(new ErrorResponse("invalid_request", "version is required."));

        var bytes = _moduleService.GetPackage(moduleId.Trim(), version.Trim());
        if (bytes is null)
            return NotFound(new ErrorResponse("not_found", "Module package not found."));

        return File(bytes, "application/octet-stream", fileDownloadName: $"{moduleId}-{version}.py");
    }

    [HttpPost("results")]
    public async Task<IActionResult> ReportResult(
        [FromBody] ModuleResultRequest? request, CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        var validation = ValidateBodyDeviceId(request.DeviceId);
        if (validation is not null)
            return validation;

        if (string.IsNullOrWhiteSpace(request.ModuleId))
            return BadRequest(new ErrorResponse("invalid_request", "module_id is required."));

        if (string.IsNullOrWhiteSpace(request.Status))
            return BadRequest(new ErrorResponse("invalid_request", "status is required."));

        await _moduleService.RecordResultAsync(request, ct);
        return Accepted();
    }

    [HttpPost("status")]
    public async Task<IActionResult> ReportStatus(
        [FromBody] ModuleStatusRequest? request, CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        var validation = ValidateBodyDeviceId(request.DeviceId);
        if (validation is not null)
            return validation;

        if (string.IsNullOrWhiteSpace(request.ModuleId))
            return BadRequest(new ErrorResponse("invalid_request", "module_id is required."));

        await _moduleService.RecordStatusAsync(request, ct);
        return Accepted();
    }

    [HttpPost("prefetch")]
    public async Task<IActionResult> Prefetch(
        [FromBody] ModulePrefetchRequest? request, CancellationToken ct)
    {
        if (request is null || request.Modules is null || request.Modules.Count == 0)
            return Accepted();

        var context = GetDeviceRequestContext();
        if (context is null)
            return Unauthorized(new ErrorResponse("unauthorized", "Missing request auth context."));

        _ = Task.Run(async () =>
        {
            foreach (var item in request.Modules)
            {
                if (string.IsNullOrWhiteSpace(item.ModuleId))
                    continue;
                await _serverCodeService.RunForModuleAsync(
                    context.DeviceId, item.ModuleId, CancellationToken.None);
            }
        });

        return Accepted();
    }
}
