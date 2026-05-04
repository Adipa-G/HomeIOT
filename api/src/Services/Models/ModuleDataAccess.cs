using HomeIOT.Api.Data;
using Microsoft.EntityFrameworkCore;
using System.Text.Json;

namespace HomeIOT.Api.Services.Models;

public sealed class ModuleDataAccess : IModuleDataAccess
{
    private readonly ApiDbContext _db;
    private readonly string _deviceId;

    public ModuleDataAccess(ApiDbContext db, string deviceId)
    {
        _db = db;
        _deviceId = deviceId;
    }

    public async Task<List<ModuleResultEntry>> QueryResultsAsync(
        string moduleId, DateTimeOffset from, DateTimeOffset to, CancellationToken ct = default)
    {
        var fromStr = from.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'");
        var toStr = to.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'");

        var records = await _db.ModuleResults
            .AsNoTracking()
            .Where(r => r.DeviceId == _deviceId
                     && r.ModuleId == moduleId
                     && string.Compare(r.StartedAtUtc.ToString(), fromStr, StringComparison.Ordinal) >= 0
                     && string.Compare(r.StartedAtUtc.ToString(), toStr, StringComparison.Ordinal) <= 0)
            .OrderByDescending(r => r.StartedAtUtc)
            .ToListAsync(ct);

        return records.Select(r => new ModuleResultEntry(
            r.ModuleId,
            r.ModuleVersion,
            r.StartedAtUtc,
            r.Status,
            r.Output is not null ? ParseJson(r.Output) : null)).ToList();
    }

    public async Task<ModuleResultEntry?> GetLatestResultAsync(
        string moduleId, CancellationToken ct = default)
    {
        var record = await _db.ModuleResults
            .AsNoTracking()
            .Where(r => r.DeviceId == _deviceId && r.ModuleId == moduleId)
            .OrderByDescending(r => r.StartedAtUtc)
            .FirstOrDefaultAsync(ct);

        if (record is null)
            return null;

        return new ModuleResultEntry(
            record.ModuleId,
            record.ModuleVersion,
            record.StartedAtUtc,
            record.Status,
            record.Output is not null ? ParseJson(record.Output) : null);
    }

    private static JsonDocument? ParseJson(string json)
    {
        try { return JsonDocument.Parse(json); }
        catch { return null; }
    }
}
