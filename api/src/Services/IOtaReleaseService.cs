using HomeIOT.Api.Contracts;

namespace HomeIOT.Api.Services;

public interface IOtaReleaseService
{
    OtaCheckResponse CheckForUpdate(string platform, string currentVersion);
    Task StreamReleaseAsync(string platform, string version, Stream output, CancellationToken ct = default);

    // Admin
    List<OtaPlatformListItem> ListPlatforms();
    List<OtaReleaseListItem> ListReleases(string platform);
    OtaReleaseDetailResponse? GetReleaseDetail(string platform, string version);
    Task UploadReleaseAsync(string platform, string version, Stream zipStream, CancellationToken ct = default);
    bool DeleteRelease(string platform, string version);
}
