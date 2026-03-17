using HomeIOT.Api.Data.Entities;

namespace HomeIOT.Api.Infrastructure;

public sealed record DeviceRequestContext(string DeviceId, string ApiKey, DeviceRecord? Device);
