namespace HomeIOT.Api.Data.Entities;

public sealed class ModuleVariableVisualizationRecord
{
    public Guid Id { get; set; }
    public Guid ModuleVariableDefId { get; set; }
    public string JsonPath { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
    public string? VisualizationType { get; set; }
    public string? VisualizationConfig { get; set; }
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public ModuleVariableDefRecord ModuleVariableDef { get; set; } = null!;
}
