using HomeIOT.Api.Services;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public class DevCommandQueueTests
{
    private const string DeviceId = "pico-01";

    [Fact]
    public void Start_PendingCommand_RemovesItAndRecordsRunningResult()
    {
        var queue = new DevCommandQueue();
        var entry = queue.Enqueue(DeviceId, "import machine; machine.reset()", null);

        Assert.True(queue.Start(DeviceId, entry.CommandId));

        Assert.Null(queue.PeekNext(DeviceId));
        var running = queue.GetResult(entry.CommandId);
        Assert.NotNull(running);
        Assert.Equal("running", running.Status);
        Assert.Equal("import machine; machine.reset()", running.Code);
    }

    [Fact]
    public void Start_CommandNoLongerPending_ReturnsFalseAndKeepsNewerCommand()
    {
        var queue = new DevCommandQueue();
        var first = queue.Enqueue(DeviceId, "print(1)", null);
        var second = queue.Enqueue(DeviceId, "print(2)", null);

        Assert.False(queue.Start(DeviceId, first.CommandId));

        Assert.Equal(second.CommandId, queue.PeekNext(DeviceId)?.CommandId);
        Assert.Null(queue.GetResult(first.CommandId));
    }

    [Fact]
    public void Start_SameCommandTwice_OnlyFirstSucceeds()
    {
        var queue = new DevCommandQueue();
        var entry = queue.Enqueue(DeviceId, "print(1)", null);

        Assert.True(queue.Start(DeviceId, entry.CommandId));
        Assert.False(queue.Start(DeviceId, entry.CommandId));
    }
}
