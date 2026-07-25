using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data.Entities;

namespace HomeIOT.Api.Services;

public interface IModuleService
{
    // Device-facing
    Task<ModuleAssignmentResponse?> GetAssignmentForDeviceAsync(string deviceId, string? lastAssignmentHash, CancellationToken ct = default);
    byte[]? GetPackage(string moduleId, string version);
    Task RecordResultAsync(ModuleResultRequest request, CancellationToken ct = default);
    Task RecordStatusAsync(ModuleStatusRequest request, CancellationToken ct = default);

    // Admin-facing
    Task<List<ModuleListItem>> ListModulesAsync(CancellationToken ct = default);
    Task<ModuleDetailResponse?> GetModuleAsync(string moduleId, CancellationToken ct = default);
    Task<ModuleDefinitionRecord> CreateModuleAsync(CreateModuleRequest request, CancellationToken ct = default);
    Task<ModuleVersionRecord?> UploadVersionAsync(string moduleId, string version, Stream content, CancellationToken ct = default);
    Task<ModuleAssignmentRecord?> AssignModuleAsync(string moduleId, AssignModuleRequest request, CancellationToken ct = default);
    Task<ModuleAssignmentRecord?> UpdateAssignmentAsync(Guid assignmentId, UpdateAssignmentRequest request, CancellationToken ct = default);
    Task<bool> RemoveAssignmentAsync(Guid assignmentId, CancellationToken ct = default);

    // Admin observability
    Task<PaginatedResponse<ModuleResultListItem>> QueryResultsAsync(
        int offset, int limit, DateTimeOffset? from, DateTimeOffset? to,
        string? deviceId, string? moduleId, string? status, CancellationToken ct = default);

    Task<PaginatedResponse<ModuleStatusListItem>> QueryStatusesAsync(
        int offset, int limit, string? deviceId, string? moduleId, CancellationToken ct = default);

    Task<bool> UpdateModuleAsync(string moduleId, UpdateModuleRequest request, CancellationToken ct = default);
    Task<bool> DeleteModuleAsync(string moduleId, CancellationToken ct = default);
    Task<bool> DeleteVersionAsync(string moduleId, string version, CancellationToken ct = default);

    // Dashboard
    Task<List<DashboardModuleItem>> GetDashboardModulesAsync(CancellationToken ct = default);
}
