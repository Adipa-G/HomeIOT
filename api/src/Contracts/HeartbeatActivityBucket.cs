using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record HeartbeatActivityBucket(
    [property: JsonPropertyName("bucket_start_utc")] string BucketStartUtc,
    [property: JsonPropertyName("bucket_end_utc")] string BucketEndUtc,
    [property: JsonPropertyName("count")] int Count);
