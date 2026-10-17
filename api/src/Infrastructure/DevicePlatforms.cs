namespace HomeIOT.Api.Infrastructure;

public static class DevicePlatforms
{
    public static readonly IReadOnlyList<string> Provisionable = ["esp32", "pico"];

    public static bool IsProvisionable(string? platform)
    {
        return platform is not null && Provisionable.Contains(platform, StringComparer.Ordinal);
    }
}
