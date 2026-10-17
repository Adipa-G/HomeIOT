using HomeIOT.Api.Infrastructure;
using Xunit;

namespace HomeIOT.Api.Tests.Infrastructure;

public class DeviceApiKeyHasherTests
{
    [Fact]
    public void GenerateKey_ReturnsUrlSafeUniqueKeys()
    {
        var first = DeviceApiKeyHasher.GenerateKey();
        var second = DeviceApiKeyHasher.GenerateKey();

        Assert.NotEqual(first, second);
        Assert.Equal(43, first.Length);
        Assert.Matches("^[A-Za-z0-9_-]+$", first);
    }

    [Fact]
    public void Hash_IsDeterministicAndPrefixed()
    {
        var hash = DeviceApiKeyHasher.Hash("abc");

        Assert.Equal(hash, DeviceApiKeyHasher.Hash("abc"));
        Assert.Equal("sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", hash);
        Assert.True(DeviceApiKeyHasher.IsHashed(hash));
        Assert.False(DeviceApiKeyHasher.IsHashed("abc"));
    }

    [Theory]
    [InlineData("key-1", true)]
    [InlineData("key-2", false)]
    [InlineData("", false)]
    public void Verify_HashedStoredValue(string presented, bool expected)
    {
        Assert.Equal(expected, DeviceApiKeyHasher.Verify(presented, DeviceApiKeyHasher.Hash("key-1")));
    }

    [Theory]
    [InlineData("legacy", true)]
    [InlineData("other", false)]
    public void Verify_LegacyPlaintextStoredValue(string presented, bool expected)
    {
        Assert.Equal(expected, DeviceApiKeyHasher.Verify(presented, "legacy"));
    }

    [Fact]
    public void Verify_EmptyStoredValue_ReturnsFalse()
    {
        Assert.False(DeviceApiKeyHasher.Verify("key", ""));
    }
}
