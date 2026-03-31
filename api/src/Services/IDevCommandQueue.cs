using HomeIOT.Api.Services.Models;

namespace HomeIOT.Api.Services;

public interface IDevCommandQueue
{
    DevCommandEntry Enqueue(string deviceId, string code, int? timeoutMs);
    DevCommandEntry? PeekNext(string deviceId);
    void Acknowledge(string deviceId, string commandId);
    void StoreResult(string commandId, DevCommandResultPayload result);
    DevCommandResultPayload? GetResult(string commandId);
}
