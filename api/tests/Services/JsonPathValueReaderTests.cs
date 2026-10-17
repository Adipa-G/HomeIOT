using System.Text.Json;
using HomeIOT.Api.Services;
using Xunit;

namespace HomeIOT.Api.Tests.Services;

public sealed class JsonPathValueReaderTests
{
    private static (bool Ok, double Value) Read(string json, string path)
    {
        using var doc = JsonDocument.Parse(json);
        var ok = JsonPathValueReader.TryReadNumber(doc.RootElement, path, out var value);
        return (ok, value);
    }

    [Theory]
    [InlineData("{\"v\":21.5}", "v", 21.5)]
    [InlineData("{\"a\":{\"b\":{\"c\":-3}}}", "a.b.c", -3)]
    [InlineData("{\"v\":\"42.25\"}", "v", 42.25)]
    [InlineData("{\"items\":[10,20,30]}", "items.1", 20)]
    [InlineData("{\"items\":[{\"t\":5}]}", "items.0.t", 5)]
    public void TryReadNumber_ResolvesNumericValues(string json, string path, double expected)
    {
        var (ok, value) = Read(json, path);

        Assert.True(ok);
        Assert.Equal(expected, value);
    }

    [Theory]
    [InlineData("{\"v\":\"abc\"}", "v")]
    [InlineData("{\"v\":null}", "v")]
    [InlineData("{\"v\":true}", "v")]
    [InlineData("{\"v\":{\"x\":1}}", "v")]
    [InlineData("{\"v\":1}", "missing")]
    [InlineData("{\"v\":1}", "v.deeper")]
    [InlineData("{\"items\":[1]}", "items.5")]
    [InlineData("{\"items\":[1]}", "items.x")]
    [InlineData("{\"v\":1}", "")]
    [InlineData("{\"v\":\"NaN\"}", "v")]
    public void TryReadNumber_ReturnsFalse_ForMissingOrNonNumericValues(string json, string path)
    {
        Assert.False(Read(json, path).Ok);
    }
}
