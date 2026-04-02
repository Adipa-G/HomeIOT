using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/admin/modules")]
public sealed class AdminModulesController : UserApiControllerBase
{
    private readonly IModuleService _moduleService;

    public AdminModulesController(IModuleService moduleService)
    {
        _moduleService = moduleService;
    }

    [HttpGet]
    public async Task<ActionResult<List<ModuleListItem>>> ListModules(CancellationToken ct)
    {
        var modules = await _moduleService.ListModulesAsync(ct);
        return Ok(modules);
    }

    [HttpPost]
    public async Task<IActionResult> CreateModule(
        [FromBody] CreateModuleRequest? request, CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        if (string.IsNullOrWhiteSpace(request.ModuleId))
            return BadRequest(new ErrorResponse("invalid_request", "module_id is required."));

        // If code is provided, version is required
        if (!string.IsNullOrWhiteSpace(request.Code) && string.IsNullOrWhiteSpace(request.Version))
            return BadRequest(new ErrorResponse("invalid_request", "version is required when code is provided."));

        var module = await _moduleService.CreateModuleAsync(request, ct);

        ModuleVersionItem? versionItem = null;
        if (!string.IsNullOrWhiteSpace(request.Code) && !string.IsNullOrWhiteSpace(request.Version))
        {
            using var stream = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(request.Code));
            var ver = await _moduleService.UploadVersionAsync(module.ModuleId, request.Version.Trim(), stream, ct);
            if (ver is not null)
            {
                versionItem = new ModuleVersionItem(
                    ver.Id, ver.Version, ver.PackageHash, ver.PackageSizeBytes, ToUtcZ(ver.CreatedAtUtc));
            }
        }

