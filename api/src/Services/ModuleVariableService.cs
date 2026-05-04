using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Infrastructure;
using Microsoft.EntityFrameworkCore;

namespace HomeIOT.Api.Services;

public sealed class ModuleVariableService : IModuleVariableService
{
    private static readonly HashSet<string> ValidTypes = new(StringComparer.OrdinalIgnoreCase)
        { "string", "number", "boolean", "json" };

    private readonly ApiDbContext _db;

    public ModuleVariableService(ApiDbContext db)
    {
        _db = db;
    }

    // ──────────────────────────────────────────────
    //  Variable definitions
    // ──────────────────────────────────────────────

    public async Task<List<ModuleVariableDefRecord>> GetVariableDefsAsync(
        string moduleId, CancellationToken ct = default)
    {
        var def = await _db.ModuleDefinitions
            .AsNoTracking()
            .FirstOrDefaultAsync(d => d.ModuleId == moduleId, ct);

        if (def is null)
            return [];

        return await _db.ModuleVariableDefs
            .AsNoTracking()
            .Where(v => v.ModuleDefinitionId == def.Id)
            .OrderBy(v => v.Name)
            .ToListAsync(ct);
    }

    public async Task<ModuleVariableDefRecord?> UpsertVariableDefAsync(
        string moduleId, string name, UpsertVariableDefRequest request, CancellationToken ct = default)
    {
        var def = await _db.ModuleDefinitions
            .FirstOrDefaultAsync(d => d.ModuleId == moduleId, ct);

        if (def is null)
            return null;

        var type = (request.Type ?? "string").ToLowerInvariant();
        if (!ValidTypes.Contains(type))
            type = "string";

        var existing = await _db.ModuleVariableDefs
            .FirstOrDefaultAsync(v => v.ModuleDefinitionId == def.Id && v.Name == name, ct);

        var now = DateTimeOffset.UtcNow;

        if (existing is not null)
        {
            existing.Type = type;
            existing.DefaultValue = request.DefaultValue;
            existing.Description = request.Description;
            existing.ServerCode = request.ServerCode;
            existing.UpdatedAtUtc = now;
        }
        else
        {
            existing = new ModuleVariableDefRecord
            {
                Id = Guid.NewGuid(),
                ModuleDefinitionId = def.Id,
                Name = name,
                Type = type,
                DefaultValue = request.DefaultValue,
                Description = request.Description,
                ServerCode = request.ServerCode,
                CreatedAtUtc = now,
                UpdatedAtUtc = now,
            };
            _db.ModuleVariableDefs.Add(existing);
        }

        await _db.SaveChangesAsync(ct);
        return existing;
    }

    public async Task<bool> DeleteVariableDefAsync(
        string moduleId, string name, CancellationToken ct = default)
    {
        var def = await _db.ModuleDefinitions
            .FirstOrDefaultAsync(d => d.ModuleId == moduleId, ct);

        if (def is null)
            return false;

        var record = await _db.ModuleVariableDefs
            .FirstOrDefaultAsync(v => v.ModuleDefinitionId == def.Id && v.Name == name, ct);

        if (record is null)
            return false;

        _db.ModuleVariableDefs.Remove(record);
        await _db.SaveChangesAsync(ct);
        return true;
    }

    // ──────────────────────────────────────────────
    //  Variable values (per assignment)
    // ──────────────────────────────────────────────

    public async Task<Dictionary<string, string?>> GetResolvedVariablesAsync(
        Guid assignmentId, CancellationToken ct = default)
    {
        var assignment = await _db.ModuleAssignments
            .AsNoTracking()
            .Include(a => a.ModuleDefinition)
                .ThenInclude(d => d.VariableDefs)
            .Include(a => a.VariableValues)
            .FirstOrDefaultAsync(a => a.Id == assignmentId, ct);

        if (assignment is null)
            return [];

        var result = new Dictionary<string, string?>(StringComparer.Ordinal);

        foreach (var varDef in assignment.ModuleDefinition.VariableDefs)
        {
            var stored = assignment.VariableValues
                .FirstOrDefault(v => v.VariableName == varDef.Name);

            // Resolution: manual override (ComputedByServer=false) > server-computed > default
            result[varDef.Name] = stored?.Value ?? varDef.DefaultValue;
        }

        return result;
    }

