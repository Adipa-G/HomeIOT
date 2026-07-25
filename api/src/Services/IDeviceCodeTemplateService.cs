using HomeIOT.Api.Contracts;

namespace HomeIOT.Api.Services;

public interface IDeviceCodeTemplateService
{
    Task<List<DeviceCodeTemplateItem>> GetTemplatesAsync(CancellationToken ct = default);
}
