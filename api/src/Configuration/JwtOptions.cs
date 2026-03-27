namespace HomeIOT.Api.Configuration;

public sealed class JwtOptions
{
    public const string SectionName = "Jwt";

    public string SecretKey { get; set; } = string.Empty;
    public string Issuer { get; set; } = "HomeIOT";
    public int ExpirationHours { get; set; } = 24;
}
