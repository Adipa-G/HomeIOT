// Fetch a value from a remote API and return it, with a safe fallback.
var client = new HttpClient();
try
{
    var json = await client.GetStringAsync("https://api.example.com/device-config?device_id=kitchen-01");
    var doc = JsonDocument.Parse(json);
    var threshold = doc.RootElement.GetProperty("temp_threshold").GetDouble();
    return threshold;
}
catch
{
    return 25.0; // fallback
}
finally
{
    client.Dispose();
}
