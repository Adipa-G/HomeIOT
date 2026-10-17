using HomeIOT.Api.Contracts;
using HomeIOT.Api.Controllers;
using HomeIOT.Api.Services;
using HomeIOT.Api.Services.Models;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class AdminDeviceProvisioningControllerTests
{
    private static readonly ProvisionDeviceResponse SampleResponse = new("dev-001", "esp32", "1.0.0", "main.py", "script");

    [Fact]
    public async Task CreateDevice_Success_Returns201WithScript()
    {
        var service = new Mock<IDeviceProvisioningService>();
        service.Setup(x => x.CreateDeviceAsync(It.IsAny<CreateDeviceRequest>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new DeviceProvisioningResult(DeviceProvisioningStatus.Success, SampleResponse));

        var result = await new AdminDeviceProvisioningController(service.Object).CreateDevice(ValidCreate(), CancellationToken.None);

        var objectResult = Assert.IsType<ObjectResult>(result.Result);
        Assert.Equal(StatusCodes.Status201Created, objectResult.StatusCode);
        Assert.Same(SampleResponse, objectResult.Value);
    }

    public static TheoryData<CreateDeviceRequest> InvalidCreateRequests => new()
    {
        With(r => r.DeviceId = ""),
        With(r => r.DeviceId = "bad id"),
        With(r => r.DeviceId = "../etc"),
        With(r => r.DeviceId = new string('a', 65)),
        With(r => r.Platform = "simulator"),
        With(r => r.Platform = null),
        With(r => r.ApiUrl = "not-a-url"),
        With(r => r.ApiUrl = "ftp://host"),
        With(r => r.ApiUrl = null),
        With(r => r.WifiSsid = ""),
        With(r => r.WifiSsid = new string('s', 33)),
        With(r => r.WifiPassword = new string('p', 65)),
    };

    [Theory]
    [MemberData(nameof(InvalidCreateRequests))]
    public async Task CreateDevice_InvalidRequest_Returns400WithoutCallingService(CreateDeviceRequest request)
    {
        var service = new Mock<IDeviceProvisioningService>(MockBehavior.Strict);

        var result = await new AdminDeviceProvisioningController(service.Object).CreateDevice(request, CancellationToken.None);

        var badRequest = Assert.IsType<BadRequestObjectResult>(result.Result);
        Assert.Equal("invalid_request", Assert.IsType<ErrorResponse>(badRequest.Value).Error);
    }

    [Fact]
    public async Task CreateDevice_NullBody_Returns400()
    {
        var service = new Mock<IDeviceProvisioningService>(MockBehavior.Strict);

        var result = await new AdminDeviceProvisioningController(service.Object).CreateDevice(null, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result.Result);
    }

    [Fact]
    public async Task CreateDevice_EmptyWifiPassword_IsAllowed()
    {
        var service = new Mock<IDeviceProvisioningService>();
        service.Setup(x => x.CreateDeviceAsync(It.IsAny<CreateDeviceRequest>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new DeviceProvisioningResult(DeviceProvisioningStatus.Success, SampleResponse));

        var result = await new AdminDeviceProvisioningController(service.Object)
            .CreateDevice(With(r => r.WifiPassword = ""), CancellationToken.None);

        Assert.Equal(StatusCodes.Status201Created, Assert.IsType<ObjectResult>(result.Result).StatusCode);
    }

    [Theory]
    [InlineData(DeviceProvisioningStatus.DeviceExists, typeof(ConflictObjectResult), "conflict")]
    [InlineData(DeviceProvisioningStatus.NoRelease, typeof(ConflictObjectResult), "no_release")]
    [InlineData(DeviceProvisioningStatus.ReleaseIncomplete, typeof(ConflictObjectResult), "release_incomplete")]
    [InlineData(DeviceProvisioningStatus.DeviceNotFound, typeof(NotFoundObjectResult), "not_found")]
    [InlineData(DeviceProvisioningStatus.PlatformRequired, typeof(BadRequestObjectResult), "invalid_request")]
    public async Task CreateDevice_ServiceFailure_MapsToErrorResponse(DeviceProvisioningStatus status, Type expectedType, string expectedError)
    {
        var service = new Mock<IDeviceProvisioningService>();
        service.Setup(x => x.CreateDeviceAsync(It.IsAny<CreateDeviceRequest>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(DeviceProvisioningResult.Failed(status, "msg"));

        var result = await new AdminDeviceProvisioningController(service.Object).CreateDevice(ValidCreate(), CancellationToken.None);

        Assert.IsType(expectedType, result.Result);
        var payload = Assert.IsType<ErrorResponse>(((ObjectResult)result.Result!).Value);
        Assert.Equal(expectedError, payload.Error);
        Assert.Equal("msg", payload.Message);
    }

    [Fact]
    public async Task ReprovisionDevice_Success_Returns200()
    {
        var service = new Mock<IDeviceProvisioningService>();
        service.Setup(x => x.ReprovisionDeviceAsync("dev-001", It.IsAny<ReprovisionDeviceRequest>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(new DeviceProvisioningResult(DeviceProvisioningStatus.Success, SampleResponse));

        var result = await new AdminDeviceProvisioningController(service.Object)
            .ReprovisionDevice("dev-001", ValidReprovision(), CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        Assert.Same(SampleResponse, ok.Value);
    }

    [Fact]
    public async Task ReprovisionDevice_InvalidPlatform_Returns400()
    {
        var service = new Mock<IDeviceProvisioningService>(MockBehavior.Strict);
        var request = ValidReprovision();
        request.Platform = "simulator";

        var result = await new AdminDeviceProvisioningController(service.Object)
            .ReprovisionDevice("dev-001", request, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result.Result);
    }

    [Fact]
    public async Task ReprovisionDevice_MissingSsid_Returns400()
    {
        var service = new Mock<IDeviceProvisioningService>(MockBehavior.Strict);
        var request = ValidReprovision();
        request.WifiSsid = null;

        var result = await new AdminDeviceProvisioningController(service.Object)
            .ReprovisionDevice("dev-001", request, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result.Result);
    }

    [Fact]
    public async Task ReprovisionDevice_NotFound_Returns404()
    {
        var service = new Mock<IDeviceProvisioningService>();
        service.Setup(x => x.ReprovisionDeviceAsync("missing", It.IsAny<ReprovisionDeviceRequest>(), It.IsAny<CancellationToken>()))
            .ReturnsAsync(DeviceProvisioningResult.Failed(DeviceProvisioningStatus.DeviceNotFound, "Device not found."));

        var result = await new AdminDeviceProvisioningController(service.Object)
            .ReprovisionDevice("missing", ValidReprovision(), CancellationToken.None);

        Assert.IsType<NotFoundObjectResult>(result.Result);
    }

    private static CreateDeviceRequest ValidCreate() => new()
    {
        DeviceId = "dev-001",
        Platform = "esp32",
        ApiUrl = "http://192.168.1.5:8080",
        WifiSsid = "Home",
        WifiPassword = "secret",
    };

    private static ReprovisionDeviceRequest ValidReprovision() => new()
    {
        ApiUrl = "https://iot.example.com",
        WifiSsid = "Home",
        WifiPassword = "secret",
    };

    private static CreateDeviceRequest With(Action<CreateDeviceRequest> mutate)
    {
        var request = ValidCreate();
        mutate(request);
        return request;
    }
}
