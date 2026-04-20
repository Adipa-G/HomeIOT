using HomeIOT.Api.Controllers;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Data.Entities;
using HomeIOT.Api.Infrastructure;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class OtaControllerTests
{
    [Fact]
    public void Check_UsesHeaderPlatformAndVersionHint()
    {
        var serviceMock = new Mock<IOtaReleaseService>();
        serviceMock
            .Setup(x => x.CheckForUpdate("esp32", "1.0.0"))
            .Returns(new OtaCheckResponse(false));

        var controller = CreateController(serviceMock.Object);
        controller.HttpContext.Request.Headers["X-Platform"] = "esp32";
        controller.HttpContext.Request.Headers["X-Current-Version"] = "1.0.0";

        var result = controller.Check("1.0.0");

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var payload = Assert.IsType<OtaCheckResponse>(ok.Value);
        Assert.False(payload.Available);
        serviceMock.VerifyAll();
    }

    [Fact]
    public async Task GetStream_Returns200WithOctetStream_WhenReleaseExists()
    {
        var serviceMock = new Mock<IOtaReleaseService>();
        var detail = new OtaReleaseDetailResponse("esp32", "1.1.0", 1, 10,
            new List<OtaManifestFileItem> { new("main.py", "abc", 10) });
        serviceMock.Setup(x => x.GetReleaseDetail("esp32", "1.1.0")).Returns(detail);
        serviceMock
            .Setup(x => x.StreamReleaseAsync("esp32", "1.1.0", It.IsAny<Stream>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var controller = CreateController(serviceMock.Object);
        controller.HttpContext.Request.Headers["X-Platform"] = "esp32";

        var result = await controller.GetStream("1.1.0");

        Assert.IsType<EmptyResult>(result);
        Assert.Equal("application/octet-stream", controller.HttpContext.Response.ContentType);
        serviceMock.VerifyAll();
    }

    [Fact]
    public async Task GetStream_Returns404_WhenReleaseNotFound()
    {
        var serviceMock = new Mock<IOtaReleaseService>();
        serviceMock.Setup(x => x.GetReleaseDetail("esp32", "9.9.9")).Returns((OtaReleaseDetailResponse?)null);

        var controller = CreateController(serviceMock.Object);
        controller.HttpContext.Request.Headers["X-Platform"] = "esp32";

        var result = await controller.GetStream("9.9.9");

        Assert.IsType<NotFoundObjectResult>(result);
    }

    [Fact]
    public async Task GetStream_Returns400_WhenVersionMissing()
    {
        var serviceMock = new Mock<IOtaReleaseService>();
        var controller = CreateController(serviceMock.Object);
        controller.HttpContext.Request.Headers["X-Platform"] = "esp32";

        var result = await controller.GetStream(null);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task GetStream_Returns400_WhenVersionUnsafe()
    {
        var serviceMock = new Mock<IOtaReleaseService>();
        var controller = CreateController(serviceMock.Object);
        controller.HttpContext.Request.Headers["X-Platform"] = "esp32";

        var result = await controller.GetStream("../../etc/passwd");

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task GetStream_FallsBackToRegisteredPlatform()
    {
        var serviceMock = new Mock<IOtaReleaseService>();
        var detail = new OtaReleaseDetailResponse("esp32", "1.1.0", 1, 10,
            new List<OtaManifestFileItem> { new("main.py", "abc", 10) });
        serviceMock.Setup(x => x.GetReleaseDetail("esp32", "1.1.0")).Returns(detail);
        serviceMock
            .Setup(x => x.StreamReleaseAsync("esp32", "1.1.0", It.IsAny<Stream>(), It.IsAny<CancellationToken>()))
            .Returns(Task.CompletedTask);

        var controller = CreateController(serviceMock.Object);
        controller.HttpContext.SetDeviceRequestContext(new DeviceRequestContext(
            "dev-001",
            "api-key",
            new DeviceRecord
            {
                Id = Guid.NewGuid(),
                DeviceId = "dev-001",
                ApiKey = "api-key",
                Platform = "esp32",
                CreatedAtUtc = DateTimeOffset.UtcNow,
                UpdatedAtUtc = DateTimeOffset.UtcNow,
                Mode = "production",
            }));

        var result = await controller.GetStream("1.1.0");

        Assert.IsType<EmptyResult>(result);
        serviceMock.VerifyAll();
    }

    private static OtaController CreateController(IOtaReleaseService service)
    {
        return new OtaController(service)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext(),
            },
        };
    }
}
