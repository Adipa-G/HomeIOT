namespace HomeIOT.Api.Services;

public interface IModuleServerCodeService
{
    /// <summary>
    /// Executes server-side Roslyn scripts for all variables with server_code attached
    /// to modules that were just executed by the given device, and persists results.
    /// </summary>
    Task RunForModuleAsync(string deviceId, string moduleId, CancellationToken ct = default);
}
