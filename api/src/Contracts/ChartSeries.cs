using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record ChartSeries(
    [property: JsonPropertyName("visualization_id")] Guid VisualizationId,
    [property: JsonPropertyName("points")] List<ChartSeriesPoint> Points);
