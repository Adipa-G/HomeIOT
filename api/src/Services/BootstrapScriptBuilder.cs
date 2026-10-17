using System.Reflection;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Serialization;
using HomeIOT.Api.Services.Models;

namespace HomeIOT.Api.Services;

/// <summary>
/// Generates the self-extracting first-boot main.py. The output is the loader from
/// edge/bootstrap/loader.py followed by a comment-encoded payload (provisioning JSON and
/// source files) that the loader unpacks on the device. Firmware modules are taken from
/// the latest OTA release so the installer always matches the firmware it installs.
/// </summary>
public sealed class BootstrapScriptBuilder : IBootstrapScriptBuilder
{
    public const string ProvisionMarker = "#@@PROVISION ";
    public const string FileMarker = "#@@FILE ";
    public const string LineMarker = "#|";
    public const string EndMarker = "#@@END";

    private const string ResourcePrefix = "bootstrap/";

    private static readonly JsonSerializerOptions ProvisionJsonOptions = new()
    {
        // Keeps non-ASCII characters readable; control characters (incl. newlines) are still escaped.
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    private readonly IOtaReleaseService _otaReleaseService;
    private readonly Lazy<BundleDocument> _bundle;

    public BootstrapScriptBuilder(IOtaReleaseService otaReleaseService)
    {
        _otaReleaseService = otaReleaseService;
        _bundle = new Lazy<BundleDocument>(LoadBundle);
    }

    public BootstrapScript? Build(BootstrapProvisioningData data)
    {
        var version = _otaReleaseService.GetLatestVersion(data.Platform);
        if (version is null)
        {
            return null;
        }

        var bundle = _bundle.Value;
        var builder = new StringBuilder();
        builder.Append(ReadResource(bundle.Loader).Replace("\r\n", "\n").TrimEnd('\n')).Append('\n');
        builder.Append('\n');
        builder.Append(ProvisionMarker).Append(SerializeProvision(data)).Append('\n');

        foreach (var path in bundle.BootstrapFiles)
        {
            AppendFile(builder, path, ReadResource(path));
        }

        foreach (var path in bundle.ReleaseFiles)
        {
            var content = _otaReleaseService.ReadReleaseFileText(data.Platform, version, path)
                ?? throw new InvalidOperationException(
                    $"Release {data.Platform}/{version} is missing '{path}' required by the bootstrap installer.");
            AppendFile(builder, path, content);
        }

        return new BootstrapScript(version, builder.ToString());
    }

    private static void AppendFile(StringBuilder builder, string path, string content)
    {
        builder.Append(FileMarker).Append(path).Append('\n');
        var lines = content.Replace("\r\n", "\n").Split('\n');
        var count = lines.Length > 0 && lines[^1].Length == 0 ? lines.Length - 1 : lines.Length;
        for (var i = 0; i < count; i++)
        {
            builder.Append(LineMarker).Append(lines[i].TrimEnd('\r')).Append('\n');
        }

        builder.Append(EndMarker).Append('\n');
    }

    private static string SerializeProvision(BootstrapProvisioningData data)
    {
        var payload = new Dictionary<string, string>
        {
            ["device_id"] = data.DeviceId,
            ["platform"] = data.Platform,
            ["api_url"] = data.ApiUrl,
            ["api_key"] = data.ApiKey,
            ["wifi_ssid"] = data.WifiSsid,
            ["wifi_password"] = data.WifiPassword,
        };
        return JsonSerializer.Serialize(payload, ProvisionJsonOptions);
    }

    private static BundleDocument LoadBundle()
    {
        var bundle = JsonSerializer.Deserialize<BundleDocument>(ReadResource("bundle.json"))
            ?? throw new InvalidOperationException("Bootstrap bundle.json is empty.");
        if (string.IsNullOrWhiteSpace(bundle.Loader) || bundle.ReleaseFiles.Count == 0)
        {
            throw new InvalidOperationException("Bootstrap bundle.json is incomplete.");
        }

        return bundle;
    }

    private static string ReadResource(string path)
    {
        var name = ResourcePrefix + Path.GetFileName(path);
        using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(name)
            ?? throw new InvalidOperationException($"Embedded bootstrap resource '{name}' not found.");
        using var reader = new StreamReader(stream, Encoding.UTF8);
        return reader.ReadToEnd();
    }

    private sealed class BundleDocument
    {
        [JsonPropertyName("loader")]
        public string Loader { get; set; } = string.Empty;

        [JsonPropertyName("bootstrap_files")]
        public List<string> BootstrapFiles { get; set; } = new();

        [JsonPropertyName("release_files")]
        public List<string> ReleaseFiles { get; set; } = new();
    }
}
