using System.Globalization;
using System.Text.Json;

namespace HomeIOT.Api.Services;

/// <summary>
/// Reads values from module output using the same dot-notation paths as the web UI
/// (e.g. <c>sensors.temp</c>, <c>readings.0</c>).
/// </summary>
public static class JsonPathValueReader
{
    /// <summary>
    /// Resolves <paramref name="path"/> and returns true when it points at a finite number or a
    /// numeric string.
    /// </summary>
    public static bool TryReadNumber(JsonElement root, string path, out double value)
    {
        value = 0;
        if (string.IsNullOrWhiteSpace(path)) return false;

        var current = root;
        foreach (var key in path.Split('.'))
        {
            if (current.ValueKind == JsonValueKind.Object)
            {
                if (!current.TryGetProperty(key, out current)) return false;
            }
            else if (current.ValueKind == JsonValueKind.Array
                && int.TryParse(key, NumberStyles.None, CultureInfo.InvariantCulture, out var index)
                && index < current.GetArrayLength())
            {
                current = current[index];
            }
            else
            {
                return false;
            }
        }

        var parsed = current.ValueKind switch
        {
            JsonValueKind.Number when current.TryGetDouble(out var d) => d,
            JsonValueKind.String when double.TryParse(current.GetString(), NumberStyles.Float, CultureInfo.InvariantCulture, out var s) => s,
            _ => double.NaN,
        };

        if (!double.IsFinite(parsed)) return false;
        value = parsed;
        return true;
    }
}
