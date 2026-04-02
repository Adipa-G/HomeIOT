using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class CreateUserRequest
{
    [JsonPropertyName("username")]
    public string? Username { get; set; }

    [JsonPropertyName("password")]
    public string? Password { get; set; }
}
