using System.Text;
using System.IO.Compression;
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

    [Fact]
    public void ListPlatforms_ReturnsAllPlatforms()
    {
        CreateRelease("esp32", "1.0.0", new[] { ("main.py", "hash1") });
        CreateRelease("pico", "1.0.0", new[] { ("main.py", "hash2") });

        var service = CreateService();

        var platforms = service.ListPlatforms();

        Assert.Equal(2, platforms.Count);
        Assert.Contains(platforms, p => p.Platform == "esp32" && p.ReleaseCount == 1);
        Assert.Contains(platforms, p => p.Platform == "pico" && p.ReleaseCount == 1);
    }

    [Fact]
    public void ListPlatforms_ReturnsEmpty_WhenNoArtifacts()
    {
        var service = CreateService();
        var platforms = service.ListPlatforms();
        Assert.Empty(platforms);
    }

    [Fact]
    public void ListReleases_ReturnsVersionsDescending()
    {
        CreateRelease("esp32", "1.0.0", new[] { ("main.py", "hash1") });
        CreateRelease("esp32", "1.2.0", new[] { ("main.py", "hash2"), ("boot.py", "hash3") });

        var service = CreateService();

        var releases = service.ListReleases("esp32");

        Assert.Equal(2, releases.Count);
        Assert.Equal("1.2.0", releases[0].Version);
        Assert.Equal(2, releases[0].FileCount);
        Assert.Equal("1.0.0", releases[1].Version);
    }

    [Fact]
    public void ListReleases_ReturnsEmpty_WhenPlatformMissing()
    {
        var service = CreateService();
        var releases = service.ListReleases("nonexistent");
        Assert.Empty(releases);
    }

    [Fact]
    public void GetReleaseDetail_ReturnsManifestWithSizes()
    {
        CreateRelease("esp32", "1.0.0", new[] { ("main.py", "hash1") });

        var service = CreateService();

        var detail = service.GetReleaseDetail("esp32", "1.0.0");

        Assert.NotNull(detail);
        Assert.Equal("esp32", detail!.Platform);
        Assert.Equal("1.0.0", detail.Version);
        Assert.Single(detail.Manifest);
        Assert.Equal("main.py", detail.Manifest[0].Path);
        Assert.True(detail.Manifest[0].SizeBytes > 0);
    }

    [Fact]
    public void GetReleaseDetail_ReturnsNull_WhenMissing()
    {
        var service = CreateService();
        var detail = service.GetReleaseDetail("esp32", "9.9.9");
        Assert.Null(detail);
    }

    [Fact]
    public async Task UploadRelease_ExtractsZipAndWritesManifest()
    {
        var service = CreateService();

        using var zipStream = CreateTestZip(new Dictionary<string, string>
        {
            ["main.py"] = "print('hello')",
            ["lib/utils.py"] = "# utils",
        });

        await service.UploadReleaseAsync("esp32", "2.0.0", zipStream);

        var detail = service.GetReleaseDetail("esp32", "2.0.0");

        Assert.NotNull(detail);
        Assert.Equal("2.0.0", detail!.Version);
        Assert.Equal(2, detail.FileCount);
        Assert.Contains(detail.Manifest, f => f.Path == "main.py");
        Assert.Contains(detail.Manifest, f => f.Path == "lib/utils.py");
        Assert.All(detail.Manifest, f => Assert.NotEmpty(f.Hash));
    }

    [Fact]
    public void DeleteRelease_RemovesDirectory()
    {
        CreateRelease("esp32", "1.0.0", new[] { ("main.py", "hash1") });

        var service = CreateService();

        var deleted = service.DeleteRelease("esp32", "1.0.0");

        Assert.True(deleted);
        Assert.Null(service.GetReleaseDetail("esp32", "1.0.0"));
    }

    [Fact]
    public void DeleteRelease_ReturnsFalse_WhenMissing()
    {
        var service = CreateService();
        Assert.False(service.DeleteRelease("esp32", "9.9.9"));
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

    private static MemoryStream CreateTestZip(Dictionary<string, string> files)
    {
        var ms = new MemoryStream();
        using (var archive = new ZipArchive(ms, ZipArchiveMode.Create, leaveOpen: true))
        {
            foreach (var (path, content) in files)
            {
                var entry = archive.CreateEntry(path);
                using var writer = new StreamWriter(entry.Open());
                writer.Write(content);
            }
        }

        ms.Position = 0;
        return ms;
    }
}