    public async Task<List<ModuleVariableValueItem>> GetVariableValuesWithSourceAsync(
        Guid assignmentId, CancellationToken ct = default)
    {
        var assignment = await _db.ModuleAssignments
            .AsNoTracking()
            .Include(a => a.ModuleDefinition)
                .ThenInclude(d => d.VariableDefs)
            .Include(a => a.VariableValues)
            .FirstOrDefaultAsync(a => a.Id == assignmentId, ct);

        if (assignment is null)
            return [];

        var items = new List<ModuleVariableValueItem>();

        foreach (var varDef in assignment.ModuleDefinition.VariableDefs.OrderBy(v => v.Name))
        {
            var stored = assignment.VariableValues
                .FirstOrDefault(v => v.VariableName == varDef.Name);

            string source;
            string? value;
            string? lastComputedAtUtc = null;

            if (stored is not null && !stored.ComputedByServer)
            {
                source = "override";
                value = stored.Value;
            }
            else if (stored is not null && stored.ComputedByServer)
            {
                source = "server_computed";
                value = stored.Value;
                lastComputedAtUtc = stored.LastComputedAtUtc.HasValue
                    ? EndpointValidation.ToUtcZ(stored.LastComputedAtUtc.Value)
                    : null;
            }
            else
            {
                source = "default";
                value = varDef.DefaultValue;
            }

            items.Add(new ModuleVariableValueItem(varDef.Name, value, source, lastComputedAtUtc));
        }

        return items;
    }

    public async Task<bool> SetVariableValueAsync(
        Guid assignmentId, string variableName, string? value, CancellationToken ct = default)
    {
        var assignment = await _db.ModuleAssignments
            .Include(a => a.ModuleDefinition)
                .ThenInclude(d => d.VariableDefs)
            .FirstOrDefaultAsync(a => a.Id == assignmentId, ct);

        if (assignment is null)
            return false;

        var varDefExists = assignment.ModuleDefinition.VariableDefs
            .Any(v => v.Name == variableName);

        if (!varDefExists)
            return false;

        var existing = await _db.ModuleVariableValues
            .FirstOrDefaultAsync(v => v.ModuleAssignmentId == assignmentId && v.VariableName == variableName, ct);

        if (existing is not null)
        {
            existing.Value = value;
            existing.ComputedByServer = false;
            existing.LastComputedAtUtc = null;
        }
        else
        {
            _db.ModuleVariableValues.Add(new ModuleVariableValueRecord
            {
                Id = Guid.NewGuid(),
                ModuleAssignmentId = assignmentId,
                VariableName = variableName,
                Value = value,
                ComputedByServer = false,
                LastComputedAtUtc = null,
            });
        }

        await _db.SaveChangesAsync(ct);
        return true;
    }

    public async Task<bool> DeleteVariableValueAsync(
        Guid assignmentId, string variableName, CancellationToken ct = default)
    {
        var existing = await _db.ModuleVariableValues
            .FirstOrDefaultAsync(v => v.ModuleAssignmentId == assignmentId && v.VariableName == variableName, ct);

        if (existing is null)
            return false;

        _db.ModuleVariableValues.Remove(existing);
        await _db.SaveChangesAsync(ct);
        return true;
    }

    public async Task UpsertComputedValueAsync(
        Guid assignmentId, string variableName, string? value, CancellationToken ct = default)
    {
        var existing = await _db.ModuleVariableValues
            .FirstOrDefaultAsync(v => v.ModuleAssignmentId == assignmentId && v.VariableName == variableName, ct);

        var now = DateTimeOffset.UtcNow;

        if (existing is not null)
        {
            // Only overwrite if this is not a manual override
            if (existing.ComputedByServer)
            {
                existing.Value = value;
                existing.LastComputedAtUtc = now;
            }
        }
        else
        {
            _db.ModuleVariableValues.Add(new ModuleVariableValueRecord
            {
                Id = Guid.NewGuid(),
                ModuleAssignmentId = assignmentId,
                VariableName = variableName,
                Value = value,
                ComputedByServer = true,
                LastComputedAtUtc = now,
            });
        }

        await _db.SaveChangesAsync(ct);
    }
}
