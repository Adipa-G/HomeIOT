namespace HomeIOT.Api.Data.Entities;

public sealed class ModuleVariableDefRecord
{
    public Guid Id { get; set; }
    public Guid ModuleDefinitionId { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Type { get; set; } = "string";
    public string? DefaultValue { get; set; }
    public string? Description { get; set; }
    public string? ServerCode { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public ModuleDefinitionRecord ModuleDefinition { get; set; } = null!;
}
