namespace HomeIOT.Api.Data.Entities;

public sealed class LogBatchRecord
{
    public Guid Id { get; set; }
    public Guid DeviceRecordId { get; set; }
    public DeviceRecord Device { get; set; } = null!;
    public string Reason { get; set; } = string.Empty;
    public long SentAt { get; set; }
    public int DroppedCount { get; set; }
    public bool Truncated { get; set; }
    public int ReceivedCount { get; set; }
    public string LogsJson { get; set; } = "[]";
    public DateTimeOffset ReceivedAtUtc { get; set; }
}
