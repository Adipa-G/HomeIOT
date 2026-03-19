using HomeIOT.Api.Controllers;
using HomeIOT.Api.Contracts;
using Microsoft.AspNetCore.Mvc;
using Xunit;

namespace HomeIOT.Api.Tests.Controllers;

public class PingControllerTests
{
    [Fact]
    public void Get_Returns200WithExpectedPayload()
    {
        var controller = new PingController();

        var result = controller.Get();

        var ok = Assert.IsType<OkObjectResult>(result.Result);
        var payload = Assert.IsType<PingResponse>(ok.Value);

        Assert.Equal("ok", payload.Status);
        Assert.Equal("HomeIOT API", payload.Service);
        Assert.EndsWith("Z", payload.ServerTimeUtc);
    }
}
