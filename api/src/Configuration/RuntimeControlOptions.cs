namespace HomeIOT.Api.Configuration;

public sealed class RuntimeControlOptions
{
    public const string SectionName = "RuntimeControl";

    public int NextHeartbeatMs { get; set; } = 30000;
    public int DevPollIntervalMs { get; set; } = 2000;
    public int ModuleAssignmentPollIntervalMs { get; set; } = 60000;
}
