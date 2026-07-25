using System.Text.Json;

namespace HomeIOT.Api.Services;

/// <summary>
/// Shared directory-scanning/meta.json-parsing logic used by both
/// <see cref="DeviceCodeTemplateService"/> and <see cref="ServerCodeTemplateService"/>.
/// Each service is still responsible for its own item-shape validation
/// (e.g. variants vs. single code file) and code-file loading.
/// </summary>
internal static class TemplateDirectoryScanner
{
    private static readonly JsonSerializerOptions MetaJsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public static string ResolveRoot(string configuredRoot, IWebHostEnvironment environment)
    {
        return Path.IsPathRooted(configuredRoot)
            ? Path.GetFullPath(configuredRoot)
            : Path.GetFullPath(Path.Combine(environment.ContentRootPath, configuredRoot));
    }

    public static async Task<List<(string TemplateDir, TMeta Meta)>> ScanAsync<TMeta>(
        string templatesRoot,
        ILogger logger,
        string templateKindLabel,
        CancellationToken ct = default)
        where TMeta : class
    {
        var results = new List<(string TemplateDir, TMeta Meta)>();

        if (!Directory.Exists(templatesRoot))
        {
            return results;
        }

        foreach (var templateDir in Directory.GetDirectories(templatesRoot))
        {
            var metaPath = Path.Combine(templateDir, "meta.json");
            if (!File.Exists(metaPath))
            {
                logger.LogWarning("Skipping {Kind} template folder without meta.json: {TemplateDir}", templateKindLabel, templateDir);
                continue;
            }

            try
            {
                var metaJson = await File.ReadAllTextAsync(metaPath, ct);
                var meta = JsonSerializer.Deserialize<TMeta>(metaJson, MetaJsonOptions);

                if (meta is null)
                {
                    logger.LogWarning("Skipping invalid {Kind} template meta.json: {MetaPath}", templateKindLabel, metaPath);
                    continue;
                }

                results.Add((templateDir, meta));
            }
            catch (JsonException ex)
            {
                logger.LogWarning(ex, "Failed to parse {Kind} template meta.json: {MetaPath}", templateKindLabel, metaPath);
            }
        }

        return results;
    }
}