        return Created($"/api/admin/modules/{module.ModuleId}", new
        {
            module_id = module.ModuleId,
            description = module.Description,
            default_entrypoint = module.DefaultEntrypoint,
            created_at_utc = ToUtcZ(module.CreatedAtUtc),
            version = versionItem,
        });
    }

    [HttpGet("{moduleId}")]
    public async Task<IActionResult> GetModule(string moduleId, CancellationToken ct)
    {
        var module = await _moduleService.GetModuleAsync(moduleId, ct);
        if (module is null)
            return NotFound(new ErrorResponse("not_found", "Module not found."));

        return Ok(module);
    }

    [HttpPost("{moduleId}/versions/upload")]
    [Consumes("multipart/form-data")]
    public async Task<IActionResult> UploadVersionFile(
        string moduleId,
        [FromQuery] string? version,
        IFormFile? file,
        CancellationToken ct)
    {
        if (string.IsNullOrWhiteSpace(version))
            return BadRequest(new ErrorResponse("invalid_request", "version query parameter is required."));

        if (file is null || file.Length == 0)
            return BadRequest(new ErrorResponse("invalid_request", "A .py file is required."));

        using var stream = file.OpenReadStream();
        var result = await _moduleService.UploadVersionAsync(moduleId, version.Trim(), stream, ct);
        if (result is null)
            return NotFound(new ErrorResponse("not_found", "Module not found."));

        return Created($"/api/admin/modules/{moduleId}", new ModuleVersionItem(
            result.Id,
            result.Version,
            result.PackageHash,
            result.PackageSizeBytes,
            ToUtcZ(result.CreatedAtUtc)));
    }

    [HttpPost("{moduleId}/versions")]
    public async Task<IActionResult> UploadVersionText(
        string moduleId,
        [FromBody] UploadVersionRequest? request,
        CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        if (string.IsNullOrWhiteSpace(request.Version))
            return BadRequest(new ErrorResponse("invalid_request", "version is required."));

        if (string.IsNullOrWhiteSpace(request.Code))
            return BadRequest(new ErrorResponse("invalid_request", "code is required."));

        using var stream = new MemoryStream(System.Text.Encoding.UTF8.GetBytes(request.Code));
        var result = await _moduleService.UploadVersionAsync(moduleId, request.Version.Trim(), stream, ct);
        if (result is null)
            return NotFound(new ErrorResponse("not_found", "Module not found."));

        return Created($"/api/admin/modules/{moduleId}", new ModuleVersionItem(
            result.Id,
            result.Version,
            result.PackageHash,
            result.PackageSizeBytes,
            ToUtcZ(result.CreatedAtUtc)));
    }

    [HttpGet("{moduleId}/assignments")]
    public async Task<IActionResult> GetAssignments(string moduleId, CancellationToken ct)
    {
        var module = await _moduleService.GetModuleAsync(moduleId, ct);
        if (module is null)
            return NotFound(new ErrorResponse("not_found", "Module not found."));

        return Ok(module.Assignments);
    }

    [HttpPost("{moduleId}/assignments")]
    public async Task<IActionResult> AssignModule(
        string moduleId,
        [FromBody] AssignModuleRequest? request,
        CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        if (string.IsNullOrWhiteSpace(request.DeviceId))
            return BadRequest(new ErrorResponse("invalid_request", "device_id is required."));

        if (string.IsNullOrWhiteSpace(request.Version))
            return BadRequest(new ErrorResponse("invalid_request", "version is required."));

        var assignment = await _moduleService.AssignModuleAsync(moduleId, request, ct);
        if (assignment is null)
            return NotFound(new ErrorResponse("not_found", "Module, device, or version not found."));

        return Created($"/api/admin/modules/assignments/{assignment.Id}", new
        {
            id = assignment.Id,
            module_id = moduleId,
            device_id = request.DeviceId,
            version = request.Version,
            interval_ms = assignment.IntervalMs,
            timeout_ms = assignment.TimeoutMs,
            entrypoint = assignment.Entrypoint,
            enabled = assignment.Enabled,
        });
    }

    [HttpPut("assignments/{assignmentId:guid}")]
    public async Task<IActionResult> UpdateAssignment(
        Guid assignmentId,
        [FromBody] UpdateAssignmentRequest? request,
        CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        var assignment = await _moduleService.UpdateAssignmentAsync(assignmentId, request, ct);
        if (assignment is null)
            return NotFound(new ErrorResponse("not_found", "Assignment or version not found."));

        return Ok(new { status = "ok", id = assignment.Id });
    }

    [HttpDelete("assignments/{assignmentId:guid}")]
    public async Task<IActionResult> RemoveAssignment(Guid assignmentId, CancellationToken ct)
    {
        var removed = await _moduleService.RemoveAssignmentAsync(assignmentId, ct);
        if (!removed)
            return NotFound(new ErrorResponse("not_found", "Assignment not found."));

        return Ok(new { status = "ok" });
    }

    [HttpPut("{moduleId}")]
    public async Task<IActionResult> UpdateModule(
        string moduleId, [FromBody] UpdateModuleRequest? request, CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        var updated = await _moduleService.UpdateModuleAsync(moduleId, request, ct);
        if (!updated)
            return NotFound(new ErrorResponse("not_found", "Module not found."));

        return Ok(new { status = "ok" });
    }

    [HttpDelete("{moduleId}")]
    public async Task<IActionResult> DeleteModule(string moduleId, CancellationToken ct)
    {
        var deleted = await _moduleService.DeleteModuleAsync(moduleId, ct);
        if (!deleted)
            return NotFound(new ErrorResponse("not_found", "Module not found."));

        return Ok(new { status = "ok" });
    }

    [HttpDelete("{moduleId}/versions/{versionId:guid}")]
    public async Task<IActionResult> DeleteVersion(string moduleId, Guid versionId, CancellationToken ct)
    {
        var deleted = await _moduleService.DeleteVersionAsync(moduleId, versionId, ct);
        if (!deleted)
            return NotFound(new ErrorResponse("not_found", "Version not found."));

        return Ok(new { status = "ok" });
    }

    [HttpGet("results")]
    public async Task<IActionResult> QueryResults(
        [FromQuery] int offset = 0,
        [FromQuery] int limit = 50,
        [FromQuery] DateTimeOffset? from = null,
        [FromQuery] DateTimeOffset? to = null,
        [FromQuery(Name = "device_id")] string? deviceId = null,
        [FromQuery(Name = "module_id")] string? moduleId = null,
        [FromQuery] string? status = null,
        CancellationToken ct = default)
    {
        limit = Math.Clamp(limit, 1, 200);
        offset = Math.Max(offset, 0);

        var result = await _moduleService.QueryResultsAsync(offset, limit, from, to, deviceId, moduleId, status, ct);
        return Ok(result);
    }

    [HttpGet("statuses")]
    public async Task<IActionResult> QueryStatuses(
        [FromQuery] int offset = 0,
        [FromQuery] int limit = 50,
        [FromQuery(Name = "device_id")] string? deviceId = null,
        [FromQuery(Name = "module_id")] string? moduleId = null,
        CancellationToken ct = default)
    {
        limit = Math.Clamp(limit, 1, 200);
        offset = Math.Max(offset, 0);

        var result = await _moduleService.QueryStatusesAsync(offset, limit, deviceId, moduleId, ct);
        return Ok(result);
    }
}
