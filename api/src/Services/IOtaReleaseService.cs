using HomeIOT.Api.Contracts;

namespace HomeIOT.Api.Services;

public interface IOtaReleaseService
{
    OtaCheckResponse CheckForUpdate(string platform, string currentVersion);
    OtaFileContent? TryGetReleaseFile(string platform, string version, string relativePath);
}

public sealed record OtaFileContent(byte[] Content, string FileName);
