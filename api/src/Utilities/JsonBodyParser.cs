using System.Text.Json;
using HomeIOT.Api.Contracts;

namespace HomeIOT.Api.Utilities;

public static class JsonBodyParser
{
    public static async Task<JsonElement?> ReadJsonBodyAsync(HttpContext httpContext, CancellationToken cancellationToken)
    {
        try
        {
            var body = await JsonDocument.ParseAsync(httpContext.Request.Body, cancellationToken: cancellationToken);
            return body.RootElement.Clone();
        }
        catch
        {
            return null;
        }
    }

    public static string? GetString(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString()
            : null;
    }

    public static long? GetInt64(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var value) && value.TryGetInt64(out var parsed)
            ? parsed
            : null;
    }

    public static int? GetInt32(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var value) && value.TryGetInt32(out var parsed)
            ? parsed
            : null;
    }

    public static bool? GetBoolean(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var value) && (value.ValueKind is JsonValueKind.True or JsonValueKind.False)
            ? value.GetBoolean()
            : null;
    }

    public static List<LogEntryRequest> GetLogEntries(JsonElement element)
    {
        if (!element.TryGetProperty("logs", out var logsElement) || logsElement.ValueKind != JsonValueKind.Array)
        {
            return new List<LogEntryRequest>();
        }

        var logs = new List<LogEntryRequest>();
        foreach (var item in logsElement.EnumerateArray())
        {
            logs.Add(new LogEntryRequest
            {
                Ts = GetInt64(item, "ts"),
                Level = GetString(item, "level"),
                Message = GetString(item, "message"),
                Context = item.TryGetProperty("context", out var contextElement) && contextElement.ValueKind == JsonValueKind.Object
                    ? JsonSerializer.Deserialize<Dictionary<string, object?>>(contextElement.GetRawText()) ?? new Dictionary<string, object?>()
                    : new Dictionary<string, object?>(),
            });
        }

        return logs;
    }
}
