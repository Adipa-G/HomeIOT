namespace HomeIOT.Api.Data.Entities;

public sealed class ModuleVariableValueRecord
{
    public Guid Id { get; set; }
    public Guid ModuleAssignmentId { get; set; }
    public string VariableName { get; set; } = string.Empty;
    public string? Value { get; set; }
    public bool ComputedByServer { get; set; }
    public DateTimeOffset? LastComputedAtUtc { get; set; }
    public ModuleAssignmentRecord ModuleAssignment { get; set; } = null!;
}
