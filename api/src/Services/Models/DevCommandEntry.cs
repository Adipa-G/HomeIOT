namespace HomeIOT.Api.Services.Models;

public sealed record DevCommandEntry(
    string CommandId,
    string DeviceId,
    string RevisionHash,
    string DedupeToken,
    string Code,
    int? TimeoutMs,
    DateTimeOffset QueuedAt);
