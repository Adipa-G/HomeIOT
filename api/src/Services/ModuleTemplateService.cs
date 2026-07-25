using System.Text.Json;
using System.Text.Json.Serialization;
using HomeIOT.Api.Configuration;
using HomeIOT.Api.Contracts;
using Microsoft.Extensions.Options;

namespace HomeIOT.Api.Services;

public sealed class ModuleTemplateService : IModuleTemplateService
{
    private static readonly JsonSerializerOptions MetaJsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    private readonly string _templatesRoot;
    private readonly ILogger<ModuleTemplateService> _logger;

    public ModuleTemplateService(
        IOptions<ModuleTemplateOptions> templateOptions,
        IWebHostEnvironment environment,
        ILogger<ModuleTemplateService> logger)
    {
        _logger = logger;

        var configuredRoot = string.IsNullOrWhiteSpace(templateOptions.Value.TemplatesRoot)
            ? "Templates"
            : templateOptions.Value.TemplatesRoot;

        _templatesRoot = Path.IsPathRooted(configuredRoot)
            ? Path.GetFullPath(configuredRoot)
            : Path.GetFullPath(Path.Combine(environment.ContentRootPath, configuredRoot));
    }

    public async Task<List<ModuleTemplateItem>> GetTemplatesAsync(CancellationToken ct = default)
    {
        var items = new List<ModuleTemplateItem>();

        if (!Directory.Exists(_templatesRoot))
        {
            return items;
        }

        foreach (var templateDir in Directory.GetDirectories(_templatesRoot))
        {
            var metaPath = Path.Combine(templateDir, "meta.json");
            if (!File.Exists(metaPath))
            {
                _logger.LogWarning("Skipping module template folder without meta.json: {TemplateDir}", templateDir);
                continue;
            }

            try
            {
                var metaJson = await File.ReadAllTextAsync(metaPath, ct);
                var meta = JsonSerializer.Deserialize<TemplateMeta>(metaJson, MetaJsonOptions);

                if (meta is null || string.IsNullOrWhiteSpace(meta.Id) || meta.Variants is null || meta.Variants.Count == 0)
                {
                    _logger.LogWarning("Skipping invalid module template meta.json: {MetaPath}", metaPath);
                    continue;
                }

                var variants = new List<ModuleTemplateVariantItem>();
                foreach (var variant in meta.Variants)
                {
                    if (string.IsNullOrWhiteSpace(variant.Platform) || string.IsNullOrWhiteSpace(variant.File))
                    {
                        continue;
                    }

                    var codePath = Path.Combine(templateDir, variant.File);
                    if (!File.Exists(codePath))
                    {
                        _logger.LogWarning("Skipping module template variant with missing code file: {CodePath}", codePath);
                        continue;
                    }

                    var code = await File.ReadAllTextAsync(codePath, ct);
                    variants.Add(new ModuleTemplateVariantItem(variant.Platform, code));
                }

                if (variants.Count == 0)
                {
                    continue;
                }

                items.Add(new ModuleTemplateItem(
                    meta.Id,
                    meta.Name ?? meta.Id,
                    meta.Description ?? string.Empty,
                    meta.SetupGuide ?? string.Empty,
                    variants));
            }
            catch (JsonException ex)
            {
                _logger.LogWarning(ex, "Failed to parse module template meta.json: {MetaPath}", metaPath);
            }
        }

        return items.OrderBy(i => i.Name, StringComparer.OrdinalIgnoreCase).ToList();
    }

    private sealed class TemplateMeta
    {
        public string? Id { get; set; }
        public string? Name { get; set; }
        public string? Description { get; set; }

        [JsonPropertyName("setup_guide")]
        public string? SetupGuide { get; set; }

        public List<TemplateMetaVariant>? Variants { get; set; }
    }

    private sealed class TemplateMetaVariant
    {
        public string? Platform { get; set; }
        public string? File { get; set; }
    }
}
