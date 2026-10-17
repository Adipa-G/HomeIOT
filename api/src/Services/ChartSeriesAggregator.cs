using HomeIOT.Api.Contracts;
using HomeIOT.Api.Infrastructure;
using HomeIOT.Api.Services.Models;

namespace HomeIOT.Api.Services;

/// <summary>
/// Downsamples chart history so long ranges (e.g. 1440 one-minute runs) can be plotted
/// without shipping or drawing every sample.
/// </summary>
public static class ChartSeriesAggregator
{
    public const int MaxBuckets = 120;

    /// <summary>
    /// Returns one point per sample when they fit within <paramref name="maxBuckets"/>; otherwise
    /// splits the sampled time range into equal-width buckets carrying avg/min/max/count.
    /// Buckets without samples are kept (count 0) so the chart can render gaps.
    /// </summary>
    /// <param name="samples">Samples ordered oldest first.</param>
    /// <param name="maxBuckets">Maximum number of points to return.</param>
    public static List<ChartSeriesPoint> Aggregate(IReadOnlyList<ChartSample> samples, int maxBuckets = MaxBuckets)
    {
        if (samples.Count == 0) return [];
        maxBuckets = Math.Max(1, maxBuckets);

        if (samples.Count <= maxBuckets)
        {
            return samples
                .Select(s =>
                {
                    var at = EndpointValidation.ToUtcZ(s.At);
                    return new ChartSeriesPoint(at, at, s.Value, s.Value, s.Value, 1);
                })
                .ToList();
        }

        var start = samples[0].At;
        var spanTicks = (samples[^1].At - start).Ticks;
        if (spanTicks <= 0)
        {
            return [ToPoint(start, samples[^1].At, samples)];
        }

        var bucketCount = maxBuckets;
        var buckets = new List<ChartSample>[bucketCount];
        for (var i = 0; i < bucketCount; i++) buckets[i] = [];

        foreach (var sample in samples)
        {
            var offset = (sample.At - start).Ticks;
            var index = (int)Math.Clamp(offset * bucketCount / spanTicks, 0, bucketCount - 1);
            buckets[index].Add(sample);
        }

        var points = new List<ChartSeriesPoint>(bucketCount);
        for (var i = 0; i < bucketCount; i++)
        {
            var bucketStart = start.AddTicks(spanTicks * i / bucketCount);
            var bucketEnd = start.AddTicks(spanTicks * (i + 1) / bucketCount);
            points.Add(ToPoint(bucketStart, bucketEnd, buckets[i]));
        }

        return points;
    }

    private static ChartSeriesPoint ToPoint(DateTimeOffset start, DateTimeOffset end, IReadOnlyCollection<ChartSample> samples)
    {
        var startUtc = EndpointValidation.ToUtcZ(start);
        var endUtc = EndpointValidation.ToUtcZ(end);
        if (samples.Count == 0) return new ChartSeriesPoint(startUtc, endUtc, null, null, null, 0);

        return new ChartSeriesPoint(
            startUtc,
            endUtc,
            samples.Average(s => s.Value),
            samples.Min(s => s.Value),
            samples.Max(s => s.Value),
            samples.Count);
    }
}
