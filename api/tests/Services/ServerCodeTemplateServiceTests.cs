using HomeIOT.Api.Configuration;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public class ServerCodeTemplateServiceTests : IDisposable
{
    private readonly string _tempDir;
    private readonly ServerCodeTemplateService _service;

    public ServerCodeTemplateServiceTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), $"server_code_template_test_{Guid.NewGuid():N}");
        Directory.CreateDirectory(_tempDir);

        var templateOptions = new Mock<IOptions<ServerCodeTemplateOptions>>();
        templateOptions.Setup(x => x.Value).Returns(new ServerCodeTemplateOptions { TemplatesRoot = _tempDir });

        var env = new Mock<IWebHostEnvironment>();
        env.Setup(x => x.ContentRootPath).Returns(_tempDir);

        var logger = new Mock<ILogger<ServerCodeTemplateService>>();

        _service = new ServerCodeTemplateService(templateOptions.Object, env.Object, logger.Object);
    }

    public void Dispose()
    {
        if (Directory.Exists(_tempDir))
            Directory.Delete(_tempDir, true);
    }

    private void CreateTemplate(string id, string metaJson, string? codeFileName = "code.csx", string codeContent = "return 1;")
    {
        var dir = Path.Combine(_tempDir, id);
        Directory.CreateDirectory(dir);
        File.WriteAllText(Path.Combine(dir, "meta.json"), metaJson);
        if (codeFileName is not null)
            File.WriteAllText(Path.Combine(dir, codeFileName), codeContent);
    }

    [Fact]
    public async Task GetTemplatesAsync_ReturnsEmptyList_WhenTemplatesDirMissing()
    {
        Directory.Delete(_tempDir, true);

        var result = await _service.GetTemplatesAsync();

        Assert.Empty(result);
    }

    [Fact]
    public async Task GetTemplatesAsync_ParsesTemplate()
    {
        CreateTemplate(
            "static-value",
            """
            {
              "id": "static-value",
              "name": "Static value",
              "description": "Return a fixed value.",
              "setup_guide": "Paste into Server Code.",
              "file": "code.csx"
            }
            """,
            codeContent: "return 28;");

        var result = await _service.GetTemplatesAsync();

        var item = Assert.Single(result);
        Assert.Equal("static-value", item.Id);
        Assert.Equal("Static value", item.Name);
        Assert.Equal("Paste into Server Code.", item.SetupGuide);
        Assert.Equal("return 28;", item.Code);
    }

    [Fact]
    public async Task GetTemplatesAsync_SortsTemplates_ByName()
    {
        CreateTemplate(
            "z-template",
            """{ "id": "z-template", "name": "Z Template", "file": "code.csx" }""");

        CreateTemplate(
            "a-template",
            """{ "id": "a-template", "name": "A Template", "file": "code.csx" }""");

        var result = await _service.GetTemplatesAsync();

        Assert.Equal(2, result.Count);
        Assert.Equal("A Template", result[0].Name);
        Assert.Equal("Z Template", result[1].Name);
    }

    [Fact]
    public async Task GetTemplatesAsync_SkipsFolder_WithMissingMetaJson()
    {
        Directory.CreateDirectory(Path.Combine(_tempDir, "no-meta"));

        var result = await _service.GetTemplatesAsync();

        Assert.Empty(result);
    }

    [Fact]
    public async Task GetTemplatesAsync_SkipsTemplate_WithMalformedMetaJson()
    {
        CreateTemplate("broken", "{ not valid json", codeFileName: null);

        var result = await _service.GetTemplatesAsync();

        Assert.Empty(result);
    }

    [Fact]
    public async Task GetTemplatesAsync_SkipsTemplate_WithMissingCodeFile()
    {
        CreateTemplate(
            "missing-code",
            """{ "id": "missing-code", "name": "Missing Code", "file": "code.csx" }""",
            codeFileName: null);

        var result = await _service.GetTemplatesAsync();

        Assert.Empty(result);
    }
}
