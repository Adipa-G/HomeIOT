using System.Text.Json.Serialization;
using HomeIOT.Api.Configuration;
using HomeIOT.Api.Contracts;
using Microsoft.Extensions.Options;

namespace HomeIOT.Api.Services;

public sealed class DeviceCodeTemplateService : IDeviceCodeTemplateService
{
    private readonly string _templatesRoot;
    private readonly ILogger<DeviceCodeTemplateService> _logger;

    public DeviceCodeTemplateService(
        IOptions<DeviceCodeTemplateOptions> templateOptions,
        IWebHostEnvironment environment,
        ILogger<DeviceCodeTemplateService> logger)
    {
        _logger = logger;

        var configuredRoot = string.IsNullOrWhiteSpace(templateOptions.Value.TemplatesRoot)
            ? "Templates/device-code"
            : templateOptions.Value.TemplatesRoot;

        _templatesRoot = TemplateDirectoryScanner.ResolveRoot(configuredRoot, environment);
    }

    public async Task<List<DeviceCodeTemplateItem>> GetTemplatesAsync(CancellationToken ct = default)
    {
        var items = new List<DeviceCodeTemplateItem>();

        var scanned = await TemplateDirectoryScanner.ScanAsync<TemplateMeta>(_templatesRoot, _logger, "device code", ct);

        foreach (var (templateDir, meta) in scanned)
        {
            if (string.IsNullOrWhiteSpace(meta.Id) || meta.Variants is null || meta.Variants.Count == 0)
            {
                _logger.LogWarning("Skipping invalid device code template meta.json in: {TemplateDir}", templateDir);
                continue;
            }

            var variants = new List<DeviceCodeTemplateVariantItem>();
            foreach (var variant in meta.Variants)
            {
                if (string.IsNullOrWhiteSpace(variant.Platform) || string.IsNullOrWhiteSpace(variant.File))
                {
                    continue;
                }

                var codePath = Path.Combine(templateDir, variant.File);
                if (!File.Exists(codePath))
                {
                    _logger.LogWarning("Skipping device code template variant with missing code file: {CodePath}", codePath);
                    continue;
                }

                var code = await File.ReadAllTextAsync(codePath, ct);
                variants.Add(new DeviceCodeTemplateVariantItem(variant.Platform, code));
            }

            if (variants.Count == 0)
            {
                continue;
            }

            items.Add(new DeviceCodeTemplateItem(
                meta.Id,
                meta.Name ?? meta.Id,
                meta.Description ?? string.Empty,
                meta.SetupGuide ?? string.Empty,
                variants));
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
