using HomeIOT.Api.Contracts;

namespace HomeIOT.Api.Services;

public interface IModuleTemplateService
{
    Task<List<ModuleTemplateItem>> GetTemplatesAsync(CancellationToken ct = default);
}
