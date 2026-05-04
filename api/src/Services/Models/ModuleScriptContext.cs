namespace HomeIOT.Api.Services.Models;

public sealed class ModuleScriptContext
{
    public string DeviceId { get; set; } = string.Empty;
    public string ModuleId { get; set; } = string.Empty;
    public IModuleDataAccess Data { get; set; } = null!;
}
