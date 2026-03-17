namespace HomeIOT.Api.Infrastructure;

public static class HttpContextExtensions
{
    private const string DeviceContextKey = "HomeIOT.DeviceContext";

    public static void SetDeviceRequestContext(this HttpContext httpContext, DeviceRequestContext context)
    {
        httpContext.Items[DeviceContextKey] = context;
    }

    public static DeviceRequestContext? GetDeviceRequestContext(this HttpContext httpContext)
    {
        return httpContext.Items.TryGetValue(DeviceContextKey, out var value)
            ? value as DeviceRequestContext
            : null;
    }
}
