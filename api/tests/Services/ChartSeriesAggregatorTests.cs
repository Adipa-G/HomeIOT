using HomeIOT.Api.Services;
using HomeIOT.Api.Services.Models;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public sealed class ChartSeriesAggregatorTests
{
    private static readonly DateTimeOffset T0 = new(2026, 5, 10, 0, 0, 0, TimeSpan.Zero);

    private static List<ChartSample> Minutely(params double[] values) =>
        values.Select((v, i) => new ChartSample(T0.AddMinutes(i), v)).ToList();

    [Fact]
    public void Aggregate_Empty_ReturnsEmpty()
    {
        Assert.Empty(ChartSeriesAggregator.Aggregate([]));
    }

    [Fact]
    public void Aggregate_FewerSamplesThanBuckets_ReturnsOnePointPerSample()
    {
        var points = ChartSeriesAggregator.Aggregate(Minutely(1, 2, 3), maxBuckets: 5);

        Assert.Equal(new double?[] { 1, 2, 3 }, points.Select(p => p.Avg));
        Assert.All(points, p =>
        {
            Assert.Equal(1, p.Count);
            Assert.Equal(p.Avg, p.Min);
            Assert.Equal(p.Avg, p.Max);
            Assert.Equal(p.StartUtc, p.EndUtc);
        });
        Assert.Equal("2026-05-10T00:00:00Z", points[0].StartUtc);
    }

    [Fact]
    public void Aggregate_MoreSamplesThanBuckets_AveragesIntoEqualTimeBuckets()
    {
        // 9 samples over 8 minutes into 4 buckets of 2 minutes; the final sample lands in the last bucket.
        var points = ChartSeriesAggregator.Aggregate(Minutely(1, 3, 5, 7, 9, 11, 13, 15, 17), maxBuckets: 4);

        Assert.Equal(4, points.Count);
        Assert.Equal(new[] { 2, 2, 2, 3 }, points.Select(p => p.Count));
        Assert.Equal(new double?[] { 2, 6, 10, 15 }, points.Select(p => p.Avg));
        Assert.Equal(new double?[] { 1, 5, 9, 13 }, points.Select(p => p.Min));
        Assert.Equal(new double?[] { 3, 7, 11, 17 }, points.Select(p => p.Max));
        Assert.Equal("2026-05-10T00:00:00Z", points[0].StartUtc);
        Assert.Equal("2026-05-10T00:02:00Z", points[0].EndUtc);
        Assert.Equal("2026-05-10T00:08:00Z", points[^1].EndUtc);
    }

    [Fact]
    public void Aggregate_KeepsEmptyBucketsForGaps()
    {
        var samples = new List<ChartSample>
        {
            new(T0, 1),
            new(T0.AddMinutes(1), 2),
            new(T0.AddMinutes(9), 3),
            new(T0.AddMinutes(10), 4),
        };

        var points = ChartSeriesAggregator.Aggregate(samples, maxBuckets: 3);

        Assert.Equal(new[] { 2, 0, 2 }, points.Select(p => p.Count));
        Assert.Null(points[1].Avg);
        Assert.Null(points[1].Min);
        Assert.Null(points[1].Max);
    }

    [Fact]
    public void Aggregate_AllSamplesAtSameInstant_ReturnsSingleBucket()
    {
        var samples = Enumerable.Range(0, 5).Select(i => new ChartSample(T0, i)).ToList();

        var point = Assert.Single(ChartSeriesAggregator.Aggregate(samples, maxBuckets: 2));

        Assert.Equal(5, point.Count);
        Assert.Equal(2, point.Avg);
    }

    [Fact]
    public void Aggregate_DayOfMinutelySamples_FitsMaxBuckets()
    {
        var samples = Minutely(Enumerable.Range(0, 1440).Select(i => (double)i).ToArray());

        var points = ChartSeriesAggregator.Aggregate(samples);

        Assert.Equal(ChartSeriesAggregator.MaxBuckets, points.Count);
        Assert.Equal(1440, points.Sum(p => p.Count));
        Assert.All(points, p => Assert.True(p.Count > 0));
    }
}
