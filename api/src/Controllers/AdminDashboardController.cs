using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace HomeIOT.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/admin/dashboard")]
public sealed class AdminDashboardController : UserApiControllerBase
{
    private readonly ApiDbContext _db;

    public AdminDashboardController(ApiDbContext db)
    {
        _db = db;
    }

    [HttpGet]
    public async Task<ActionResult<DashboardResponse>> GetDashboard(CancellationToken ct)
    {
        var now = DateTimeOffset.UtcNow;
        var since24h = now.AddHours(-24);

        var totalDevices = await _db.Devices.CountAsync(ct);
        var devicesOnline24h = await _db.Devices
            .CountAsync(d => d.LastHeartbeatAtUtc.HasValue && d.LastHeartbeatAtUtc.Value >= since24h, ct);
        var totalModules = await _db.ModuleDefinitions.CountAsync(ct);
        var totalAssignments = await _db.ModuleAssignments.CountAsync(ct);
        var totalUsers = await _db.Users.CountAsync(ct);
        var heartbeats24h = await _db.Heartbeats
            .CountAsync(h => h.ReceivedAtUtc >= since24h, ct);
        var logBatches24h = await _db.LogBatches
            .CountAsync(l => l.ReceivedAtUtc >= since24h, ct);
        var moduleRuns24h = await _db.ModuleResults
            .CountAsync(r => r.ReceivedAtUtc >= since24h, ct);
        var moduleFailures24h = await _db.ModuleResults
            .CountAsync(r => r.ReceivedAtUtc >= since24h && r.Status == "error", ct);

        return Ok(new DashboardResponse(
            totalDevices,
            devicesOnline24h,
            totalModules,
            totalAssignments,
            totalUsers,
            heartbeats24h,
            logBatches24h,
            moduleRuns24h,
            moduleFailures24h));
    }
}
