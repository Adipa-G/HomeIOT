using HomeIOT.Api.Contracts;

namespace HomeIOT.Api.Services;

public interface IOtaReleaseService
{
    OtaCheckResponse CheckForUpdate(string platform, string currentVersion);
    Task StreamReleaseAsync(string platform, string version, Stream output, CancellationToken ct = default);

    /// <summary>Returns the highest available release version for a platform, or null if none.</summary>
    string? GetLatestVersion(string platform);

    /// <summary>Reads a text file from a release, or returns null if the release or file does not exist.</summary>
    string? ReadReleaseFileText(string platform, string version, string relativePath);

    // Admin
    List<OtaPlatformListItem> ListPlatforms();
    List<OtaReleaseListItem> ListReleases(string platform);
    OtaReleaseDetailResponse? GetReleaseDetail(string platform, string version);
    Task UploadReleaseAsync(string platform, string version, Stream zipStream, CancellationToken ct = default);
    bool DeleteRelease(string platform, string version);
}
