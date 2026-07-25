namespace HomeIOT.Api.Configuration;

public sealed class ModuleTemplateOptions
{
    public const string SectionName = "ModuleTemplates";

    public string TemplatesRoot { get; set; } = "Templates";
}
