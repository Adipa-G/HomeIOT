using System.Collections.Concurrent;
using HomeIOT.Api.Services.Models;

namespace HomeIOT.Api.Services;

/// <summary>
/// Lightweight in-memory dev-command queue.
/// One pending command per device at a time; results are stored until overwritten.
/// Not persisted — designed for interactive development use. A DB-backed
/// implementation can be substituted later by implementing the same interface.
/// </summary>
public sealed class DevCommandQueue : IDevCommandQueue
{
    // One pending command per device — replaces any existing pending entry.
    private readonly ConcurrentDictionary<string, DevCommandEntry> _pending = new();
    // Results keyed by commandId.
    private readonly ConcurrentDictionary<string, DevCommandResultPayload> _results = new();

    public DevCommandEntry Enqueue(string deviceId, string code, int? timeoutMs)
    {
        var entry = new DevCommandEntry(
            CommandId: Guid.NewGuid().ToString("N"),
            DeviceId: deviceId,
            RevisionHash: Guid.NewGuid().ToString("N"),
            DedupeToken: Guid.NewGuid().ToString("N"),
            Code: code,
            TimeoutMs: timeoutMs,
            QueuedAt: DateTimeOffset.UtcNow);

        _pending[deviceId] = entry;
        return entry;
    }

    public DevCommandEntry? PeekNext(string deviceId) =>
        _pending.TryGetValue(deviceId, out var entry) ? entry : null;

    public void Acknowledge(string deviceId, string commandId)
    {
        // Remove only if the commandId still matches (avoid race with re-queued command).
        if (_pending.TryGetValue(deviceId, out var entry) && entry.CommandId == commandId)
            _pending.TryRemove(deviceId, out _);
    }

    public void StoreResult(string commandId, DevCommandResultPayload result) =>
        _results[commandId] = result;

    public DevCommandResultPayload? GetResult(string commandId) =>
        _results.TryGetValue(commandId, out var result) ? result : null;
}

