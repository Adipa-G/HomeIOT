namespace HomeIOT.Api.Data.Entities;

public sealed class DeviceRecord
{
    public Guid Id { get; set; }
    public string DeviceId { get; set; } = string.Empty;
    public string ApiKey { get; set; } = string.Empty;
    public string? Platform { get; set; }
    public string? Version { get; set; }
    public string? Ip { get; set; }
    public string Mode { get; set; } = "production";
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public DateTimeOffset? LastHeartbeatAtUtc { get; set; }
    public ICollection<HeartbeatRecord> Heartbeats { get; set; } = new List<HeartbeatRecord>();
    public ICollection<LogBatchRecord> LogBatches { get; set; } = new List<LogBatchRecord>();
}
