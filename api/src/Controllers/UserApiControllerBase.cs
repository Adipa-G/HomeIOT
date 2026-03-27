using Microsoft.AspNetCore.Mvc;

namespace HomeIOT.Api.Controllers;

public abstract class UserApiControllerBase : ControllerBase
{
    protected static string ToUtcZ(DateTimeOffset value)
    {
        return Infrastructure.EndpointValidation.ToUtcZ(value);
    }
}
