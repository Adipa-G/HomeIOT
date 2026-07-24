namespace HomeIOT.Api.Configuration;

public sealed class DataRetentionOptions
{
    public const string SectionName = "DataRetention";

    /// <summary>
    /// Number of days to keep heartbeat and log records before they are purged.
    /// A value of 0 or less disables cleanup (records are kept forever).
    /// </summary>
    public int RetentionDays { get; set; } = 30;

    /// <summary>
    /// How often the cleanup pass runs, in minutes.
    /// </summary>
    public int CleanupIntervalMinutes { get; set; } = 60;
}
