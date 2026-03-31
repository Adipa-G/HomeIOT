namespace HomeIOT.Api.Configuration;

public sealed class ModuleStorageOptions
{
    public const string SectionName = "ModuleStorage";

    public string PackageRoot { get; set; } = "../modules";
}
