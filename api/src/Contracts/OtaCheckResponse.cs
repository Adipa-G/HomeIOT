namespace HomeIOT.Api.Contracts;

public sealed record OtaCheckResponse(bool Available, string? Version = null, IReadOnlyList<OtaManifestItem>? Manifest = null);
