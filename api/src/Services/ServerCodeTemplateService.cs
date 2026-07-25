using System.Text.Json.Serialization;
using HomeIOT.Api.Configuration;
using HomeIOT.Api.Contracts;
using Microsoft.Extensions.Options;

namespace HomeIOT.Api.Services;

public sealed class ServerCodeTemplateService : IServerCodeTemplateService
{
    private readonly string _templatesRoot;
    private readonly ILogger<ServerCodeTemplateService> _logger;

    public ServerCodeTemplateService(
        IOptions<ServerCodeTemplateOptions> templateOptions,
        IWebHostEnvironment environment,
        ILogger<ServerCodeTemplateService> logger)
    {
        _logger = logger;

        var configuredRoot = string.IsNullOrWhiteSpace(templateOptions.Value.TemplatesRoot)
            ? "Templates/server-code"
            : templateOptions.Value.TemplatesRoot;

        _templatesRoot = TemplateDirectoryScanner.ResolveRoot(configuredRoot, environment);
    }

    public async Task<List<ServerCodeTemplateItem>> GetTemplatesAsync(CancellationToken ct = default)
    {
        var items = new List<ServerCodeTemplateItem>();

        var scanned = await TemplateDirectoryScanner.ScanAsync<TemplateMeta>(_templatesRoot, _logger, "server code", ct);

        foreach (var (templateDir, meta) in scanned)
        {
            if (string.IsNullOrWhiteSpace(meta.Id) || string.IsNullOrWhiteSpace(meta.File))
            {
                _logger.LogWarning("Skipping invalid server code template meta.json in: {TemplateDir}", templateDir);
                continue;
            }

            var codePath = Path.Combine(templateDir, meta.File);
            if (!File.Exists(codePath))
            {
                _logger.LogWarning("Skipping server code template with missing code file: {CodePath}", codePath);
                continue;
            }

            var code = await File.ReadAllTextAsync(codePath, ct);

            items.Add(new ServerCodeTemplateItem(
                meta.Id,
                meta.Name ?? meta.Id,
                meta.Description ?? string.Empty,
                meta.SetupGuide ?? string.Empty,
                code));
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

        public string? File { get; set; }
    }
}
