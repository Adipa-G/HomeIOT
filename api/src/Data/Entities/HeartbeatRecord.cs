namespace HomeIOT.Api.Data.Entities;

public sealed class HeartbeatRecord
{
    public Guid Id { get; set; }
    public Guid DeviceRecordId { get; set; }
    public DeviceRecord Device { get; set; } = null!;
    public long? ClientTimestamp { get; set; }
    public long? UptimeMs { get; set; }
    public long? FreeMemoryBytes { get; set; }
    public DateTimeOffset ReceivedAtUtc { get; set; }
}
