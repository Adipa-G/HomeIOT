using System.Text.Json;

namespace HomeIOT.Api.Services.Models;

public sealed record DevCommandResultPayload(
    string CommandId,
    string? RevisionHash,
    string? DedupeToken,
    string Status,
    string? StartedAtUtc,
    string? FinishedAtUtc,
    long ElapsedMs,
    int ExitCode,
    string? Stdout,
    string? Stderr,
    JsonElement? Data,
    DateTimeOffset ReceivedAt);
