using HomeIOT.Api.Data;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Services.Models;
using Microsoft.CodeAnalysis.CSharp.Scripting;
using Microsoft.CodeAnalysis.Scripting;
using Microsoft.EntityFrameworkCore;
using System.Text.Json;

namespace HomeIOT.Api.Services;

public sealed class ModuleServerCodeService : IModuleServerCodeService
{
    private static readonly ScriptOptions ScriptOptions = ScriptOptions.Default
        .WithImports(
            "System",
            "System.Collections.Generic",
            "System.Linq",
            "System.Threading.Tasks")
        .WithReferences(typeof(object).Assembly);

    private static readonly TimeSpan ExecutionTimeout = TimeSpan.FromSeconds(5);

    private readonly ApiDbContext _db;
    private readonly IModuleVariableService _variableService;
    private readonly ILogger<ModuleServerCodeService> _logger;

    public ModuleServerCodeService(
        ApiDbContext db,
        IModuleVariableService variableService,
        ILogger<ModuleServerCodeService> logger)
    {
        _db = db;
        _variableService = variableService;
        _logger = logger;
    }

    public async Task RunForModuleAsync(string deviceId, string moduleId, CancellationToken ct = default)
    {
        // Find the assignment for this device+module
        var assignment = await _db.ModuleAssignments
            .AsNoTracking()
            .Include(a => a.ModuleDefinition)
                .ThenInclude(d => d.VariableDefs)
            .Include(a => a.Device)
            .Where(a => a.Device.DeviceId == deviceId && a.ModuleDefinition.ModuleId == moduleId)
            .FirstOrDefaultAsync(ct);

        if (assignment is null)
            return;

        var varsWithCode = assignment.ModuleDefinition.VariableDefs
            .Where(v => !string.IsNullOrWhiteSpace(v.ServerCode))
            .ToList();

        if (varsWithCode.Count == 0)
            return;

        var dataAccess = new ModuleDataAccess(_db, deviceId);

        foreach (var varDef in varsWithCode)
        {
            await ExecuteVariableCodeAsync(assignment.Id, deviceId, moduleId, varDef, dataAccess, ct);
        }
    }

    private async Task ExecuteVariableCodeAsync(
        Guid assignmentId,
        string deviceId,
        string moduleId,
        ModuleVariableDefRecord varDef,
        ModuleDataAccess dataAccess,
        CancellationToken ct)
    {
        try
        {
            var scriptContext = new ModuleScriptContext
            {
                DeviceId = deviceId,
                ModuleId = moduleId,
                Data = dataAccess,
            };

            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(ExecutionTimeout);

            var result = await CSharpScript.EvaluateAsync<object?>(
                varDef.ServerCode!,
                ScriptOptions,
                globals: scriptContext,
                cancellationToken: cts.Token);

            var stringValue = result switch
            {
                null => null,
                string s => s,
                bool b => b ? "true" : "false",
                _ => result.ToString(),
            };

            await _variableService.UpsertComputedValueAsync(assignmentId, varDef.Name, stringValue, ct);

            _logger.LogDebug(
                "Server code executed for variable {VarName} on {DeviceId}/{ModuleId}: {Value}",
                varDef.Name, deviceId, moduleId, stringValue);
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning(
                "Server code timeout for variable {VarName} on {DeviceId}/{ModuleId}",
                varDef.Name, deviceId, moduleId);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex,
                "Server code failed for variable {VarName} on {DeviceId}/{ModuleId}",
                varDef.Name, deviceId, moduleId);
        }
    }
}
