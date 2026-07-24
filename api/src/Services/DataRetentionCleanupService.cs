using HomeIOT.Api.Configuration;
using HomeIOT.Api.Data;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace HomeIOT.Api.Services;

/// <summary>
/// Periodically purges heartbeat and log batch records older than the configured
/// retention period. Runs as a background hosted service for the lifetime of the app.
/// </summary>
public sealed class DataRetentionCleanupService(
    IServiceScopeFactory scopeFactory,
    IOptions<DataRetentionOptions> options,
    ILogger<DataRetentionCleanupService> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        var intervalMinutes = Math.Max(1, options.Value.CleanupIntervalMinutes);
        var interval = TimeSpan.FromMinutes(intervalMinutes);

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await RunCleanupOnceAsync(stoppingToken);
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                logger.LogError(ex, "Data retention cleanup pass failed");
            }

            try
            {
                await Task.Delay(interval, stoppingToken);
            }
            catch (OperationCanceledException)
            {
                break;
            }
        }
    }

    /// <summary>
    /// Executes a single cleanup pass. Public so it can be unit tested
    /// without running the full background loop.
    /// </summary>
    public async Task RunCleanupOnceAsync(CancellationToken ct)
    {
        var retentionDays = options.Value.RetentionDays;
        if (retentionDays <= 0)
            return;

        using var scope = scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<ApiDbContext>();
        var cutoff = DateTimeOffset.UtcNow.AddDays(-retentionDays);

        var staleHeartbeats = await db.Heartbeats
            .Where(h => h.ReceivedAtUtc < cutoff)
            .ToListAsync(ct);
        db.Heartbeats.RemoveRange(staleHeartbeats);

        var staleLogBatches = await db.LogBatches
            .Where(l => l.ReceivedAtUtc < cutoff)
            .ToListAsync(ct);
        db.LogBatches.RemoveRange(staleLogBatches);

        if (staleHeartbeats.Count > 0 || staleLogBatches.Count > 0)
        {
            await db.SaveChangesAsync(ct);
            logger.LogInformation(
                "Data retention cleanup removed {HeartbeatCount} heartbeat(s) and {LogBatchCount} log batch(es) older than {RetentionDays} day(s)",
                staleHeartbeats.Count,
                staleLogBatches.Count,
                retentionDays);
        }
    }
}
