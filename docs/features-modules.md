# Module System Guide

Modules are reusable Python programs that run on edge devices. The module system lets you create, version, assign, and monitor remote code execution.

---

## Overview

### What Are Modules?

Modules are:
- **Python scripts** executed on devices
- **Versioned** — Multiple versions can coexist
- **Reusable** — Assign same module to many devices
- **Remotely manageable** — Create and assign from web UI
- **Monitored** — View execution results and failures

### Module Lifecycle

1. **Create Module** — Define metadata (name, description, category)
2. **Upload Version** — Upload Python code for a specific version
3. **Assign to Device(s)** — Select which devices run which version
4. **Device Downloads** — Device polls and fetches assigned module
5. **Device Executes** — Module runs on device
6. **Results Reported** — Device uploads results (output, status, errors)
7. **Admin Reviews** — View results in web UI

---

## Creating a Module

Navigate to **Admin → Modules** then click **Create Module**.

### Module Metadata

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | Module identifier | `temperature-reader` |
| **Description** | Purpose of module | `Reads temperature sensor and uploads data` |
| **Category** | Functional category | `sensor-data`, `control`, `monitoring` |

### Uploading Your First Version

After creating the module, upload Python code:

1. Click **Upload Version**
2. Specify **Version** number (semantic: `1.0.0`, `1.0.1`, etc.)
3. Upload `.py` file

### Module Code Structure

Modules follow a standard pattern with a `run(ctx)` function:

```python
def run(ctx):
    """
    Module entry point. Executed by the device.
    
    Args:
        ctx: Execution context (reserved for future use)
    
    Returns:
        dict: Result object to be serialized and reported
    """
    # Your module logic here
    import esp32
    
    raw_temp = esp32.raw_temperature()
    temp_celsius = (raw_temp - 32) * 5 / 9
    
    return {
        "raw_value": raw_temp,
        "temp_celsius": round(temp_celsius, 1),
        "status": "ok"
    }
```

**Requirements:**
- Must define a `run(ctx)` function (entry point)
- Function must return a `dict` (will be serialized to JSON)
- No external dependencies beyond Python stdlib (MicroPython)
- No infinite loops or blocking operations
- Handle errors gracefully (use try-catch)
- No network calls without timeout: `socket.settimeout(5)`

**Execution Environment:**
- MicroPython runtime (not CPython)
- Access to device modules: `machine`, `esp32`, `dht`, `json`, `socket`, `network`, etc.
- Limited memory (typical device has 4-8 MB)
- Device injected variables available directly (see Module Variables section below)

---

## Module Variables

Module Variables allow you to parameterize module behavior without redeploying code. Variables can be:
- **Static values** — Hard-coded strings, numbers, booleans
- **Dynamically computed** — Calculated using C# code (HTTP requests, database queries, etc.)

Variables are injected into the module's execution context and accessible by name.

### Using Variables in Modules

Variables appear as global names in your module code:

```python
def run(ctx):
    """Example module using injected variables."""
    import esp32
    
    raw_temp = esp32.raw_temperature()
    temp_celsius = (raw_temp - 32) * 5 / 9
    
    # Injected by your module-variable infrastructure.
    # Fallback keeps module running even if variable is missing or invalid.
    threshold = 28.0
    try:
        threshold = float(TEMP_THRESHOLD)
    except Exception:
        pass
    
    is_excess = temp_celsius > threshold
    
    return {
        "raw_value": raw_temp,
        "temp_celsius": round(temp_celsius, 1),
        "temp_threshold": threshold,
        "exceeds_threshold": is_excess,
        "location": LOCATION  # Another injected variable
    }
```

**Key Points:**
- Variables are injected into the global namespace (e.g., `TEMP_THRESHOLD`, `LOCATION`)
- Always use try-catch around variable access (in case variable is missing)
- Provide sensible fallback defaults
- If variable fails to parse, module continues with fallback value

### Defining Module Variables

Navigate to **Admin → Modules → [Module Name] → Variables** to define variables for a module.

#### Variable Properties

| Property | Description | Example |
|----------|-------------|---------|
| **Name** | Variable name (appears as global in code) | `TEMP_THRESHOLD`, `API_URL`, `RETRY_COUNT` |
| **Type** | Data type: `string`, `number`, `boolean` | `number` |
| **Value Type** | How value is computed: `static` or `expression` | `static` or `expression` |
| **Value** | Static value or C# expression | `28.0` or `await GetThresholdAsync()` |
| **Description** | Human-readable purpose | `"Temperature threshold for alarm trigger"` |

#### Static Variables

**Example: Hard-coded threshold**

| Name | Type | Value Type | Value |
|------|------|-----------|-------|
| `TEMP_THRESHOLD` | number | static | `28.0` |
| `LOCATION` | string | static | `"kitchen"` |
| `ENABLE_LOGGING` | boolean | static | `true` |

In module code:
```python
def run(ctx):
    threshold = float(TEMP_THRESHOLD)  # 28.0
    location = LOCATION                 # "kitchen"
    if ENABLE_LOGGING:
        # Log something
        pass
    return {"threshold": threshold, "location": location}
```

