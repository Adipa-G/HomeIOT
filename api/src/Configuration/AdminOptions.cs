namespace HomeIOT.Api.Configuration;

public sealed class AdminOptions
{
    public const string SectionName = "Admin";

    public string MasterUsername { get; set; } = "Admin";
    public string MasterPassword { get; set; } = string.Empty;
}
