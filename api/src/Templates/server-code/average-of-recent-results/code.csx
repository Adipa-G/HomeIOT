// Average a numeric field across this module's recent results.
// Change FIELD_NAME to match a field in your module's output.
var FIELD_NAME = "temp_celsius";
var from = DateTimeOffset.UtcNow.AddHours(-1);
var to = DateTimeOffset.UtcNow;

try
{
    var results = await Data.QueryResultsAsync(ModuleId, from, to);
    var values = new List<double>();
    foreach (var r in results)
    {
        if (r.Output is not null && r.Output.RootElement.TryGetProperty(FIELD_NAME, out var value))
        {
            values.Add(value.GetDouble());
        }
    }

    if (values.Count > 0)
    {
        return values.Average();
    }
}
catch
{
    // fall through to default
}

return 0.0; // fallback
