using HomeIOT.Api.Contracts;
using HomeIOT.Api.Services.Models;

namespace HomeIOT.Api.Services;

public interface IOtaReleaseService
{
    OtaCheckResponse CheckForUpdate(string platform, string currentVersion);
    OtaFileContent? TryGetReleaseFile(string platform, string version, string relativePath);
}
