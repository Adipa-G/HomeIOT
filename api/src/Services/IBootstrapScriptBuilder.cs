using HomeIOT.Api.Services.Models;

namespace HomeIOT.Api.Services;

public interface IBootstrapScriptBuilder
{
    /// <summary>
    /// Builds a first-boot main.py for a device using the latest release of its platform.
    /// Returns null when no release exists; throws <see cref="InvalidOperationException"/>
    /// when the release is missing files the bootstrap needs.
    /// </summary>
    BootstrapScript? Build(BootstrapProvisioningData data);
}
