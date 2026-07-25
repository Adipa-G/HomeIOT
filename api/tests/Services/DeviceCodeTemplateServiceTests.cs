using HomeIOT.Api.Configuration;
using HomeIOT.Api.Services;
using Microsoft.AspNetCore.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Moq;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public class DeviceCodeTemplateServiceTests : IDisposable
{
    private readonly string _tempDir;
    private readonly DeviceCodeTemplateService _service;

    public DeviceCodeTemplateServiceTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), $"device_code_template_test_{Guid.NewGuid():N}");
        Directory.CreateDirectory(_tempDir);

        var templateOptions = new Mock<IOptions<DeviceCodeTemplateOptions>>();
        templateOptions.Setup(x => x.Value).Returns(new DeviceCodeTemplateOptions { TemplatesRoot = _tempDir });

        var env = new Mock<IWebHostEnvironment>();
        env.Setup(x => x.ContentRootPath).Returns(_tempDir);

        var logger = new Mock<ILogger<DeviceCodeTemplateService>>();

        _service = new DeviceCodeTemplateService(templateOptions.Object, env.Object, logger.Object);
    }

    public void Dispose()
    {
        if (Directory.Exists(_tempDir))
            Directory.Delete(_tempDir, true);
    }

    private void CreateTemplate(string id, string metaJson, Dictionary<string, string> codeFiles)
    {
        var dir = Path.Combine(_tempDir, id);
        Directory.CreateDirectory(dir);
        File.WriteAllText(Path.Combine(dir, "meta.json"), metaJson);
        foreach (var (fileName, content) in codeFiles)
            File.WriteAllText(Path.Combine(dir, fileName), content);
    }

    [Fact]
    public async Task GetTemplatesAsync_ReturnsEmptyList_WhenTemplatesDirMissing()
    {
        Directory.Delete(_tempDir, true);

        var result = await _service.GetTemplatesAsync();

        Assert.Empty(result);
    }

    [Fact]
    public async Task GetTemplatesAsync_ParsesTemplate_WithVariants()
    {
        CreateTemplate(
            "read-digital-pin",
            """
            {
              "id": "read-digital-pin",
              "name": "Read a digital pin",
              "description": "Read a button or switch.",
              "setup_guide": "Add a variable named value.",
              "variants": [
                { "platform": "esp32", "file": "esp32.py" },
                { "platform": "pico", "file": "pico.py" }
              ]
            }
            """,
            new Dictionary<string, string>
            {
                ["esp32.py"] = "print('esp32')",
                ["pico.py"] = "print('pico')",
            });

        var result = await _service.GetTemplatesAsync();

        var item = Assert.Single(result);
        Assert.Equal("read-digital-pin", item.Id);
        Assert.Equal("Read a digital pin", item.Name);
        Assert.Equal("Add a variable named value.", item.SetupGuide);
        Assert.Equal(2, item.Variants.Count);
        Assert.Contains(item.Variants, v => v.Platform == "esp32" && v.Code == "print('esp32')");
        Assert.Contains(item.Variants, v => v.Platform == "pico" && v.Code == "print('pico')");
    }

    [Fact]
    public async Task GetTemplatesAsync_SortsTemplates_ByName()
    {
        CreateTemplate(
            "z-template",
            """{ "id": "z-template", "name": "Z Template", "variants": [{ "platform": "generic", "file": "generic.py" }] }""",
            new Dictionary<string, string> { ["generic.py"] = "pass" });

        CreateTemplate(
            "a-template",
            """{ "id": "a-template", "name": "A Template", "variants": [{ "platform": "generic", "file": "generic.py" }] }""",
            new Dictionary<string, string> { ["generic.py"] = "pass" });

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
        CreateTemplate("broken", "{ not valid json", new Dictionary<string, string>());

        var result = await _service.GetTemplatesAsync();

        Assert.Empty(result);
    }

    [Fact]
    public async Task GetTemplatesAsync_SkipsVariant_WithMissingCodeFile()
    {
        CreateTemplate(
            "missing-code",
            """{ "id": "missing-code", "name": "Missing Code", "variants": [{ "platform": "esp32", "file": "esp32.py" }] }""",
            new Dictionary<string, string>());

        var result = await _service.GetTemplatesAsync();

        Assert.Empty(result);
    }
}
