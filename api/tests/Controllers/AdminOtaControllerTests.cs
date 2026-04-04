using HomeIOT.Api.Controllers;
using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class AdminOtaControllerTests
{
    private readonly Mock<IOtaReleaseService> _mockService;
    private readonly AdminOtaController _controller;

    public AdminOtaControllerTests()
    {
        _mockService = new Mock<IOtaReleaseService>();
        _controller = new AdminOtaController(_mockService.Object)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext(),
            },
        };
    }

    [Fact]
    public void ListPlatforms_ReturnsOk()
    {
        _mockService.Setup(s => s.ListPlatforms())
            .Returns(new List<OtaPlatformListItem>
            {
                new("esp32", 3),
            });

        var result = _controller.ListPlatforms();

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var items = Assert.IsType<List<OtaPlatformListItem>>(ok.Value);
        Assert.Single(items);
    }

    [Fact]
    public void ListReleases_ReturnsOk()
    {
        _mockService.Setup(s => s.ListReleases("esp32"))
            .Returns(new List<OtaReleaseListItem>
            {
                new("1.0.0", 5, 12345),
            });

        var result = _controller.ListReleases("esp32");

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var items = Assert.IsType<List<OtaReleaseListItem>>(ok.Value);
        Assert.Single(items);
    }

    [Fact]
    public void ListReleases_ReturnsBadRequest_WhenUnsafePlatform()
    {
        var result = _controller.ListReleases("../etc");

        Assert.IsType<BadRequestObjectResult>(result.Result);
    }

    [Fact]
    public void GetRelease_ReturnsOk_WhenFound()
    {
        var detail = new OtaReleaseDetailResponse("esp32", "1.0.0", 1, 100,
            new List<OtaManifestFileItem> { new("main.py", "abc123", 100) });
        _mockService.Setup(s => s.GetReleaseDetail("esp32", "1.0.0")).Returns(detail);

        var result = _controller.GetRelease("esp32", "1.0.0");

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        Assert.IsType<OtaReleaseDetailResponse>(ok.Value);
    }

    [Fact]
    public void GetRelease_ReturnsNotFound_WhenMissing()
    {
        _mockService.Setup(s => s.GetReleaseDetail("esp32", "9.9.9"))
            .Returns((OtaReleaseDetailResponse?)null);

        var result = _controller.GetRelease("esp32", "9.9.9");

        Assert.IsType<NotFoundObjectResult>(result.Result);
    }

    [Fact]
    public void GetRelease_ReturnsBadRequest_WhenUnsafeVersion()
    {
        var result = _controller.GetRelease("esp32", "../../../etc/passwd");

        Assert.IsType<BadRequestObjectResult>(result.Result);
    }

    [Fact]
    public async Task UploadRelease_ReturnsBadRequest_WhenNoFile()
    {
        var result = await _controller.UploadRelease("esp32", "1.0.0", null, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task UploadRelease_ReturnsBadRequest_WhenNotZip()
    {
        var file = new Mock<IFormFile>();
        file.Setup(f => f.FileName).Returns("release.tar.gz");
        file.Setup(f => f.Length).Returns(100);

        var result = await _controller.UploadRelease("esp32", "1.0.0", file.Object, CancellationToken.None);

        Assert.IsType<BadRequestObjectResult>(result);
    }

    [Fact]
    public async Task UploadRelease_ReturnsCreated_WhenValid()
    {
        var file = new Mock<IFormFile>();
        file.Setup(f => f.FileName).Returns("release.zip");
        file.Setup(f => f.Length).Returns(100);
        file.Setup(f => f.OpenReadStream()).Returns(new MemoryStream());

        var detail = new OtaReleaseDetailResponse("esp32", "2.0.0", 1, 100,
            new List<OtaManifestFileItem> { new("main.py", "abc", 100) });
        _mockService.Setup(s => s.GetReleaseDetail("esp32", "2.0.0")).Returns(detail);

        var result = await _controller.UploadRelease("esp32", "2.0.0", file.Object, CancellationToken.None);

        Assert.IsType<CreatedResult>(result);
    }

    [Fact]
    public void DeleteRelease_ReturnsOk_WhenDeleted()
    {
        _mockService.Setup(s => s.DeleteRelease("esp32", "1.0.0")).Returns(true);

        var result = _controller.DeleteRelease("esp32", "1.0.0");

        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public void DeleteRelease_ReturnsNotFound_WhenMissing()
    {
        _mockService.Setup(s => s.DeleteRelease("esp32", "9.9.9")).Returns(false);

        var result = _controller.DeleteRelease("esp32", "9.9.9");

        Assert.IsType<NotFoundObjectResult>(result);
    }
}
