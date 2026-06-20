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
            existing.ControlType = request.ControlType;
            existing.ControlOptions = request.ControlOptions != null 
                ? System.Text.Json.JsonSerializer.Serialize(request.ControlOptions)
                : null;
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
                ControlType = request.ControlType,
                ControlOptions = request.ControlOptions != null 
                    ? System.Text.Json.JsonSerializer.Serialize(request.ControlOptions)
                    : null,
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

    // ──────────────────────────────────────────────
    //  Visualizations & Schema Inference
    // ──────────────────────────────────────────────

    public async Task<List<ModuleVariableVisualizationRecord>> GetVisualizationsForVariableAsync(
        string moduleId, string variableName, CancellationToken ct = default)
    {
        var def = await _db.ModuleDefinitions
            .AsNoTracking()
            .FirstOrDefaultAsync(d => d.ModuleId == moduleId, ct);

        if (def is null)
            return [];

        var varDef = await _db.ModuleVariableDefs
            .AsNoTracking()
            .FirstOrDefaultAsync(v => v.ModuleDefinitionId == def.Id && v.Name == variableName, ct);

        if (varDef is null)
            return [];

        return await _db.ModuleVariableVisualizations
            .AsNoTracking()
            .Where(v => v.ModuleVariableDefId == varDef.Id)
            .OrderBy(v => v.DisplayName)
            .ToListAsync(ct);
    }

    public async Task<ModuleVariableVisualizationRecord?> UpsertVisualizationAsync(
        string moduleId, string variableName, string vizId, UpsertModuleVariableVisualizationRequest request, CancellationToken ct = default)
    {
        var def = await _db.ModuleDefinitions
            .FirstOrDefaultAsync(d => d.ModuleId == moduleId, ct);

        if (def is null)
            return null;

        var varDef = await _db.ModuleVariableDefs
            .FirstOrDefaultAsync(v => v.ModuleDefinitionId == def.Id && v.Name == variableName, ct);

        if (varDef is null)
            return null;

        var existing = vizId != "new"
            ? await _db.ModuleVariableVisualizations
                .FirstOrDefaultAsync(v => v.Id == Guid.Parse(vizId), ct)
            : null;

        var now = DateTimeOffset.UtcNow;

        if (existing is not null)
        {
            existing.JsonPath = request.JsonPath;
            existing.DisplayName = request.DisplayName;
            existing.VisualizationType = request.VisualizationType;
            existing.VisualizationConfig = request.VisualizationConfig != null
                ? System.Text.Json.JsonSerializer.Serialize(request.VisualizationConfig)
                : null;
            existing.UpdatedAtUtc = now;
        }
        else
        {
            existing = new ModuleVariableVisualizationRecord
            {
                Id = Guid.NewGuid(),
                ModuleVariableDefId = varDef.Id,
                JsonPath = request.JsonPath,
                DisplayName = request.DisplayName,
                VisualizationType = request.VisualizationType,
                VisualizationConfig = request.VisualizationConfig != null
                    ? System.Text.Json.JsonSerializer.Serialize(request.VisualizationConfig)
                    : null,
                CreatedAtUtc = now,
                UpdatedAtUtc = now,
            };
            _db.ModuleVariableVisualizations.Add(existing);
        }

        await _db.SaveChangesAsync(ct);
        return existing;
    }

    public async Task<bool> DeleteVisualizationAsync(
        string moduleId, string variableName, Guid vizId, CancellationToken ct = default)
    {
        var def = await _db.ModuleDefinitions
            .FirstOrDefaultAsync(d => d.ModuleId == moduleId, ct);

        if (def is null)
            return false;

        var varDef = await _db.ModuleVariableDefs
            .FirstOrDefaultAsync(v => v.ModuleDefinitionId == def.Id && v.Name == variableName, ct);

        if (varDef is null)
            return false;

        var viz = await _db.ModuleVariableVisualizations
            .FirstOrDefaultAsync(v => v.Id == vizId && v.ModuleVariableDefId == varDef.Id, ct);

        if (viz is null)
            return false;

        _db.ModuleVariableVisualizations.Remove(viz);
        await _db.SaveChangesAsync(ct);
        return true;
    }

    public async Task<object?> InferJsonSchemaAsync(
        string moduleId, string variableName, CancellationToken ct = default)
    {
        var def = await _db.ModuleDefinitions
            .AsNoTracking()
            .FirstOrDefaultAsync(d => d.ModuleId == moduleId, ct);

        if (def is null)
            return null;

        var varDef = await _db.ModuleVariableDefs
            .AsNoTracking()
            .FirstOrDefaultAsync(v => v.ModuleDefinitionId == def.Id && v.Name == variableName, ct);

        if (varDef is null)
            return null;

        // Get latest execution result for this module
        var latestResult = await _db.ModuleResults
            .AsNoTracking()
            .Where(r => r.ModuleId == moduleId)
            .OrderByDescending(r => r.FinishedAtUtc)
            .FirstOrDefaultAsync(ct);

        if (latestResult is null)
            return null;

        // For OUTPUT variables (control_type is null), infer schema from the Output field
        // Return the schema of the entire output (not just the variable's value), since JSON Path is used to extract specific fields
        if (string.IsNullOrEmpty(varDef.ControlType) && !string.IsNullOrEmpty(latestResult.Output))
        {
            try
            {
                var output = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(latestResult.Output);
                if (output is null || output.Count == 0)
                    return null;

                var schema = InferSchemaFromValue(output);
               
                // Update the inferred schema in the database
                var varDefForUpdate = await _db.ModuleVariableDefs
                    .FirstOrDefaultAsync(v => v.Id == varDef.Id, ct);
                if (varDefForUpdate is not null)
                {
                    varDefForUpdate.InferredJsonSchema = System.Text.Json.JsonSerializer.Serialize(schema);
                    varDefForUpdate.UpdatedAtUtc = DateTimeOffset.UtcNow;
                    await _db.SaveChangesAsync(ct);
                }

                return schema;
            }
            catch
            {
                return null;
            }
        }
        
        // For INPUT variables (control_type is not null), infer schema from VariableValues
        if (!string.IsNullOrEmpty(varDef.ControlType) && !string.IsNullOrEmpty(latestResult.VariableValues))
        {
            try
            {
                var variableValues = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(latestResult.VariableValues);
                if (variableValues is null || !variableValues.ContainsKey(variableName))
                    return null;

                var value = variableValues[variableName];
                
                var schema = InferSchemaFromValue(value);
                
                // Update the inferred schema in the database
                var varDefForUpdate = await _db.ModuleVariableDefs
                    .FirstOrDefaultAsync(v => v.Id == varDef.Id, ct);
                if (varDefForUpdate is not null)
                {
                    varDefForUpdate.InferredJsonSchema = System.Text.Json.JsonSerializer.Serialize(schema);
                    varDefForUpdate.UpdatedAtUtc = DateTimeOffset.UtcNow;
                    await _db.SaveChangesAsync(ct);
                }

                return schema;
            }
            catch
            {
                return null;
            }
        }

        return null;
    }

    private static object InferSchemaFromValue(object value)
    {
        if (value is null)
            return new { };

        if (value is string)
            return "string";

        if (value is System.Text.Json.JsonElement jsonElement)
        {
            return jsonElement.ValueKind switch
            {
                System.Text.Json.JsonValueKind.Object => 
                    jsonElement.EnumerateObject()
                        .ToDictionary(
                            p => p.Name,
                            p => InferSchemaFromValue(p.Value) as object),
                System.Text.Json.JsonValueKind.Array => "array",
                System.Text.Json.JsonValueKind.String => "string",
                System.Text.Json.JsonValueKind.Number => "number",
                System.Text.Json.JsonValueKind.True or System.Text.Json.JsonValueKind.False => "boolean",
                System.Text.Json.JsonValueKind.Null => "null",
                _ => "unknown"
            };
        }

        var type = value.GetType();
        
        // Handle Dictionary - recursively infer schema for each property
        if (type.IsGenericType && type.GetGenericTypeDefinition() == typeof(Dictionary<,>))
        {
            if (value is Dictionary<string, object> dict)
            {
                return dict.ToDictionary(
                    kvp => kvp.Key,
                    kvp => InferSchemaFromValue(kvp.Value) as object);
            }
        }

        // Handle List - return "array"
        if (type.IsGenericType && type.GetGenericTypeDefinition() == typeof(List<>))
            return "array";

        return type switch
        {
            _ when type == typeof(int) || type == typeof(long) || type == typeof(double) || type == typeof(decimal) => "number",
            _ when type == typeof(bool) => "boolean",
            _ => "unknown"
        };
    }

    public static string? ExtractValueAtJsonPath(string? jsonValue, string jsonPath)
    {
        if (string.IsNullOrEmpty(jsonValue) || string.IsNullOrEmpty(jsonPath))
            return null;

        try
        {
            // If jsonPath is just a simple key, it's a flat variable
            // Otherwise it's in the form "parent.child.field"
            var parts = jsonPath.Split('.');
            object? current = System.Text.Json.JsonSerializer.Deserialize<object>(jsonValue);

            foreach (var part in parts)
            {
                if (current is System.Text.Json.JsonElement jsonElement)
                {
                    if (jsonElement.ValueKind == System.Text.Json.JsonValueKind.Object &&
                        jsonElement.TryGetProperty(part, out var property))
                    {
                        current = property;
                    }
                    else
                    {
                        return null;
                    }
                }
                else if (current is Dictionary<string, object> dict && dict.ContainsKey(part))
                {
                    current = dict[part];
                }
                else
                {
                    return null;
                }
            }

            if (current is System.Text.Json.JsonElement finalElement)
                return finalElement.GetRawText();

            return current?.ToString();
        }
        catch
        {
            return null;
        }
    }
}

