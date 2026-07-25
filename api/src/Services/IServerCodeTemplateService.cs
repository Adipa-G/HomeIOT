using HomeIOT.Api.Contracts;

namespace HomeIOT.Api.Services;

public interface IServerCodeTemplateService
{
    Task<List<ServerCodeTemplateItem>> GetTemplatesAsync(CancellationToken ct = default);
}
