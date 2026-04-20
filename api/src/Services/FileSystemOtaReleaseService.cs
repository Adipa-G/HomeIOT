using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
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

    private static readonly JsonSerializerOptions ManifestWriteOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true,
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

    public async Task StreamReleaseAsync(string platform, string version, Stream output, CancellationToken ct = default)
    {
        var releaseRoot = Path.Combine(_artifactRoot, platform, version);
        var release = LoadRelease(releaseRoot);
        if (release is null)
        {
            return;
        }

        foreach (var item in release.Manifest)
        {
            var fullPath = TryResolveSafePath(releaseRoot, item.Path);
            if (fullPath is null || !File.Exists(fullPath))
            {
                continue;
            }

            var sizeBytes = new FileInfo(fullPath).Length;
            await output.WriteAsync(Encoding.ASCII.GetBytes($"HASH:{item.Hash}\n"), ct);
            await output.WriteAsync(Encoding.ASCII.GetBytes($"FILE:{item.Path}\n"), ct);
            await output.WriteAsync(Encoding.ASCII.GetBytes($"SIZE:{sizeBytes}\n"), ct);

            using var fileStream = new FileStream(fullPath, FileMode.Open, FileAccess.Read, FileShare.Read);
            await fileStream.CopyToAsync(output, ct);
        }

        await output.WriteAsync(Encoding.ASCII.GetBytes("END\n"), ct);
        await output.FlushAsync(ct);
    }

    // ──────────────────────────────────────────────
    //  Admin
    // ──────────────────────────────────────────────

    public List<OtaPlatformListItem> ListPlatforms()
    {
        if (!Directory.Exists(_artifactRoot))
            return new List<OtaPlatformListItem>();

        var result = new List<OtaPlatformListItem>();
        foreach (var dir in Directory.EnumerateDirectories(_artifactRoot))
        {
            var platform = Path.GetFileName(dir);
            var releases = LoadReleases(dir);
            result.Add(new OtaPlatformListItem(platform, releases.Count));
        }

        return result.OrderBy(p => p.Platform).ToList();
    }

    public List<OtaReleaseListItem> ListReleases(string platform)
    {
        var platformRoot = Path.Combine(_artifactRoot, platform);
        if (!Directory.Exists(platformRoot))
            return new List<OtaReleaseListItem>();

        var releases = LoadReleases(platformRoot);
        var result = new List<OtaReleaseListItem>();
        foreach (var release in releases)
        {
            var releaseDir = Path.Combine(platformRoot, release.Version);
            long totalSize = 0;
            foreach (var item in release.Manifest)
            {
                var filePath = TryResolveSafePath(releaseDir, item.Path);
                if (filePath is not null && File.Exists(filePath))
                    totalSize += new FileInfo(filePath).Length;
            }

            result.Add(new OtaReleaseListItem(release.Version, release.Manifest.Count, totalSize));
        }

        return result
            .OrderByDescending(r =>
                Version.TryParse(r.Version, out var v) ? v : new Version(0, 0))
            .ToList();
    }

    public OtaReleaseDetailResponse? GetReleaseDetail(string platform, string version)
    {
        var releaseDir = Path.Combine(_artifactRoot, platform, version);
        if (!Directory.Exists(releaseDir))
            return null;

        var release = LoadRelease(releaseDir);
        if (release is null)
            return null;

        var manifestFiles = new List<OtaManifestFileItem>();
        long totalSize = 0;
        foreach (var item in release.Manifest)
        {
            var filePath = TryResolveSafePath(releaseDir, item.Path);
            long fileSize = 0;
            if (filePath is not null && File.Exists(filePath))
                fileSize = new FileInfo(filePath).Length;

            totalSize += fileSize;
            manifestFiles.Add(new OtaManifestFileItem(item.Path, item.Hash, fileSize));
        }

        return new OtaReleaseDetailResponse(platform, release.Version, manifestFiles.Count, totalSize, manifestFiles);
    }

    public async Task UploadReleaseAsync(string platform, string version, Stream zipStream, CancellationToken ct = default)
    {
        var releaseDir = Path.Combine(_artifactRoot, platform, version);
        Directory.CreateDirectory(releaseDir);

        using var archive = new ZipArchive(zipStream, ZipArchiveMode.Read);

        var manifestItems = new List<ManifestItemDocument>();

        foreach (var entry in archive.Entries)
        {
            // Skip directories
            if (string.IsNullOrEmpty(entry.Name))
                continue;

            var relativePath = entry.FullName.Replace('\\', '/');
            if (!IsSafeRelativePath(relativePath))
                continue;

            var targetPath = TryResolveSafePath(releaseDir, relativePath);
            if (targetPath is null)
                continue;

            var targetDir = Path.GetDirectoryName(targetPath);
            if (targetDir is not null)
                Directory.CreateDirectory(targetDir);

            using (var entryStream = entry.Open())
            using (var fileStream = new FileStream(targetPath, FileMode.Create, FileAccess.Write))
            {
                await entryStream.CopyToAsync(fileStream, ct);
            }

            // Compute hash from written file
            string hash;
            using (var readStream = new FileStream(targetPath, FileMode.Open, FileAccess.Read))
            {
                var hashBytes = await SHA256.HashDataAsync(readStream, ct);
                hash = Convert.ToHexString(hashBytes).ToLowerInvariant();
            }

            manifestItems.Add(new ManifestItemDocument { Path = relativePath, Hash = hash });
        }

        // Write manifest.json
        var document = new ManifestDocument
        {
            Version = version,
            Manifest = manifestItems,
        };
        var manifestJson = JsonSerializer.Serialize(document, ManifestWriteOptions);
        var manifestPath = Path.Combine(releaseDir, _manifestFileName);
        await File.WriteAllTextAsync(manifestPath, manifestJson, ct);
    }

    public bool DeleteRelease(string platform, string version)
    {
        var releaseDir = Path.Combine(_artifactRoot, platform, version);
        if (!Directory.Exists(releaseDir))
            return false;

        Directory.Delete(releaseDir, recursive: true);
        return true;
    }

    // ──────────────────────────────────────────────
    //  Private helpers
    // ──────────────────────────────────────────────

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
