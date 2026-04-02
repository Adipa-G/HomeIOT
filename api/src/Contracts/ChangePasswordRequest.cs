using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class ChangePasswordRequest
{
    [JsonPropertyName("new_password")]
    public string? NewPassword { get; set; }
}
