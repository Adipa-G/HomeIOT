namespace HomeIOT.Api.Configuration;

public sealed class OtaArtifactOptions
{
    public const string SectionName = "OtaArtifacts";

    public string ArtifactRoot { get; set; } = "../artifacts";
    public string ManifestFileName { get; set; } = "manifest.json";
}
