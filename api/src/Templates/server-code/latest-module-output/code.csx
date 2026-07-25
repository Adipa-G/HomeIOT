// Read a field from the latest result of another module on this device.
// Change SOURCE_MODULE_ID and FIELD_NAME to match your setup.
var SOURCE_MODULE_ID = "sensor-2";
var FIELD_NAME = "temp_celsius";

try
{
    var latest = await Data.GetLatestResultAsync(SOURCE_MODULE_ID);
    if (latest?.Output is not null && latest.Output.RootElement.TryGetProperty(FIELD_NAME, out var value))
    {
        return value.GetDouble();
    }
}
catch
{
    // fall through to default
}

return 0.0; // fallback
