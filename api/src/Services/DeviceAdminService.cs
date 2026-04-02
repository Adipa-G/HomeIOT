using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Infrastructure;
using Microsoft.EntityFrameworkCore;

namespace HomeIOT.Api.Services;

public sealed class DeviceAdminService : IDeviceAdminService
{
    private readonly ApiDbContext _db;

    public DeviceAdminService(ApiDbContext db)
    {
        _db = db;
    }

    public async Task<PaginatedResponse<DeviceListItem>> ListDevicesAsync(
        int offset, int limit, string? platform, string? mode, string? search, CancellationToken ct = default)
    {
        var query = _db.Devices.AsNoTracking().AsQueryable();

        if (!string.IsNullOrWhiteSpace(platform))
            query = query.Where(d => d.Platform == platform);

        if (!string.IsNullOrWhiteSpace(mode))
            query = query.Where(d => d.Mode == mode);

        if (!string.IsNullOrWhiteSpace(search))
            query = query.Where(d => d.DeviceId.Contains(search));

        var total = await query.CountAsync(ct);

        var items = await query
            .OrderBy(d => d.DeviceId)
            .Skip(offset)
            .Take(limit)
            .Select(d => new DeviceListItem(
                d.DeviceId,
                d.Platform,
                d.Version,
                d.Ip,
                d.Mode,
                d.LastHeartbeatAtUtc.HasValue ? EndpointValidation.ToUtcZ(d.LastHeartbeatAtUtc.Value) : null,
                EndpointValidation.ToUtcZ(d.CreatedAtUtc)))
            .ToListAsync(ct);

        return new PaginatedResponse<DeviceListItem>(items, total, offset, limit);
    }

    public async Task<DeviceDetailResponse?> GetDeviceAsync(string deviceId, CancellationToken ct = default)
    {
        var device = await _db.Devices
            .AsNoTracking()
            .FirstOrDefaultAsync(d => d.DeviceId == deviceId, ct);

        if (device is null)
            return null;

        var latestHeartbeat = await _db.Heartbeats
            .AsNoTracking()
            .Where(h => h.DeviceRecordId == device.Id)
            .OrderByDescending(h => h.ReceivedAtUtc)
            .Select(h => new HeartbeatListItem(
                h.UptimeMs,
                h.FreeMemoryBytes,
                EndpointValidation.ToUtcZ(h.ReceivedAtUtc)))
            .FirstOrDefaultAsync(ct);

        return new DeviceDetailResponse(
            device.DeviceId,
            device.Platform,
            device.Version,
            device.Ip,
            device.Mode,
            device.LastHeartbeatAtUtc.HasValue ? EndpointValidation.ToUtcZ(device.LastHeartbeatAtUtc.Value) : null,
            EndpointValidation.ToUtcZ(device.CreatedAtUtc),
            EndpointValidation.ToUtcZ(device.UpdatedAtUtc),
            latestHeartbeat);
    }

    public async Task<bool> UpdateDeviceModeAsync(string deviceId, string mode, CancellationToken ct = default)
    {
        var device = await _db.Devices.FirstOrDefaultAsync(d => d.DeviceId == deviceId, ct);
        if (device is null)
            return false;

        device.Mode = mode;
        device.UpdatedAtUtc = DateTimeOffset.UtcNow;
        await _db.SaveChangesAsync(ct);
        return true;
    }

    public async Task<bool> DeleteDeviceAsync(string deviceId, CancellationToken ct = default)
    {
        var device = await _db.Devices.FirstOrDefaultAsync(d => d.DeviceId == deviceId, ct);
        if (device is null)
            return false;

        _db.Devices.Remove(device);
        await _db.SaveChangesAsync(ct);
        return true;
    }

    public async Task<PaginatedResponse<HeartbeatListItem>> GetHeartbeatsAsync(
        string deviceId, int offset, int limit, DateTimeOffset? from, DateTimeOffset? to, CancellationToken ct = default)
    {
        var device = await _db.Devices.AsNoTracking().FirstOrDefaultAsync(d => d.DeviceId == deviceId, ct);
        if (device is null)
            return new PaginatedResponse<HeartbeatListItem>(new List<HeartbeatListItem>(), 0, offset, limit);

        var query = _db.Heartbeats
            .AsNoTracking()
            .Where(h => h.DeviceRecordId == device.Id);

        if (from.HasValue)
            query = query.Where(h => h.ReceivedAtUtc >= from.Value);
        if (to.HasValue)
            query = query.Where(h => h.ReceivedAtUtc <= to.Value);

        var total = await query.CountAsync(ct);

        var items = await query
            .OrderByDescending(h => h.ReceivedAtUtc)
            .Skip(offset)
            .Take(limit)
            .Select(h => new HeartbeatListItem(
                h.UptimeMs,
                h.FreeMemoryBytes,
                EndpointValidation.ToUtcZ(h.ReceivedAtUtc)))
            .ToListAsync(ct);

        return new PaginatedResponse<HeartbeatListItem>(items, total, offset, limit);
    }

    public async Task<PaginatedResponse<LogBatchListItem>> GetLogsAsync(
        string deviceId, int offset, int limit, DateTimeOffset? from, DateTimeOffset? to, CancellationToken ct = default)
    {
        var device = await _db.Devices.AsNoTracking().FirstOrDefaultAsync(d => d.DeviceId == deviceId, ct);
        if (device is null)
            return new PaginatedResponse<LogBatchListItem>(new List<LogBatchListItem>(), 0, offset, limit);

        var query = _db.LogBatches
            .AsNoTracking()
            .Where(l => l.DeviceRecordId == device.Id);

        if (from.HasValue)
            query = query.Where(l => l.ReceivedAtUtc >= from.Value);
        if (to.HasValue)
            query = query.Where(l => l.ReceivedAtUtc <= to.Value);

        var total = await query.CountAsync(ct);

        var items = await query
            .OrderByDescending(l => l.ReceivedAtUtc)
            .Skip(offset)
            .Take(limit)
            .Select(l => new LogBatchListItem(
                l.Id,
                l.Reason,
                l.ReceivedCount,
                l.DroppedCount,
                l.Truncated,
                l.LogsJson,
                EndpointValidation.ToUtcZ(l.ReceivedAtUtc)))
            .ToListAsync(ct);

        return new PaginatedResponse<LogBatchListItem>(items, total, offset, limit);
    }
}
