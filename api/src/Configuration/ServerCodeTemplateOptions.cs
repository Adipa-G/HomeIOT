namespace HomeIOT.Api.Configuration;

public sealed class ServerCodeTemplateOptions
{
    public const string SectionName = "ServerCodeTemplates";

    public string TemplatesRoot { get; set; } = "Templates/server-code";
}
