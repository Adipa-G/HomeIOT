namespace HomeIOT.Api.Data.Entities;

public sealed class ModuleResultRecord
{
    public Guid Id { get; set; }
    public string DeviceId { get; set; } = string.Empty;
    public string ModuleId { get; set; } = string.Empty;
    public string ModuleVersion { get; set; } = string.Empty;
    public string RunId { get; set; } = string.Empty;
    public DateTimeOffset StartedAtUtc { get; set; }
    public DateTimeOffset FinishedAtUtc { get; set; }
    public int ElapsedMs { get; set; }
    public string Status { get; set; } = string.Empty;
    public string? Output { get; set; }
    public string? VariableValues { get; set; }
    public string? ErrorMessage { get; set; }
    public DateTimeOffset ReceivedAtUtc { get; set; }
}
