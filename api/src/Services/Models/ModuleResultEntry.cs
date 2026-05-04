using System.Text.Json;

namespace HomeIOT.Api.Services.Models;

public sealed record ModuleResultEntry(
    string ModuleId,
    string ModuleVersion,
    DateTimeOffset StartedAtUtc,
    string Status,
    JsonDocument? Output);
