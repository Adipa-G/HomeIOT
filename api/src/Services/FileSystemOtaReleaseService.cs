using System.Text.Json;
using HomeIOT.Api.Configuration;
using HomeIOT.Api.Contracts;
using Microsoft.Extensions.Options;

namespace HomeIOT.Api.Services;

public sealed class FileSystemOtaReleaseService : IOtaReleaseService
{
    private static readonly JsonSerializerOptions ManifestJsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    private readonly string _artifactRoot;
    private readonly string _manifestFileName;
    private readonly ILogger<FileSystemOtaReleaseService> _logger;

    public FileSystemOtaReleaseService(
        IOptions<OtaArtifactOptions> options,
        IWebHostEnvironment environment,
        ILogger<FileSystemOtaReleaseService> logger)
    {
        _logger = logger;

        var configuredRoot = string.IsNullOrWhiteSpace(options.Value.ArtifactRoot)
            ? "../artifacts"
            : options.Value.ArtifactRoot;

        _artifactRoot = Path.IsPathRooted(configuredRoot)
            ? Path.GetFullPath(configuredRoot)
            : Path.GetFullPath(Path.Combine(environment.ContentRootPath, configuredRoot));

        _manifestFileName = string.IsNullOrWhiteSpace(options.Value.ManifestFileName)
            ? "manifest.json"
            : options.Value.ManifestFileName.Trim();
    }

    public OtaCheckResponse CheckForUpdate(string platform, string currentVersion)
    {
        var platformRoot = Path.Combine(_artifactRoot, platform);
        if (!Directory.Exists(platformRoot))
        {
            _logger.LogInformation("No OTA artifacts for platform {Platform}", platform);
            return new OtaCheckResponse(false);
        }

        var releases = LoadReleases(platformRoot);
        if (releases.Count == 0)
        {
            return new OtaCheckResponse(false);
        }

        ReleaseEntry? latest = null;
        foreach (var release in releases)
        {
            if (CompareVersions(release.Version, currentVersion) <= 0)
            {
                continue;
            }

            if (latest is null || CompareVersions(release.Version, latest.Version) > 0)
            {
                latest = release;
            }
        }

        if (latest is null)
        {
            return new OtaCheckResponse(false);
        }

        return new OtaCheckResponse(true, latest.Version, latest.Manifest);
    }

    public OtaFileContent? TryGetReleaseFile(string platform, string version, string relativePath)
    {
        var platformRoot = Path.Combine(_artifactRoot, platform);
        var releaseRoot = Path.Combine(platformRoot, version);
        if (!Directory.Exists(releaseRoot))
        {
            return null;
        }

        var release = LoadRelease(releaseRoot);
        if (release is null)
        {
            return null;
        }

        var manifestItem = release.Manifest.FirstOrDefault(x => string.Equals(x.Path, relativePath, StringComparison.Ordinal));
        if (manifestItem is null)
        {
            return null;
        }

        var fullPath = TryResolveSafePath(releaseRoot, manifestItem.Path);
        if (fullPath is null || !File.Exists(fullPath))
        {
            return null;
        }

        return new OtaFileContent(File.ReadAllBytes(fullPath), Path.GetFileName(fullPath));
    }

    private List<ReleaseEntry> LoadReleases(string platformRoot)
    {
        var releases = new List<ReleaseEntry>();

        foreach (var dir in Directory.EnumerateDirectories(platformRoot))
        {
            var release = LoadRelease(dir);
            if (release is null)
            {
                continue;
            }

            releases.Add(release);
        }

        return releases;
    }

    private ReleaseEntry? LoadRelease(string releaseDirectory)
    {
        var manifestPath = Path.Combine(releaseDirectory, _manifestFileName);
        if (!File.Exists(manifestPath))
        {
            return null;
        }

        ManifestDocument? document;
        try
        {
            document = JsonSerializer.Deserialize<ManifestDocument>(File.ReadAllText(manifestPath), ManifestJsonOptions);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Invalid OTA manifest: {ManifestPath}", manifestPath);
            return null;
        }

        if (document is null || document.Manifest is null || document.Manifest.Count == 0)
        {
            return null;
        }

        var version = string.IsNullOrWhiteSpace(document.Version)
            ? Path.GetFileName(releaseDirectory)
            : document.Version.Trim();

        var normalizedManifest = new List<OtaManifestItem>();
        foreach (var item in document.Manifest)
        {
            if (item is null || string.IsNullOrWhiteSpace(item.Path) || string.IsNullOrWhiteSpace(item.Hash))
            {
                continue;
            }

            var cleanPath = item.Path.Replace('\\', '/').Trim();
            if (!IsSafeRelativePath(cleanPath))
            {
                continue;
            }

            normalizedManifest.Add(new OtaManifestItem(cleanPath, item.Hash.Trim()));
        }

        if (normalizedManifest.Count == 0)
        {
            return null;
        }

        return new ReleaseEntry(version, normalizedManifest);
    }

    private static bool IsSafeRelativePath(string path)
    {
        if (path.StartsWith("/", StringComparison.Ordinal) || path.StartsWith("../", StringComparison.Ordinal))
        {
            return false;
        }

        return !path.Contains("..", StringComparison.Ordinal);
    }

    private static string? TryResolveSafePath(string rootPath, string relativePath)
    {
        var candidate = Path.GetFullPath(Path.Combine(rootPath, relativePath.Replace('/', Path.DirectorySeparatorChar)));
        var fullRoot = Path.GetFullPath(rootPath);
        if (!candidate.StartsWith(fullRoot, StringComparison.OrdinalIgnoreCase))
        {
            return null;
        }

        return candidate;
    }

    private static int CompareVersions(string left, string right)
    {
        if (Version.TryParse(left, out var l) && Version.TryParse(right, out var r))
        {
            return l.CompareTo(r);
        }

        return string.Compare(left, right, StringComparison.Ordinal);
    }

    private sealed record ReleaseEntry(string Version, IReadOnlyList<OtaManifestItem> Manifest);

    private sealed class ManifestDocument
    {
        public string? Version { get; set; }
        public List<ManifestItemDocument>? Manifest { get; set; }
    }

    private sealed class ManifestItemDocument
    {
        public string? Path { get; set; }
        public string? Hash { get; set; }
    }
}
