using HomeIOT.Api.Services.Models;

namespace HomeIOT.Api.Services.Models;

public interface IModuleDataAccess
{
    Task<List<ModuleResultEntry>> QueryResultsAsync(
        string moduleId, DateTimeOffset from, DateTimeOffset to, CancellationToken ct = default);

    Task<ModuleResultEntry?> GetLatestResultAsync(
        string moduleId, CancellationToken ct = default);
}
