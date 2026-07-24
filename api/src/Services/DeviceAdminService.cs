using System.Text.Json;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using HomeIOT.Api.Infrastructure;
using Microsoft.EntityFrameworkCore;

namespace HomeIOT.Api.Services;

public sealed class DeviceAdminService : IDeviceAdminService
{
    private static readonly Dictionary<string, TimeSpan> BucketSpans = new(StringComparer.OrdinalIgnoreCase)
    {
        ["day"] = TimeSpan.FromDays(1),
        ["hour"] = TimeSpan.FromHours(1),
        ["five_minute"] = TimeSpan.FromMinutes(5),
    };

    private readonly ApiDbContext _db;

    public DeviceAdminService(ApiDbContext db)
    {
        _db = db;
    }

    private static DateTimeOffset AlignToBucket(DateTimeOffset value, TimeSpan span)
    {
        var utc = value.UtcDateTime;
        var ticks = utc.Ticks - (utc.Ticks % span.Ticks);
        return new DateTimeOffset(new DateTime(ticks, DateTimeKind.Utc));
    }

    private static List<DateTimeOffset> BuildBucketStarts(DateTimeOffset from, DateTimeOffset to, TimeSpan span)
    {
        var starts = new List<DateTimeOffset>();
        var cursor = AlignToBucket(from, span);
        while (cursor < to)
        {
            starts.Add(cursor);
            cursor = cursor.Add(span);
        }
        return starts;
    }

    private readonly record struct LogCounts(int Info, int Warn, int Error, int Debug, int Other);

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

    public async Task<List<HeartbeatActivityBucket>> GetHeartbeatActivityAsync(
        string deviceId, string bucket, DateTimeOffset from, DateTimeOffset to, CancellationToken ct = default)
    {
        var span = BucketSpans[bucket];
        var bucketStarts = BuildBucketStarts(from, to, span);

        var device = await _db.Devices.AsNoTracking().FirstOrDefaultAsync(d => d.DeviceId == deviceId, ct);
        if (device is null)
        {
            return bucketStarts
                .Select(b => new HeartbeatActivityBucket(EndpointValidation.ToUtcZ(b), EndpointValidation.ToUtcZ(b.Add(span)), 0))
                .ToList();
        }

        var timestamps = await _db.Heartbeats
            .AsNoTracking()
            .Where(h => h.DeviceRecordId == device.Id && h.ReceivedAtUtc >= from && h.ReceivedAtUtc < to)
            .Select(h => h.ReceivedAtUtc)
            .ToListAsync(ct);

        var counts = timestamps
            .GroupBy(t => AlignToBucket(t, span))
            .ToDictionary(g => g.Key, g => g.Count());

        return bucketStarts
            .Select(b => new HeartbeatActivityBucket(
                EndpointValidation.ToUtcZ(b),
                EndpointValidation.ToUtcZ(b.Add(span)),
                counts.GetValueOrDefault(b, 0)))
            .ToList();
    }

    public async Task<List<LogActivityBucket>> GetLogActivityAsync(
        string deviceId, string bucket, DateTimeOffset from, DateTimeOffset to, CancellationToken ct = default)
    {
        var span = BucketSpans[bucket];
        var bucketStarts = BuildBucketStarts(from, to, span);

        var device = await _db.Devices.AsNoTracking().FirstOrDefaultAsync(d => d.DeviceId == deviceId, ct);
        if (device is null)
        {
            return bucketStarts
                .Select(b => new LogActivityBucket(EndpointValidation.ToUtcZ(b), EndpointValidation.ToUtcZ(b.Add(span)), 0, 0, 0, 0, 0))
                .ToList();
        }

        var batches = await _db.LogBatches
            .AsNoTracking()
            .Where(l => l.DeviceRecordId == device.Id && l.ReceivedAtUtc >= from && l.ReceivedAtUtc < to)
            .Select(l => new { l.ReceivedAtUtc, l.LogsJson })
            .ToListAsync(ct);

        var counters = new Dictionary<DateTimeOffset, LogCounts>();
        foreach (var batch in batches)
        {
            List<LogEntryRequest>? entries;
            try
            {
                entries = JsonSerializer.Deserialize<List<LogEntryRequest>>(batch.LogsJson);
            }
            catch (JsonException)
            {
                continue;
            }

            if (entries is null || entries.Count == 0)
                continue;

            var bucketStart = AlignToBucket(batch.ReceivedAtUtc, span);
            var current = counters.GetValueOrDefault(bucketStart);

            foreach (var entry in entries)
            {
                var level = (entry.Level ?? "info").Trim().ToLowerInvariant();
                current = level switch
                {
                    "info" => current with { Info = current.Info + 1 },
                    "warn" or "warning" => current with { Warn = current.Warn + 1 },
                    "error" => current with { Error = current.Error + 1 },
                    "debug" => current with { Debug = current.Debug + 1 },
                    _ => current with { Other = current.Other + 1 },
                };
            }

            counters[bucketStart] = current;
        }

        return bucketStarts
            .Select(b =>
            {
                var c = counters.GetValueOrDefault(b);
                return new LogActivityBucket(
                    EndpointValidation.ToUtcZ(b),
                    EndpointValidation.ToUtcZ(b.Add(span)),
                    c.Info,
                    c.Warn,
                    c.Error,
                    c.Debug,
                    c.Other);
            })
            .ToList();
    }
}
