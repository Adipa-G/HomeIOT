using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed class SetVariableValueRequest
{
    [JsonPropertyName("value")]
    public string? Value { get; set; }
}
