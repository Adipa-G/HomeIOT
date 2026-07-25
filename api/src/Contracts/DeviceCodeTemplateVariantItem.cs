using System.Text.Json.Serialization;

namespace HomeIOT.Api.Contracts;

public sealed record DeviceCodeTemplateVariantItem(
    [property: JsonPropertyName("platform")] string Platform,
    [property: JsonPropertyName("code")] string Code);
