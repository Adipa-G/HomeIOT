using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using HomeIOT.Api.Configuration;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Infrastructure;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace HomeIOT.Api.Services;

public sealed class ModuleService : IModuleService
{
    private static readonly JsonSerializerOptions HashJsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        WriteIndented = false,
    };

    private readonly ApiDbContext _db;
    private readonly string _packageRoot;
    private readonly ILogger<ModuleService> _logger;
    private readonly IModuleVariableService _variableService;

    public ModuleService(
        ApiDbContext db,
        IOptions<ModuleStorageOptions> storageOptions,
        IWebHostEnvironment environment,
        ILogger<ModuleService> logger,
        IModuleVariableService variableService)
    {
        _db = db;
        _logger = logger;
        _variableService = variableService;

        var configuredRoot = string.IsNullOrWhiteSpace(storageOptions.Value.PackageRoot)
            ? "../modules"
            : storageOptions.Value.PackageRoot;

        _packageRoot = Path.IsPathRooted(configuredRoot)
            ? Path.GetFullPath(configuredRoot)
            : Path.GetFullPath(Path.Combine(environment.ContentRootPath, configuredRoot));
    }

    // ──────────────────────────────────────────────
    //  Device-facing
    // ──────────────────────────────────────────────

    public async Task<ModuleAssignmentResponse?> GetAssignmentForDeviceAsync(
        string deviceId, string? lastAssignmentHash, CancellationToken ct = default)
    {
        var device = await _db.Devices
            .AsNoTracking()
            .FirstOrDefaultAsync(d => d.DeviceId == deviceId, ct);

        if (device is null)
            return null;

        var assignments = await _db.ModuleAssignments
            .AsNoTracking()
            .Include(a => a.ModuleDefinition)
            .Include(a => a.ModuleVersion)
            .Where(a => a.DeviceRecordId == device.Id)
            .OrderBy(a => a.ModuleDefinition.ModuleId)
            .ToListAsync(ct);

        var items = new List<ModuleAssignmentItem>();
        foreach (var a in assignments)
        {
            var variables = await _variableService.GetResolvedVariablesAsync(a.Id, ct);
            items.Add(new ModuleAssignmentItem(
                a.ModuleDefinition.ModuleId,
                a.ModuleVersion.Version,
                a.IntervalMs,
                a.TimeoutMs,
                a.Entrypoint,
                a.ModuleVersion.PackageHash,
                a.Enabled,
                variables.Count > 0 ? variables : null));
        }

        var hash = ComputeAssignmentHash(items);

        if (!string.IsNullOrWhiteSpace(lastAssignmentHash) &&
            string.Equals(hash, lastAssignmentHash, StringComparison.Ordinal))
        {
            return null; // 204 — unchanged
        }

        return new ModuleAssignmentResponse(hash, items);
    }

    public byte[]? GetPackage(string moduleId, string version)
    {
        var filePath = GetPackagePath(moduleId, version);
        if (filePath is null || !File.Exists(filePath))
        {
            _logger.LogWarning("Module package not found: {ModuleId}@{Version}", moduleId, version);
            return null;
        }

        return File.ReadAllBytes(filePath);
    }

    public async Task RecordResultAsync(ModuleResultRequest request, CancellationToken ct = default)
    {
        var record = new ModuleResultRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = request.DeviceId!,
            ModuleId = request.ModuleId!,
            ModuleVersion = request.ModuleVersion!,
            RunId = request.RunId!,
            StartedAtUtc = ParseUtc(request.StartedAtUtc),
            FinishedAtUtc = ParseUtc(request.FinishedAtUtc),
            ElapsedMs = request.ElapsedMs,
            Status = request.Status!,
            Output = request.Output is not null ? JsonSerializer.Serialize(request.Output) : null,
            VariableValues = request.VariableValues is not null ? JsonSerializer.Serialize(request.VariableValues) : null,
            ErrorMessage = request.ErrorMessage,
            ReceivedAtUtc = DateTimeOffset.UtcNow,
        };

        _db.ModuleResults.Add(record);
        await _db.SaveChangesAsync(ct);
    }

    public async Task RecordStatusAsync(ModuleStatusRequest request, CancellationToken ct = default)
    {
        var record = new ModuleStatusRecord
        {
            Id = Guid.NewGuid(),
            DeviceId = request.DeviceId!,
            ModuleId = request.ModuleId!,
            ModuleVersion = request.ModuleVersion!,
            Disabled = request.Disabled,
            DisabledReason = request.DisabledReason,
            FailedStartCount = request.FailedStartCount,
            DisabledAtUtc = string.IsNullOrWhiteSpace(request.DisabledAtUtc)
                ? null
                : ParseUtc(request.DisabledAtUtc),
            ReceivedAtUtc = DateTimeOffset.UtcNow,
        };

        _db.ModuleStatuses.Add(record);
        await _db.SaveChangesAsync(ct);
    }

    // ──────────────────────────────────────────────
    //  Admin-facing
    // ──────────────────────────────────────────────

    public async Task<List<ModuleListItem>> ListModulesAsync(CancellationToken ct = default)
    {
        return await _db.ModuleDefinitions
            .AsNoTracking()
            .OrderBy(m => m.ModuleId)
            .Select(m => new ModuleListItem(
                m.ModuleId,
                m.Description,
                m.DefaultEntrypoint,
                m.Versions.Count,
                m.Assignments.Count,
                EndpointValidation.ToUtcZ(m.CreatedAtUtc)))
            .ToListAsync(ct);
    }

    public async Task<ModuleDetailResponse?> GetModuleAsync(string moduleId, CancellationToken ct = default)
    {
        var module = await _db.ModuleDefinitions
            .AsNoTracking()
            .Include(m => m.Versions)
            .Include(m => m.Assignments)
                .ThenInclude(a => a.ModuleVersion)
            .Include(m => m.Assignments)
                .ThenInclude(a => a.Device)
            .Include(m => m.VariableDefs)
            .FirstOrDefaultAsync(m => m.ModuleId == moduleId, ct);

        if (module is null)
            return null;

        var versions = module.Versions
            .OrderByDescending(v => v.CreatedAtUtc)
            .Select(v => new ModuleVersionItem(
                v.Id,
                v.Version,
                v.PackageHash,
                v.PackageSizeBytes,
                EndpointValidation.ToUtcZ(v.CreatedAtUtc)))
            .ToList();

        var assignments = module.Assignments
            .OrderBy(a => a.Device.DeviceId)
            .Select(a => new ModuleAssignmentDetail(
                a.Id,
                a.Device.DeviceId,
                module.ModuleId,
                a.ModuleVersion.Version,
                a.IntervalMs,
                a.TimeoutMs,
                a.Entrypoint,
                a.Enabled,
                EndpointValidation.ToUtcZ(a.CreatedAtUtc),
                EndpointValidation.ToUtcZ(a.UpdatedAtUtc)))
            .ToList();

        var variableDefs = module.VariableDefs
            .OrderBy(v => v.Name)
            .Select(v => new ModuleVariableDefItem(
                v.Name,
                v.Type,
                v.DefaultValue,
                v.Description,
                v.ServerCode is not null,
                v.ServerCode))
            .ToList();

        return new ModuleDetailResponse(
            module.ModuleId,
            module.Description,
            module.DefaultEntrypoint,
            EndpointValidation.ToUtcZ(module.CreatedAtUtc),
            EndpointValidation.ToUtcZ(module.UpdatedAtUtc),
            versions,
            assignments,
            variableDefs);
    }

    public async Task<ModuleDefinitionRecord> CreateModuleAsync(
        CreateModuleRequest request, CancellationToken ct = default)
    {
        var record = new ModuleDefinitionRecord
        {
            Id = Guid.NewGuid(),
            ModuleId = request.ModuleId!.Trim(),
            Description = request.Description?.Trim(),
            DefaultEntrypoint = string.IsNullOrWhiteSpace(request.DefaultEntrypoint)
                ? "run"
                : request.DefaultEntrypoint.Trim(),
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };

        _db.ModuleDefinitions.Add(record);
        await _db.SaveChangesAsync(ct);
        return record;
    }

    public async Task<ModuleVersionRecord?> UploadVersionAsync(
        string moduleId, string version, Stream content, CancellationToken ct = default)
    {
        var module = await _db.ModuleDefinitions
            .FirstOrDefaultAsync(m => m.ModuleId == moduleId, ct);

        if (module is null)
            return null;

        // Read content and compute hash
        using var ms = new MemoryStream();
        await content.CopyToAsync(ms, ct);
        var bytes = ms.ToArray();
        var hash = ComputeSha256(bytes);

        // Save to filesystem
        var dir = Path.Combine(_packageRoot, moduleId);
        Directory.CreateDirectory(dir);
        var filePath = Path.Combine(dir, $"{version}.py");
        await File.WriteAllBytesAsync(filePath, bytes, ct);

        // Check for existing version (overwrite)
        var existing = await _db.ModuleVersions
            .FirstOrDefaultAsync(v => v.ModuleDefinitionId == module.Id && v.Version == version, ct);

        if (existing is not null)
        {
            existing.PackageHash = hash;
            existing.PackageSizeBytes = bytes.Length;
            existing.CreatedAtUtc = DateTimeOffset.UtcNow;
        }
        else
        {
            existing = new ModuleVersionRecord
            {
                Id = Guid.NewGuid(),
                ModuleDefinitionId = module.Id,
                Version = version.Trim(),
                PackageHash = hash,
                PackageSizeBytes = bytes.Length,
                CreatedAtUtc = DateTimeOffset.UtcNow,
            };
            _db.ModuleVersions.Add(existing);
        }

        module.UpdatedAtUtc = DateTimeOffset.UtcNow;
        await _db.SaveChangesAsync(ct);
        return existing;
    }

    public async Task<ModuleAssignmentRecord?> AssignModuleAsync(
        string moduleId, AssignModuleRequest request, CancellationToken ct = default)
    {
        var module = await _db.ModuleDefinitions
            .Include(m => m.Versions)
            .FirstOrDefaultAsync(m => m.ModuleId == moduleId, ct);

        if (module is null)
            return null;

        var device = await _db.Devices
            .FirstOrDefaultAsync(d => d.DeviceId == request.DeviceId, ct);

        if (device is null)
            return null;

        var version = module.Versions
            .FirstOrDefault(v => v.Version == request.Version);

        if (version is null)
            return null;

        // Check for duplicate
        var existing = await _db.ModuleAssignments
            .FirstOrDefaultAsync(a => a.DeviceRecordId == device.Id && a.ModuleDefinitionId == module.Id, ct);

        if (existing is not null)
        {
            // Update in place
            existing.ModuleVersionId = version.Id;
            existing.IntervalMs = request.IntervalMs ?? module.Assignments.FirstOrDefault()?.IntervalMs ?? 60000;
            existing.TimeoutMs = request.TimeoutMs ?? 5000;
            existing.Entrypoint = request.Entrypoint ?? module.DefaultEntrypoint;
            existing.Enabled = request.Enabled;
            existing.UpdatedAtUtc = DateTimeOffset.UtcNow;
            await _db.SaveChangesAsync(ct);
            return existing;
        }

        var assignment = new ModuleAssignmentRecord
        {
            Id = Guid.NewGuid(),
            DeviceRecordId = device.Id,
            ModuleDefinitionId = module.Id,
            ModuleVersionId = version.Id,
            IntervalMs = request.IntervalMs ?? 60000,
            TimeoutMs = request.TimeoutMs ?? 5000,
            Entrypoint = request.Entrypoint ?? module.DefaultEntrypoint,
            Enabled = request.Enabled,
            CreatedAtUtc = DateTimeOffset.UtcNow,
            UpdatedAtUtc = DateTimeOffset.UtcNow,
        };

        _db.ModuleAssignments.Add(assignment);
        await _db.SaveChangesAsync(ct);
        return assignment;
    }

    public async Task<ModuleAssignmentRecord?> UpdateAssignmentAsync(
        Guid assignmentId, UpdateAssignmentRequest request, CancellationToken ct = default)
    {
        var assignment = await _db.ModuleAssignments
            .Include(a => a.ModuleDefinition)
                .ThenInclude(m => m.Versions)
            .FirstOrDefaultAsync(a => a.Id == assignmentId, ct);

        if (assignment is null)
            return null;

        if (!string.IsNullOrWhiteSpace(request.Version))
        {
            var version = assignment.ModuleDefinition.Versions
                .FirstOrDefault(v => v.Version == request.Version);

            if (version is null)
                return null;

            assignment.ModuleVersionId = version.Id;
        }

        if (request.IntervalMs.HasValue)
            assignment.IntervalMs = request.IntervalMs.Value;

        if (request.TimeoutMs.HasValue)
            assignment.TimeoutMs = request.TimeoutMs.Value;

        if (request.Entrypoint is not null)
            assignment.Entrypoint = request.Entrypoint;

        if (request.Enabled.HasValue)
            assignment.Enabled = request.Enabled.Value;

        assignment.UpdatedAtUtc = DateTimeOffset.UtcNow;
        await _db.SaveChangesAsync(ct);
        return assignment;
    }

    public async Task<bool> RemoveAssignmentAsync(Guid assignmentId, CancellationToken ct = default)
    {
        var assignment = await _db.ModuleAssignments
            .FirstOrDefaultAsync(a => a.Id == assignmentId, ct);

        if (assignment is null)
            return false;

        _db.ModuleAssignments.Remove(assignment);
        await _db.SaveChangesAsync(ct);
        return true;
    }

    // ──────────────────────────────────────────────
    //  Admin observability
    // ──────────────────────────────────────────────

    public async Task<PaginatedResponse<ModuleResultListItem>> QueryResultsAsync(
        int offset, int limit, DateTimeOffset? from, DateTimeOffset? to,
        string? deviceId, string? moduleId, string? status, CancellationToken ct = default)
    {
        var query = _db.ModuleResults.AsNoTracking().AsQueryable();

        if (!string.IsNullOrWhiteSpace(deviceId))
            query = query.Where(r => r.DeviceId == deviceId);
        if (!string.IsNullOrWhiteSpace(moduleId))
            query = query.Where(r => r.ModuleId == moduleId);
        if (!string.IsNullOrWhiteSpace(status))
            query = query.Where(r => r.Status == status);
        if (from.HasValue)
            query = query.Where(r => r.ReceivedAtUtc >= from.Value);
        if (to.HasValue)
            query = query.Where(r => r.ReceivedAtUtc <= to.Value);

        var total = await query.CountAsync(ct);

        var items = await query
            .OrderByDescending(r => r.ReceivedAtUtc)
            .Skip(offset)
            .Take(limit)
            .Select(r => new ModuleResultListItem(
                r.Id,
                r.DeviceId,
                r.ModuleId,
                r.ModuleVersion,
                r.RunId,
                r.Status,
                r.ElapsedMs,
                r.ErrorMessage,
                r.Output,
                r.VariableValues,
                EndpointValidation.ToUtcZ(r.StartedAtUtc),
                EndpointValidation.ToUtcZ(r.FinishedAtUtc)))
            .ToListAsync(ct);

        return new PaginatedResponse<ModuleResultListItem>(items, total, offset, limit);
    }

    public async Task<PaginatedResponse<ModuleStatusListItem>> QueryStatusesAsync(
        int offset, int limit, string? deviceId, string? moduleId, CancellationToken ct = default)
    {
        var query = _db.ModuleStatuses.AsNoTracking().AsQueryable();

        if (!string.IsNullOrWhiteSpace(deviceId))
            query = query.Where(s => s.DeviceId == deviceId);
        if (!string.IsNullOrWhiteSpace(moduleId))
            query = query.Where(s => s.ModuleId == moduleId);

        var total = await query.CountAsync(ct);

        var items = await query
            .OrderByDescending(s => s.ReceivedAtUtc)
            .Skip(offset)
            .Take(limit)
            .Select(s => new ModuleStatusListItem(
                s.Id,
                s.DeviceId,
                s.ModuleId,
                s.ModuleVersion,
                s.Disabled,
                s.DisabledReason,
                s.FailedStartCount,
                s.DisabledAtUtc.HasValue ? EndpointValidation.ToUtcZ(s.DisabledAtUtc.Value) : null,
                EndpointValidation.ToUtcZ(s.ReceivedAtUtc)))
            .ToListAsync(ct);

        return new PaginatedResponse<ModuleStatusListItem>(items, total, offset, limit);
    }

    public async Task<bool> UpdateModuleAsync(string moduleId, UpdateModuleRequest request, CancellationToken ct = default)
    {
        var module = await _db.ModuleDefinitions.FirstOrDefaultAsync(m => m.ModuleId == moduleId, ct);
        if (module is null)
            return false;

        if (request.Description is not null)
            module.Description = request.Description;
        if (request.DefaultEntrypoint is not null)
            module.DefaultEntrypoint = request.DefaultEntrypoint;

        module.UpdatedAtUtc = DateTimeOffset.UtcNow;
        await _db.SaveChangesAsync(ct);
        return true;
    }

    public async Task<bool> DeleteModuleAsync(string moduleId, CancellationToken ct = default)
    {
        var module = await _db.ModuleDefinitions
            .Include(m => m.Versions)
            .FirstOrDefaultAsync(m => m.ModuleId == moduleId, ct);

        if (module is null)
            return false;

        // Remove assignments
        var assignments = await _db.ModuleAssignments
            .Where(a => a.ModuleDefinitionId == module.Id)
            .ToListAsync(ct);
        _db.ModuleAssignments.RemoveRange(assignments);

        // Remove versions
        _db.ModuleVersions.RemoveRange(module.Versions);

        // Remove definition
        _db.ModuleDefinitions.Remove(module);

        await _db.SaveChangesAsync(ct);

        // Remove package files
        var modulePath = Path.Combine(_packageRoot, moduleId);
        if (Directory.Exists(modulePath))
            Directory.Delete(modulePath, recursive: true);

        return true;
    }

    public async Task<bool> DeleteVersionAsync(string moduleId, Guid versionId, CancellationToken ct = default)
    {
        var module = await _db.ModuleDefinitions.AsNoTracking()
            .FirstOrDefaultAsync(m => m.ModuleId == moduleId, ct);

        if (module is null)
            return false;

        var version = await _db.ModuleVersions
            .FirstOrDefaultAsync(v => v.Id == versionId && v.ModuleDefinitionId == module.Id, ct);

        if (version is null)
            return false;

        _db.ModuleVersions.Remove(version);
        await _db.SaveChangesAsync(ct);

        // Remove package file
        var packagePath = Path.Combine(_packageRoot, moduleId, $"{version.Version}.py");
        if (File.Exists(packagePath))
            File.Delete(packagePath);

        return true;
    }

    // ──────────────────────────────────────────────
    //  Private helpers
    // ──────────────────────────────────────────────

    private string? GetPackagePath(string moduleId, string version)
    {
        if (!IsSafeToken(moduleId) || !IsSafeVersion(version))
            return null;

        var filePath = Path.GetFullPath(Path.Combine(_packageRoot, moduleId, $"{version}.py"));

        // Prevent directory traversal
        if (!filePath.StartsWith(_packageRoot, StringComparison.OrdinalIgnoreCase))
            return null;

        return filePath;
    }

    private static string ComputeAssignmentHash(List<ModuleAssignmentItem> items)
    {
        var json = JsonSerializer.Serialize(items, HashJsonOptions);
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(json));
        return $"sha256:{Convert.ToHexString(bytes).ToLowerInvariant()}";
    }

    private static string ComputeSha256(byte[] data)
    {
        var hash = SHA256.HashData(data);
        return $"sha256:{Convert.ToHexString(hash).ToLowerInvariant()}";
    }

    private static DateTimeOffset ParseUtc(string? value)
    {
        return DateTimeOffset.TryParse(value, out var result)
            ? result.ToUniversalTime()
            : DateTimeOffset.UtcNow;
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
