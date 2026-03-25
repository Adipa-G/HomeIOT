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
    public void GetFile_FallsBackToRegisteredPlatform()
    {
        var serviceMock = new Mock<IOtaReleaseService>();
        var bytes = new byte[] { 0x01, 0x02, 0x03 };
        serviceMock
            .Setup(x => x.TryGetReleaseFile("esp32", "1.1.0", "main.py"))
            .Returns(new OtaFileContent(bytes, "main.py"));

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

        var result = controller.GetFile("1.1.0", "main.py");

        var file = Assert.IsType<FileContentResult>(result);
        Assert.Equal("application/octet-stream", file.ContentType);
        Assert.Equal("main.py", file.FileDownloadName);
        Assert.Equal(bytes, file.FileContents);
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
