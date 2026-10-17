using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

/// <summary>
/// One plotted slot of a chart. Holds a single sample (count 1, start equals end) or the
/// aggregate of every sample within a time bucket. Empty buckets have count 0 and null values.
/// </summary>
public sealed record ChartSeriesPoint(
    [property: JsonPropertyName("start_utc")] string StartUtc,
    [property: JsonPropertyName("end_utc")] string EndUtc,
    [property: JsonPropertyName("avg")] double? Avg,
    [property: JsonPropertyName("min")] double? Min,
    [property: JsonPropertyName("max")] double? Max,
    [property: JsonPropertyName("count")] int Count);
