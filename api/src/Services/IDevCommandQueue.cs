using HomeIOT.Api.Services.Models;

namespace HomeIOT.Api.Services;

public interface IDevCommandQueue
{
    DevCommandEntry Enqueue(string deviceId, string code, int? timeoutMs);
    DevCommandEntry? PeekNext(string deviceId);
    void Acknowledge(string deviceId, string commandId);

    /// <summary>
    /// Removes the device's pending command if it matches <paramref name="commandId"/> and records it
    /// as running, so it is delivered at most once even if running it resets the device.
    /// Returns false when that command is no longer pending.
    /// </summary>
    bool Start(string deviceId, string commandId);

    void StoreResult(string commandId, DevCommandResultPayload result);
    DevCommandResultPayload? GetResult(string commandId);

    // Admin listing
    IReadOnlyList<DevCommandEntry> ListPending();
    IReadOnlyList<DevCommandResultPayload> ListResults();
}
