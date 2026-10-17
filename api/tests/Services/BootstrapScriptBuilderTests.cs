using System.Text.Json;
using HomeIOT.Api.Services;
using HomeIOT.Api.Services.Models;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public class BootstrapScriptBuilderTests
{
    private static readonly BootstrapProvisioningData Data = new(
        "dev-001", "esp32", "http://192.168.1.5:8080", "generated-key", "Home WiFi", "p\"a\\ss\nwörd");

    [Fact]
    public void Build_NoRelease_ReturnsNull()
    {
        var ota = new Mock<IOtaReleaseService>();
        ota.Setup(x => x.GetLatestVersion("esp32")).Returns((string?)null);

        Assert.Null(new BootstrapScriptBuilder(ota.Object).Build(Data));
    }

    [Fact]
    public void Build_MissingReleaseFile_Throws()
    {
        var ota = new Mock<IOtaReleaseService>();
        ota.Setup(x => x.GetLatestVersion("esp32")).Returns("1.2.0");
        ota.Setup(x => x.ReadReleaseFileText("esp32", "1.2.0", It.IsAny<string>())).Returns((string?)null);

        var ex = Assert.Throws<InvalidOperationException>(() => new BootstrapScriptBuilder(ota.Object).Build(Data));
        Assert.Contains("esp32/1.2.0", ex.Message);
    }

    [Fact]
    public void Build_ProducesLoaderFollowedByCommentPayload()
    {
        var requested = new List<string>();
        var ota = CreateOta(requested);

        var script = new BootstrapScriptBuilder(ota.Object).Build(Data);

        Assert.NotNull(script);
        Assert.Equal("1.2.0", script!.ReleaseVersion);
        Assert.DoesNotContain('\r', script.Content);
        Assert.Contains("def extract_payload(", script.Content);
        Assert.Contains("config.json", requested);
        Assert.Contains("edge/shared/app/updater.py", requested);

        var lines = script.Content.Split('\n');
        var provisionIndex = Array.FindIndex(lines, l => l.StartsWith(BootstrapScriptBuilder.ProvisionMarker, StringComparison.Ordinal));
        Assert.True(provisionIndex > 0);

        // Everything after the loader is a comment so MicroPython never has to compile it.
        foreach (var line in lines.Skip(provisionIndex).Where(l => l.Length > 0))
        {
            Assert.StartsWith("#", line);
        }

        var json = lines[provisionIndex][BootstrapScriptBuilder.ProvisionMarker.Length..];
        var provision = JsonSerializer.Deserialize<Dictionary<string, string>>(json)!;
        Assert.Equal("dev-001", provision["device_id"]);
        Assert.Equal("esp32", provision["platform"]);
        Assert.Equal("http://192.168.1.5:8080", provision["api_url"]);
        Assert.Equal("generated-key", provision["api_key"]);
        Assert.Equal("Home WiFi", provision["wifi_ssid"]);
        Assert.Equal("p\"a\\ss\nwörd", provision["wifi_password"]);
    }

    [Fact]
    public void Build_EncodesFilesLineByLineAndNormalizesLineEndings()
    {
        var script = new BootstrapScriptBuilder(CreateOta(new List<string>()).Object).Build(Data)!;

        var block = "#@@FILE edge/shared/app/updater.py\n"
            + "#|# edge/shared/app/updater.py\n"
            + "#|x = 1\n"
            + "#|\n"
            + "#|y = 2\n"
            + "#@@END\n";
        Assert.Contains(block, script.Content);
        Assert.Contains("#@@FILE edge/bootstrap/bootstrap.py\n", script.Content);
        Assert.Contains("#@@FILE edge/bootstrap/provisioning.py\n", script.Content);
        Assert.EndsWith("#@@END\n", script.Content);
    }

    private static Mock<IOtaReleaseService> CreateOta(List<string> requested)
    {
        var ota = new Mock<IOtaReleaseService>();
        ota.Setup(x => x.GetLatestVersion("esp32")).Returns("1.2.0");
        ota.Setup(x => x.ReadReleaseFileText("esp32", "1.2.0", It.IsAny<string>()))
            .Returns((string _, string _, string path) =>
            {
                requested.Add(path);
                return $"# {path}\r\nx = 1\r\n\r\ny = 2\r\n";
            });
        return ota;
    }
}
