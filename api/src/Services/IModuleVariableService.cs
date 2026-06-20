using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data.Entities;

namespace HomeIOT.Api.Services;

public interface IModuleVariableService
{
    Task<List<ModuleVariableDefRecord>> GetVariableDefsAsync(string moduleId, CancellationToken ct = default);
    Task<ModuleVariableDefRecord?> UpsertVariableDefAsync(string moduleId, string name, UpsertVariableDefRequest request, CancellationToken ct = default);
    Task<bool> DeleteVariableDefAsync(string moduleId, string name, CancellationToken ct = default);

    Task<Dictionary<string, string?>> GetResolvedVariablesAsync(Guid assignmentId, CancellationToken ct = default);
    Task<List<ModuleVariableValueItem>> GetVariableValuesWithSourceAsync(Guid assignmentId, CancellationToken ct = default);
    Task<bool> SetVariableValueAsync(Guid assignmentId, string variableName, string? value, CancellationToken ct = default);
    Task<bool> DeleteVariableValueAsync(Guid assignmentId, string variableName, CancellationToken ct = default);
    Task UpsertComputedValueAsync(Guid assignmentId, string variableName, string? value, CancellationToken ct = default);

    Task<List<ModuleVariableVisualizationRecord>> GetVisualizationsForVariableAsync(string moduleId, string variableName, CancellationToken ct = default);
    Task<ModuleVariableVisualizationRecord?> UpsertVisualizationAsync(string moduleId, string variableName, string vizId, UpsertModuleVariableVisualizationRequest request, CancellationToken ct = default);
    Task<bool> DeleteVisualizationAsync(string moduleId, string variableName, Guid vizId, CancellationToken ct = default);
    Task<object?> InferJsonSchemaAsync(string moduleId, string variableName, CancellationToken ct = default);
}
