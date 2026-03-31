namespace HomeIOT.Api.Data.Entities;

public sealed class ModuleVersionRecord
{
    public Guid Id { get; set; }
    public Guid ModuleDefinitionId { get; set; }
    public string Version { get; set; } = string.Empty;
    public string PackageHash { get; set; } = string.Empty;
    public long PackageSizeBytes { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public ModuleDefinitionRecord ModuleDefinition { get; set; } = null!;
}
