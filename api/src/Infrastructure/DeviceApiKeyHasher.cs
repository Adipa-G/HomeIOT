using System.Buffers.Text;
using System.Security.Cryptography;
using System.Text;

namespace HomeIOT.Api.Infrastructure;

/// <summary>
/// Generates device API keys and stores them as SHA-256 hashes. Values without the
/// hash prefix are legacy plaintext keys that are upgraded on the next successful auth.
/// </summary>
public static class DeviceApiKeyHasher
{
    public const string HashPrefix = "sha256:";
    private const int KeySizeBytes = 32;

    public static string GenerateKey()
    {
        return Base64Url.EncodeToString(RandomNumberGenerator.GetBytes(KeySizeBytes));
    }

    public static string Hash(string apiKey)
    {
        var digest = SHA256.HashData(Encoding.UTF8.GetBytes(apiKey));
        return HashPrefix + Convert.ToHexString(digest).ToLowerInvariant();
    }

    public static bool IsHashed(string storedValue)
    {
        return storedValue.StartsWith(HashPrefix, StringComparison.Ordinal);
    }

    public static bool Verify(string presentedKey, string storedValue)
    {
        if (string.IsNullOrEmpty(presentedKey) || string.IsNullOrEmpty(storedValue))
        {
            return false;
        }

        var expected = IsHashed(storedValue) ? storedValue : Hash(storedValue);
        return CryptographicOperations.FixedTimeEquals(
            Encoding.ASCII.GetBytes(Hash(presentedKey)),
            Encoding.ASCII.GetBytes(expected));
    }
}
