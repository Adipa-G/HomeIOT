using HomeIOT.Api.Contracts;

namespace HomeIOT.Api.Services;

public interface IDeviceAdminService
{
    Task<PaginatedResponse<DeviceListItem>> ListDevicesAsync(
        int offset, int limit, string? platform, string? mode, string? search, CancellationToken ct = default);

    Task<DeviceDetailResponse?> GetDeviceAsync(string deviceId, CancellationToken ct = default);

    Task<bool> UpdateDeviceModeAsync(string deviceId, string mode, CancellationToken ct = default);

    Task<bool> DeleteDeviceAsync(string deviceId, CancellationToken ct = default);

    Task<PaginatedResponse<HeartbeatListItem>> GetHeartbeatsAsync(
        string deviceId, int offset, int limit, DateTimeOffset? from, DateTimeOffset? to, CancellationToken ct = default);

    Task<PaginatedResponse<LogBatchListItem>> GetLogsAsync(
        string deviceId, int offset, int limit, DateTimeOffset? from, DateTimeOffset? to, CancellationToken ct = default);
}
