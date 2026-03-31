namespace HomeIOT.Api.Data.Entities;

public sealed class ModuleStatusRecord
{
    public Guid Id { get; set; }
    public string DeviceId { get; set; } = string.Empty;
    public string ModuleId { get; set; } = string.Empty;
    public string ModuleVersion { get; set; } = string.Empty;
    public bool Disabled { get; set; }
    public string? DisabledReason { get; set; }
    public int FailedStartCount { get; set; }
    public DateTimeOffset? DisabledAtUtc { get; set; }
    public DateTimeOffset ReceivedAtUtc { get; set; }
}
