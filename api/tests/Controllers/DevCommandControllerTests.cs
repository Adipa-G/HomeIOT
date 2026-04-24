using System.Text;
using System.Text.Json;
using HomeIOT.Api.Controllers;
using HomeIOT.Api.Infrastructure;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class DevCommandControllerTests
{
    [Fact]
    public void ReportResult_WithData_DataIsPreservedInStoredResult()
    {
        // Arrange
        var queue = new DevCommandQueue();
        const string deviceId = "esp32-dev-01";
        var entry = queue.Enqueue(deviceId, "return {'raw_value': 128, 'temp_celsius': 53.3}", null);

        var bodyJson = JsonSerializer.Serialize(new
        {
            status = "success",
            exit_code = 0,
            elapsed_ms = 42,
            started_at_utc = "2026-06-01T00:00:00Z",
            finished_at_utc = "2026-06-01T00:00:00Z",
            stdout = (string?)null,
            stderr = (string?)null,
            data = new { raw_value = 128, temp_celsius = 53.3 },
        });

        var controller = CreateController(queue, deviceId, bodyJson);

        // Act
        var result = controller.ReportResult(entry.CommandId, ParseBody(bodyJson));

        // Assert — command accepted
        Assert.IsType<AcceptedObjectResult>(result);

        // Assert — data is stored and readable (not disposed with the request)
        var stored = queue.GetResult(entry.CommandId);
        Assert.NotNull(stored);
        Assert.Equal("success", stored.Status);
        Assert.NotNull(stored.Data);

        // Verify the data fields survive beyond the original JsonElement scope
        var dataDoc = stored.Data.Value;
        Assert.Equal(128, dataDoc.GetProperty("raw_value").GetInt32());
        Assert.Equal(53.3, dataDoc.GetProperty("temp_celsius").GetDouble(), precision: 1);
    }

    [Fact]
    public void ReportResult_NullData_StoredDataIsNull()
    {
        var queue = new DevCommandQueue();
        const string deviceId = "esp32-dev-01";
        var entry = queue.Enqueue(deviceId, "print('hi')", null);

        var bodyJson = JsonSerializer.Serialize(new
        {
            status = "success",
            exit_code = 0,
            elapsed_ms = 10,
            started_at_utc = "2026-06-01T00:00:00Z",
            finished_at_utc = "2026-06-01T00:00:00Z",
            stdout = "hi",
            stderr = (string?)null,
            data = (object?)null,
        });

        var controller = CreateController(queue, deviceId, bodyJson);

        var result = controller.ReportResult(entry.CommandId, ParseBody(bodyJson));

        Assert.IsType<AcceptedObjectResult>(result);
        var stored = queue.GetResult(entry.CommandId);
        Assert.NotNull(stored);
        Assert.Null(stored.Data);
        Assert.Equal("hi", stored.Stdout);
    }

    [Fact]
    public void GetNext_NoPendingCommand_Returns204()
    {
        var queue = new DevCommandQueue();
        var controller = CreateController(queue, "esp32-dev-01", "{}");

        var result = controller.GetNext(null);

        Assert.IsType<NoContentResult>(result);
    }

    [Fact]
    public void GetNext_PendingCommand_Returns200WithCode()
    {
        var queue = new DevCommandQueue();
        const string deviceId = "esp32-dev-01";
        queue.Enqueue(deviceId, "print('hello')", 5000);
        var controller = CreateController(queue, deviceId, "{}");

        var result = controller.GetNext(null);

        var ok = Assert.IsType<OkObjectResult>(result);
        var json = JsonSerializer.Serialize(ok.Value);
        using var doc = JsonDocument.Parse(json);
        Assert.Equal("print('hello')", doc.RootElement.GetProperty("code").GetString());
        Assert.Equal(5000, doc.RootElement.GetProperty("timeout_ms").GetInt32());
    }

    private static DevCommandController CreateController(IDevCommandQueue queue, string deviceId, string bodyJson)
    {
        var controller = new DevCommandController(queue)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext(),
            },
        };
        controller.HttpContext.SetDeviceRequestContext(new DeviceRequestContext(deviceId, "api-key", null));
        return controller;
    }

    private static JsonElement ParseBody(string json)
    {
        var doc = JsonDocument.Parse(json);
        return doc.RootElement.Clone(); // simulate a fresh parse
    }
}