#### Dynamic Variables (C# Expressions)

**Example: Fetch threshold from web service**

| Name | Type | Value Type | Value (C# Expression) |
|------|------|-----------|--------|
| `TEMP_THRESHOLD` | number | expression | `await FetchThresholdFromWebAsync()` |

C# Expression:
```csharp
using System.Net.Http;
using System.Threading.Tasks;

var client = new HttpClient();
try
{
    var response = await client.GetStringAsync("https://config.example.com/temp-threshold");
    if (double.TryParse(response, out var value))
    {
        return value;
    }
    return 28.0; // fallback
}
catch
{
    return 28.0; // fallback on error
}
finally
{
    client.Dispose();
}
```

The expression is evaluated on the **server** when the module is assigned or every time it runs (depending on evaluation schedule).

### Common Variable Patterns

#### Configuration from Web Service

```csharp
// Fetch device config from remote API
using System.Net.Http;
using System.Text.Json;

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
```

#### Database Lookup

```csharp
// Fetch setting from database
using System.Data.SqlClient;

using (var conn = new SqlConnection("connection_string"))
{
    conn.Open();
    using (var cmd = new SqlCommand("SELECT threshold FROM settings WHERE device_id='kitchen-01'", conn))
    {
        var result = cmd.ExecuteScalar();
        if (result != null && double.TryParse(result.ToString(), out var value))
        {
            return value;
        }
    }
}
return 25.0; // fallback
```

#### Calculated Value

```csharp
// Calculate threshold based on time of day
var hour = DateTime.Now.Hour;
if (hour >= 22 || hour < 6)  // Night time
{
    return 26.0;  // Lower threshold at night
}
else
{
    return 28.0;  // Normal threshold during day
}
```

#### Fetch from Public API

```csharp
// Get data from public API (e.g., weather, currency)
using System.Net.Http;
using System.Text.Json;

var client = new HttpClient();
try
{
    var json = await client.GetStringAsync("https://api.coindesk.com/v1/bpi/currentprice/BTC.json");
    var doc = JsonDocument.Parse(json);
    var rate = doc.RootElement
        .GetProperty("bpi")
        .GetProperty("USD")
        .GetProperty("rate")
        .GetString();
    return rate;
}
catch
{
    return "0"; // fallback
}
finally
{
    client.Dispose();
}
```

### Variable Evaluation & Caching

**How variables are evaluated:**

1. **On assignment** — Variables computed when module assigned to device
2. **On device poll** — Variables recomputed each time device fetches assignment (every 60s)
3. **Optional caching** — Results can be cached for performance (future feature)

**Implications:**

- **Static variables**: Computed once, reused across runs
- **Dynamic variables**: Re-evaluated frequently (can add server load)
- **Timeouts**: Expressions have max 10-second timeout (set as limit)
- **Failures**: If expression fails, module uses last known value or `null`

### Best Practices for Module Variables

✅ **DO:**
- Use sensible fallback values
- Keep expressions fast (< 2 seconds preferred)
- Cache external API responses on server side
- Describe variable purpose in description field
- Use snake_case for variable names (matches Python convention)
- Test expressions for error handling

❌ **DON'T:**
- Create infinite loops in expressions
- Call slow/unreliable APIs without timeout
- Forget to handle exceptions
- Use variables without try-catch in module code
- Store sensitive data (credentials, keys) in variables
- Define variables the device doesn't actually use

### Debugging Variable Issues

**Variable doesn't appear in module:**
1. Verify variable name matches exactly (case-sensitive)
2. Check variable is assigned to this module (not another)
3. Use dev commands to inspect module execution

**Variable has wrong value:**
1. Check expression result in admin UI (should show computed value)
2. Verify static value is correct
3. If dynamic: check external service is returning expected data
4. Review module logs for parsing errors

**Module fails with injected variable:**
```python
def run(ctx):
    try:
        # Try to use variable
        threshold = float(SOME_VAR)
    except NameError:
        # Variable not defined (not injected)
        threshold = 25.0
    except ValueError:
        # Variable value is not a valid number
        threshold = 25.0
    except Exception as e:
        # Other error
        threshold = 25.0
    
    return {"threshold": threshold}
```

---

## Pre-Built Module Examples

The system includes example modules:

**`temp-reader` (versions 1.0.0 - 1.0.4)**
```python
# Reads temperature sensor, returns JSON
import json
import dht
import machine

pin = machine.Pin(4)
sensor = dht.DHT22(pin)
sensor.measure()

result = {
    "temperature": sensor.temperature(),
    "humidity": sensor.humidity()
}

print(json.dumps(result))
```

**`server-web-request` (versions 1.0.0 - 1.0.1)**
```python
# Makes HTTP request to remote server
import socket
import json

url = "http://api.example.com/data"
response = request_handler.get(url)

print(json.dumps({"response": response}))
```

---

## Managing Modules

### View All Modules

Navigate to **Admin → Modules** to see:
- Module name and description
- Version count
- Assignment count (how many devices have this module)
- Last updated date

### View Module Detail

Click a module name to see:
- All versions uploaded
- Devices this module is assigned to
- Execution results for this module

### Upload New Version

1. Navigate to module detail
2. Click **Upload Version**
3. Specify new version number (e.g., `1.0.1` if current is `1.0.0`)
4. Upload `.py` file

**Note:** Versions are immutable. To fix a bug, upload a new version and reassign devices.

### Delete Module

⚠️ Can only delete if no devices have it assigned.

1. Remove all device assignments first
2. Then delete module

---

## Assigning Modules to Devices

Assign a module to run on one or more devices.

### Steps

1. Navigate to **Admin → Modules**
2. Click module name
3. Click **Assign** button
4. **Select Devices** — Check devices that should run this module
5. **Select Version** — Choose which version to deploy
6. **Click Assign**

### What Happens

1. Assignment is stored on server
2. Device polls for assignments every 60 seconds (default)
3. Device downloads module code at next poll
4. Device executes module
5. Device uploads results

### Timeline

- **T+0s** — You click "Assign"
- **T+0-60s** — Device downloads module (at next poll)
- **T+0-120s** — Module executes
- **T+0-130s** — Results appear in dashboard

### Multiple Devices

To assign same module to multiple devices:
1. Select all devices at once (use checkboxes)
2. Click **Assign**
3. All selected devices get the assignment

---

## Monitoring Module Execution

### View Results

Navigate to device detail → **Module Results** tab to see:

| Field | Description |
|-------|-------------|
| **Module Name** | Which module executed |
| **Version** | Version that ran |
| **Status** | `success` or `failed` |
| **Output** | stdout from module (or error message if failed) |
| **Timestamp** | When module executed |
| **Duration** | How long execution took (ms) |

### Success Vs. Failure

**Status: success**
- Module ran without errors
- Output captured in results

**Status: failed**
- Module threw exception
- Output shows error traceback

### Troubleshooting Failed Modules

1. **Check module output** — Error message usually indicates issue
2. **Test locally** — Try running module code locally first
3. **Use Dev Commands** — Execute test code on device to debug
4. **Reassign new version** — After fixing code, upload new version and reassign
5. **Check device logs** — May contain additional context (view in device → Logs tab)

---

## Module Assignment Patterns

### Single Device Testing

1. Create module with version `0.1.0`
2. Assign to one test device
3. View results
4. If working, assign to all devices
5. If failing, fix and upload version `0.1.1`

### Gradual Rollout

1. Assign version `1.0.0` to 5% of devices (test group)
2. Monitor for failures
3. If stable, assign to 25% of devices
4. Monitor again
5. If all good, assign to 100% of devices

### A/B Testing

1. Assign module version `1.0.0` to device group A
2. Assign module version `1.0.1` (with changes) to device group B
3. Compare results
4. Deploy winner to all devices

### Scheduled Updates

1. Currently all devices run version `1.0.0`
2. Upload new version `1.1.0`
3. Reassign devices to version `1.1.0`
4. All devices fetch new version at next poll
5. Version `1.1.0` executes across fleet

---

## Common Workflows

### Deploy a Temperature Reader

1. **Create module** named `temperature-reader` (category: `sensors`)
2. **Upload Python code** (version `1.0.0`):
   ```python
   import json
   import dht
   import machine
   
   sensor = dht.DHT22(machine.Pin(4))
   sensor.measure()
   
   print(json.dumps({
       "temperature": sensor.temperature(),
       "humidity": sensor.humidity()
   }))
   ```
3. **Assign to devices** — Select all ESP32 devices, version `1.0.0`
4. **Monitor results** — View in device → Module Results tab
5. **Fix if needed** — Upload version `1.0.1` with fixes, reassign

### Test Module Before Production

1. Create module version `1.0.0-beta`
2. Assign to 1 device (test device)
3. Execute and view results
4. If working, rename/create version `1.0.0`
5. Upload production version `1.0.0`
6. Assign to all devices

### Debug Module Issues

1. If module shows `status: failed`:
   - Check output for error message
   - Check device logs for related errors
2. Use **Dev Commands** to test components:
   - Test sensor reading
   - Test network connection
   - Test JSON serialization
3. Fix code locally
4. Upload new version
5. Reassign to device

---

## Module Results Persistence

- Results are stored indefinitely (until device is deleted)
- You can view historical results for any module
- Results help identify trends (e.g., sensor drift, repeated failures)

---

## Best Practices

✅ **DO:**
- Test modules locally first before uploading
- Use semantic versioning (`1.0.0`, `1.1.0`, `2.0.0`)
- Add error handling to module code
- Use `print(json.dumps(...))` for structured output
- Version incrementally (don't jump from `1.0.0` to `10.0.0`)

❌ **DON'T:**
- Upload untested code to production devices
- Use blocking loops in modules (will hang device)
- Print binary data (will corrupt output)
- Use pip packages (MicroPython has limited stdlib)
- Delete modules while devices are assigned (unassign first)

---

## Next Steps

- [📖 Debug modules with Dev Commands](features-dev-commands.md)
- [📖 Monitor device activity](features-devices.md)
- [📖 Check dashboard metrics](features-dashboard.md)
