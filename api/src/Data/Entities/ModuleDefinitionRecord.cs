namespace HomeIOT.Api.Data.Entities;

public sealed class ModuleDefinitionRecord
{
    public Guid Id { get; set; }
    public string ModuleId { get; set; } = string.Empty;
    public string? Description { get; set; }
    public string DefaultEntrypoint { get; set; } = "run";
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public ICollection<ModuleVersionRecord> Versions { get; set; } = new List<ModuleVersionRecord>();
    public ICollection<ModuleAssignmentRecord> Assignments { get; set; } = new List<ModuleAssignmentRecord>();
    public ICollection<ModuleVariableDefRecord> VariableDefs { get; set; } = new List<ModuleVariableDefRecord>();
}
