namespace HomeIOT.Api.Contracts;

public sealed record AdminLoginResponse(string Token, DateTimeOffset ExpiresAt);
