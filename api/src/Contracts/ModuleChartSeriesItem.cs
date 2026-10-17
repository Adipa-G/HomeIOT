using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ModuleChartSeriesItem(
    [property: JsonPropertyName("module_id")] string ModuleId,
    [property: JsonPropertyName("series")] List<ChartSeries> Series);
