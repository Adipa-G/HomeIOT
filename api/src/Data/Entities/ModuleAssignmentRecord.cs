namespace HomeIOT.Api.Data.Entities;

public sealed class ModuleAssignmentRecord
{
    public Guid Id { get; set; }
    public Guid DeviceRecordId { get; set; }
    public Guid ModuleDefinitionId { get; set; }
    public Guid ModuleVersionId { get; set; }
    public int IntervalMs { get; set; } = 60000;
    public int TimeoutMs { get; set; } = 5000;
    public string Entrypoint { get; set; } = "run";
    public bool Enabled { get; set; } = true;
    public bool ShowInDashboard { get; set; } = false;
    public DateTimeOffset CreatedAtUtc { get; set; }
    public DateTimeOffset UpdatedAtUtc { get; set; }
    public DeviceRecord Device { get; set; } = null!;
    public ModuleDefinitionRecord ModuleDefinition { get; set; } = null!;
    public ModuleVersionRecord ModuleVersion { get; set; } = null!;
    public ICollection<ModuleVariableValueRecord> VariableValues { get; set; } = new List<ModuleVariableValueRecord>();
}
