using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services.Models;

namespace HomeIOT.Api.Services;

public interface IOtaReleaseService
{
    OtaCheckResponse CheckForUpdate(string platform, string currentVersion);
    OtaFileContent? TryGetReleaseFile(string platform, string version, string relativePath);

    // Admin
    List<OtaPlatformListItem> ListPlatforms();
    List<OtaReleaseListItem> ListReleases(string platform);
    OtaReleaseDetailResponse? GetReleaseDetail(string platform, string version);
    Task UploadReleaseAsync(string platform, string version, Stream zipStream, CancellationToken ct = default);
    bool DeleteRelease(string platform, string version);
}
