namespace HomeIOT.Api.Configuration;

public sealed class DeviceCodeTemplateOptions
{
    public const string SectionName = "DeviceCodeTemplates";

    public string TemplatesRoot { get; set; } = "Templates/device-code";
}
