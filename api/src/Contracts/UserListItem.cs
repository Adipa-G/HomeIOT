using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record UserListItem(
    [property: JsonPropertyName("id")] int Id,
    [property: JsonPropertyName("username")] string Username,
    [property: JsonPropertyName("created_at_utc")] string CreatedAtUtc);
