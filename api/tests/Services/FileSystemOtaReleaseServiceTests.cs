using System.Text;
using System.Text.Json;
using HomeIOT.Api.Configuration;
using HomeIOT.Api.Services;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public class FileSystemOtaReleaseServiceTests : IDisposable
{
    private readonly string _tempRoot;

    public FileSystemOtaReleaseServiceTests()
    {
        _tempRoot = Path.Combine(Path.GetTempPath(), "homeiot-ota-tests-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_tempRoot);
    }

    [Fact]
    public void CheckForUpdate_ReturnsLatestHigherVersion()
    {
        CreateRelease("esp32", "1.0.1", new[] { ("main.py", "hash-101") });
        CreateRelease("esp32", "1.2.0", new[] { ("main.py", "hash-120") });

        var service = CreateService();

        var response = service.CheckForUpdate("esp32", "1.0.0");

        Assert.True(response.Available);
        Assert.Equal("1.2.0", response.Version);
        Assert.NotNull(response.Manifest);
        Assert.Single(response.Manifest!);
        Assert.Equal("main.py", response.Manifest![0].Path);
    }

    [Fact]
    public void TryGetReleaseFile_ReturnsNullWhenPathNotInManifest()
    {
        CreateRelease("esp32", "1.1.0", new[] { ("main.py", "hash-main") });
        File.WriteAllText(Path.Combine(_tempRoot, "esp32", "1.1.0", "hidden.py"), "print('hidden')");

        var service = CreateService();

        var file = service.TryGetReleaseFile("esp32", "1.1.0", "hidden.py");

        Assert.Null(file);
    }

    [Fact]
    public void TryGetReleaseFile_ReturnsBytesForManifestPath()
    {
        CreateRelease("esp32", "1.1.0", new[] { ("main.py", "hash-main") });
        var expected = Encoding.UTF8.GetBytes("print('ok')");
        File.WriteAllBytes(Path.Combine(_tempRoot, "esp32", "1.1.0", "main.py"), expected);

        var service = CreateService();

        var file = service.TryGetReleaseFile("esp32", "1.1.0", "main.py");

        Assert.NotNull(file);
        Assert.Equal("main.py", file!.FileName);
        Assert.Equal(expected, file.Content);
    }

    public void Dispose()
    {
        if (Directory.Exists(_tempRoot))
        {
            Directory.Delete(_tempRoot, recursive: true);
        }
    }

    private FileSystemOtaReleaseService CreateService()
    {
        var envMock = new Mock<Microsoft.AspNetCore.Hosting.IWebHostEnvironment>();
        envMock.SetupGet(x => x.ContentRootPath).Returns(_tempRoot);
        envMock.SetupGet(x => x.ApplicationName).Returns("HomeIOT.Api");
        envMock.SetupGet(x => x.WebRootPath).Returns(_tempRoot);
        envMock.SetupGet(x => x.WebRootFileProvider).Returns(new NullFileProvider());
        envMock.SetupGet(x => x.ContentRootFileProvider).Returns(new NullFileProvider());
        envMock.SetupGet(x => x.EnvironmentName).Returns("Development");

        var options = Options.Create(new OtaArtifactOptions
        {
            ArtifactRoot = _tempRoot,
            ManifestFileName = "manifest.json",
        });

        return new FileSystemOtaReleaseService(options, envMock.Object, NullLogger<FileSystemOtaReleaseService>.Instance);
    }

    private void CreateRelease(string platform, string version, IEnumerable<(string Path, string Hash)> manifest)
    {
        var releaseDir = Path.Combine(_tempRoot, platform, version);
        Directory.CreateDirectory(releaseDir);

        var manifestPayload = new
        {
            version,
            manifest = manifest.Select(item => new { path = item.Path, hash = item.Hash }).ToArray(),
        };

        File.WriteAllText(
            Path.Combine(releaseDir, "manifest.json"),
            JsonSerializer.Serialize(manifestPayload));

        foreach (var item in manifest)
        {
            File.WriteAllText(Path.Combine(releaseDir, item.Path), "print('" + item.Path + "')");
        }
    }
}
