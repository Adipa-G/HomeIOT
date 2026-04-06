using HomeIOT.Api.Controllers;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services;
using HomeIOT.Api.Services.Models;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class AdminDevCommandControllerTests
{
    [Fact]
    public void Enqueue_ValidRequest_Returns202()
    {
        var queue = new DevCommandQueue();
        var controller = CreateController(queue);

        var result = controller.Enqueue(new DevCommandEnqueueRequest("esp32-001", "print('hi')", 5000));

        var acceptedResult = Assert.IsType<AcceptedResult>(result.Result);
        var response = Assert.IsType<DevCommandEnqueueResponse>(acceptedResult.Value);
        Assert.Equal("esp32-001", response.DeviceId);
        Assert.False(string.IsNullOrWhiteSpace(response.CommandId));
    }

    [Fact]
    public void Enqueue_MissingDeviceId_Returns400()
    {
        var queue = new DevCommandQueue();
        var controller = CreateController(queue);

        var result = controller.Enqueue(new DevCommandEnqueueRequest(null, "print('hi')", 5000));

        Assert.IsType<BadRequestObjectResult>(result.Result);
    }

    [Fact]
    public void Enqueue_MissingCode_Returns400()
    {
        var queue = new DevCommandQueue();
        var controller = CreateController(queue);

        var result = controller.Enqueue(new DevCommandEnqueueRequest("esp32-001", null, 5000));

        Assert.IsType<BadRequestObjectResult>(result.Result);
    }

    [Fact]
    public void Enqueue_NullBody_Returns400()
    {
        var queue = new DevCommandQueue();
        var controller = CreateController(queue);

        var result = controller.Enqueue(null);

        Assert.IsType<BadRequestObjectResult>(result.Result);
    }

    [Fact]
    public void GetResult_NoResult_Returns404()
    {
        var queue = new DevCommandQueue();
        var controller = CreateController(queue);

        var result = controller.GetResult("nonexistent-id");

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public void GetResult_AfterEnqueueAndReport_ReturnsResult()
    {
        var queue = new DevCommandQueue();
        var controller = CreateController(queue);

        // Enqueue
        var enqueueResult = controller.Enqueue(new DevCommandEnqueueRequest("esp32-001", "print('hi')", 5000));
        var enqueueResponse = Assert.IsType<DevCommandEnqueueResponse>(
            Assert.IsType<AcceptedResult>(enqueueResult.Result).Value);

        // Simulate device reporting result
        queue.Acknowledge("esp32-001", enqueueResponse.CommandId);
        queue.StoreResult(enqueueResponse.CommandId, new DevCommandResultPayload(
            CommandId: enqueueResponse.CommandId,
            RevisionHash: null,
            DedupeToken: null,
            Status: "success",
            StartedAtUtc: "2026-05-30T00:00:00Z",
            FinishedAtUtc: "2026-05-30T00:00:01Z",
            ElapsedMs: 1000,
            ExitCode: 0,
            Stdout: "hi",
            Stderr: null,
            Data: null,
            ReceivedAt: DateTimeOffset.UtcNow));

        // Get result
        var getResult = controller.GetResult(enqueueResponse.CommandId);
        Assert.IsType<OkObjectResult>(getResult);
    }

    [Fact]
    public void ListPending_ReturnsEmptyWhenNoCommands()
    {
        var queue = new DevCommandQueue();
        var controller = CreateController(queue);

        var result = controller.ListPending();

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public void ListPending_ReturnsQueuedCommands()
    {
        var queue = new DevCommandQueue();
        queue.Enqueue("dev-001", "print('a')", null);
        queue.Enqueue("dev-002", "print('b')", 5000);
        var controller = CreateController(queue);

        var result = controller.ListPending();

        var ok = Assert.IsType<OkObjectResult>(result);
        Assert.NotNull(ok.Value);
    }

    [Fact]
    public void ListResults_ReturnsEmptyWhenNoResults()
    {
        var queue = new DevCommandQueue();
        var controller = CreateController(queue);

        var result = controller.ListResults();

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public void ListResults_ReturnsStoredResults()
    {
        var queue = new DevCommandQueue();
        queue.StoreResult("cmd-1", new DevCommandResultPayload(
            CommandId: "cmd-1", RevisionHash: null, DedupeToken: null,
            Status: "success", StartedAtUtc: "2026-05-30T00:00:00Z",
            FinishedAtUtc: "2026-05-30T00:00:01Z", ElapsedMs: 100,
            ExitCode: 0, Stdout: "ok", Stderr: null, Data: null,
            ReceivedAt: DateTimeOffset.UtcNow));
        var controller = CreateController(queue);

        var result = controller.ListResults();

        Assert.IsType<OkObjectResult>(result);
    }

    private static AdminDevCommandController CreateController(IDevCommandQueue queue)
    {
        var controller = new AdminDevCommandController(queue);
        controller.ControllerContext = new ControllerContext
        {
            HttpContext = new DefaultHttpContext(),
        };
        return controller;
    }
}
