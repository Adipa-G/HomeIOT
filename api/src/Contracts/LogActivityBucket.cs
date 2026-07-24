using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record LogActivityBucket(
    [property: JsonPropertyName("bucket_start_utc")] string BucketStartUtc,
    [property: JsonPropertyName("bucket_end_utc")] string BucketEndUtc,
    [property: JsonPropertyName("info_count")] int InfoCount,
    [property: JsonPropertyName("warn_count")] int WarnCount,
    [property: JsonPropertyName("error_count")] int ErrorCount,
    [property: JsonPropertyName("debug_count")] int DebugCount,
    [property: JsonPropertyName("other_count")] int OtherCount);
