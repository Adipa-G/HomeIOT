using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record PaginatedResponse<T>(
    [property: JsonPropertyName("items")] List<T> Items,
    [property: JsonPropertyName("total")] int Total,
    [property: JsonPropertyName("offset")] int Offset,
    [property: JsonPropertyName("limit")] int Limit);
