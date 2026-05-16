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
    private readonly IModuleVariableService _variableService;

    public AdminModulesController(
        IModuleService moduleService,
        IModuleVariableService variableService)
    {
        _moduleService = moduleService;
        _variableService = variableService;
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

        return Created($"/api/admin/modules/{module.ModuleId}", new CreateModuleResponse(
            ModuleId:          module.ModuleId,
            Description:       module.Description,
            DefaultEntrypoint: module.DefaultEntrypoint,
            CreatedAtUtc:      ToUtcZ(module.CreatedAtUtc),
            Version:           versionItem));
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

    [HttpGet("{moduleId}/versions/{version}/code")]
    public IActionResult GetVersionCode(string moduleId, string version)
    {
        var bytes = _moduleService.GetPackage(moduleId, version);
        if (bytes is null)
            return NotFound(new ErrorResponse("not_found", "Module version not found."));

        var code = System.Text.Encoding.UTF8.GetString(bytes);
        return Ok(new ModuleVersionCodeResponse(ModuleId: moduleId, Version: version, Code: code));
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

        return Created($"/api/admin/modules/assignments/{assignment.Id}", new AssignModuleResponse(
            Id:         assignment.Id,
            ModuleId:   moduleId,
            DeviceId:   request.DeviceId,
            Version:    request.Version,
            IntervalMs: assignment.IntervalMs,
            TimeoutMs:  assignment.TimeoutMs,
            Entrypoint: assignment.Entrypoint,
            Enabled:    assignment.Enabled));
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

        return Ok(new UpdateAssignmentResponse(Status: "ok", Id: assignment.Id));
    }

    [HttpDelete("{moduleId}/assignments/{assignmentId:guid}")]
    public async Task<IActionResult> RemoveAssignment(string moduleId, Guid assignmentId, CancellationToken ct)
    {
        var removed = await _moduleService.RemoveAssignmentAsync(assignmentId, ct);
        if (!removed)
            return NotFound(new ErrorResponse("not_found", "Assignment not found."));

        return Ok(new StatusResponse("ok"));
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

        return Ok(new StatusResponse("ok"));
    }

    [HttpDelete("{moduleId}")]
    public async Task<IActionResult> DeleteModule(string moduleId, CancellationToken ct)
    {
        var deleted = await _moduleService.DeleteModuleAsync(moduleId, ct);
        if (!deleted)
            return NotFound(new ErrorResponse("not_found", "Module not found."));

        return Ok(new StatusResponse("ok"));
    }

    [HttpDelete("{moduleId}/versions/{versionId:guid}")]
    public async Task<IActionResult> DeleteVersion(string moduleId, Guid versionId, CancellationToken ct)
    {
        var deleted = await _moduleService.DeleteVersionAsync(moduleId, versionId, ct);
        if (!deleted)
            return NotFound(new ErrorResponse("not_found", "Version not found."));

        return Ok(new StatusResponse("ok"));
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

    // ──────────────────────────────────────────────
    //  Variable definitions
    // ──────────────────────────────────────────────

    [HttpGet("{moduleId}/variables")]
    public async Task<IActionResult> GetVariableDefs(string moduleId, CancellationToken ct)
    {
        var defs = await _variableService.GetVariableDefsAsync(moduleId, ct);
        var items = defs.Select(v => new ModuleVariableDefItem(
            v.Name, v.Type, v.DefaultValue, v.Description, v.ServerCode is not null, v.ServerCode)).ToList();
        return Ok(items);
    }

    [HttpPut("{moduleId}/variables/{varName}")]
    public async Task<IActionResult> UpsertVariableDef(
        string moduleId, string varName,
        [FromBody] UpsertVariableDefRequest? request,
        CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        var result = await _variableService.UpsertVariableDefAsync(moduleId, varName, request, ct);
        if (result is null)
            return NotFound(new ErrorResponse("not_found", "Module not found."));

        return Ok(new ModuleVariableDefItem(
            result.Name, result.Type, result.DefaultValue, result.Description, result.ServerCode is not null, result.ServerCode));
    }

    [HttpDelete("{moduleId}/variables/{varName}")]
    public async Task<IActionResult> DeleteVariableDef(string moduleId, string varName, CancellationToken ct)
    {
        var deleted = await _variableService.DeleteVariableDefAsync(moduleId, varName, ct);
        if (!deleted)
            return NotFound(new ErrorResponse("not_found", "Variable definition not found."));

        return Ok(new StatusResponse("ok"));
    }

    // ──────────────────────────────────────────────
    //  Variable values (per assignment)
    // ──────────────────────────────────────────────

    [HttpGet("assignments/{assignmentId:guid}/variables")]
    public async Task<IActionResult> GetAssignmentVariables(Guid assignmentId, CancellationToken ct)
    {
        var items = await _variableService.GetVariableValuesWithSourceAsync(assignmentId, ct);
        return Ok(items);
    }

    [HttpPut("assignments/{assignmentId:guid}/variables/{varName}")]
    public async Task<IActionResult> SetAssignmentVariable(
        Guid assignmentId, string varName,
        [FromBody] SetVariableValueRequest? request,
        CancellationToken ct)
    {
        if (request is null)
            return BadRequest(new ErrorResponse("invalid_request", "Request body is required."));

        var ok = await _variableService.SetVariableValueAsync(assignmentId, varName, request.Value, ct);
        if (!ok)
            return NotFound(new ErrorResponse("not_found", "Assignment or variable not found."));

        return Ok(new StatusResponse("ok"));
    }

    [HttpDelete("assignments/{assignmentId:guid}/variables/{varName}")]
    public async Task<IActionResult> DeleteAssignmentVariable(
        Guid assignmentId, string varName, CancellationToken ct)
    {
        var deleted = await _variableService.DeleteVariableValueAsync(assignmentId, varName, ct);
        if (!deleted)
            return NotFound(new ErrorResponse("not_found", "Variable override not found."));

        return Ok(new StatusResponse("ok"));
    }
}
