# Dev Commands Guide

Dev Commands let you execute arbitrary Python code on devices in real-time for testing, debugging, and remote administration.

---

## What Are Dev Commands?

Dev Commands are:
- **Interactive** — Execute code, see results immediately
- **Non-persistent** — Code runs in-memory, not stored on device
- **Live debugging** — Test device state, sensors, connectivity
- **Privileged** — Admin-only (requires authentication)
- **Fast** — Device fetches and executes within seconds

### Use Cases

- **Test module logic** before assigning to production devices
- **Debug device issues** — Check WiFi, memory, sensors
- **Remote administration** — Restart device, change config
- **Sensor validation** — Verify sensor readings
- **Network troubleshooting** — Test API connectivity

---

## Prerequisites: Switch to Development Mode

⚠️ **IMPORTANT:** Before using dev commands, the device **must be in development mode**.

### Enable Development Mode

1. Navigate to **Admin → Devices**
2. Click target device
3. Click **Switch Mode** button
4. Select `development`
5. Device applies mode change at next heartbeat (~60 seconds)

**Why?** Development mode enables:
- Faster dev command polling (2-second intervals)
- Debug-level logging
- Reduced power optimization (allows real-time debugging)
- Extended timeouts for long-running commands

**What happens if you try dev commands in production mode?**
- Commands are still queued, but device checks less frequently (slower)
- You may experience longer delays between queue and execution
- Some debugging operations may timeout

### Verify Device is in Development Mode

Once switched, verify in the Devices list:
- Device detail page should show **Mode: `development`**
- Last heartbeat timestamp should be recent (confirms mode change applied)

---

## Queuing a Dev Command

Navigate to **Admin → Dev Commands** then click **Create Command**.

### Steps

1. **Select Device** — Choose target device from dropdown
2. **Write Python Code** — Enter code in editor
3. **Queue Command** — Click **Queue** button
4. **Wait for Execution** — Device fetches and runs code

### Code Editor

The editor provides:
- Python syntax highlighting
- Line numbers
- Auto-indent
- Clear/reset button

### Examples

**Simple Print**
```python
print("Hello from device!")
```

**Check WiFi Connection**
```python
import network
sta = network.WLAN(0)
print("WiFi Connected:", sta.isconnected())
print("IP Address:", sta.ifconfig())
```

**Read Free Memory**
```python
import gc
gc.collect()
free_mem = gc.mem_free()
print(f"Free memory: {free_mem} bytes")
```

**Test API Connectivity**
```python
import socket
try:
    s = socket.socket()
    s.settimeout(5)
    s.connect(('192.168.1.100', 5228))
    print("✓ Connected to API server")
    s.close()
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

**Access Device Configuration**
```python
import json
try:
    with open('config.json') as f:
        config = json.load(f)
    print("Device ID:", config.get('device_id'))
    print("API URL:", config.get('api_url'))
except Exception as e:
    print(f"Error reading config: {e}")
```

**Check Sensor Reading**
```python
import dht
import machine
import json

try:
    sensor = dht.DHT22(machine.Pin(4))
    sensor.measure()
    result = {
        "temperature": sensor.temperature(),
        "humidity": sensor.humidity()
    }
    print(json.dumps(result))
except Exception as e:
    print(f"Sensor error: {e}")
```

---

## Execution Timeline

When you queue a dev command:

| Time | Event |
|------|-------|
| **T+0s** | Command queued on server, status: `pending` |
| **T+0-2s** | Device polls for pending commands (default: every 2 seconds) |
| **T+2-5s** | Device fetches code and executes |
| **T+5-10s** | Device uploads result to server |
| **T+10s+** | Result available in web UI, status: `completed` |

**Total latency:** Usually 5-10 seconds from queue to result.

---

## Viewing Results

### Command Status

Navigate to **Admin → Dev Commands** to see list of all commands:

| Column | Description |
|--------|-------------|
| **Device** | Target device |
| **Status** | `pending`, `executing`, `completed`, `failed` |
| **Queued At** | When you created command |
| **Completed At** | When execution finished |

### View Result Details

Click on any command to see:

| Field | Description |
|-------|-------------|
| **Code** | Code that was executed |
| **Status** | Final status |
| **Output** | stdout from execution |
| **Errors** | stderr / exceptions (if failed) |
| **Exit Code** | Process exit code (0 = success) |
| **Duration** | Execution time in milliseconds |

### Understanding Output

**Successful execution (status: `completed`):**
```
Output:
WiFi Connected: True
IP Address: ('192.168.1.50', '255.255.255.0', '192.168.1.1', '8.8.8.8')
```

**Failed execution (status: `failed`):**
```
Output: (empty)
Errors:
Traceback (most recent call last):
  File "<string>", line 2, in <module>
  File "sensor.py", line 10, in measure
ValueError: Sensor not responding
```

---

## Debugging Workflows

### Check Device Connectivity

```python
# Test WiFi
import network
sta = network.WLAN(0)
print("WiFi:", "Connected" if sta.isconnected() else "Disconnected")

# Test API server
import socket
s = socket.socket()
s.settimeout(5)
try:
    s.connect(('192.168.1.100', 5228))
    print("API Server: Reachable")
    s.close()
except:
    print("API Server: NOT reachable")
```

### Monitor Device Memory

```python
import gc
gc.collect()
total = gc.mem_alloc() + gc.mem_free()
free_pct = (gc.mem_free() / total) * 100
print(f"Memory: {free_pct:.1f}% free")
print(f"  Allocated: {gc.mem_alloc()} bytes")
print(f"  Free: {gc.mem_free()} bytes")
```

### Test Module Logic

Before assigning a module:

```python
# Copy module code here and test
import json
import random

# Simulate sensor
temperature = 22.5 + random.uniform(-0.5, 0.5)

result = {
    "sensor_id": "temp_01",
    "temperature_celsius": temperature,
    "status": "ok"
}

print(json.dumps(result))
```

### Inspect Device Configuration

```python
import json

with open('config.json') as f:
    config = json.load(f)

print("Device Configuration:")
for key, value in config.items():
    # Don't print secrets
    if 'password' in key or 'key' in key:
        print(f"  {key}: [redacted]")
    else:
        print(f"  {key}: {value}")
```

### Restart Device (Soft Reset)

```python
import machine
print("Restarting...")
machine.reset()
```

---

## Restrictions & Limitations

### What You CAN Do

✅ Read configuration files
✅ Access GPIO pins
✅ Test network connectivity
✅ Read sensor values
✅ Print diagnostics
✅ Call functions
✅ Import stdlib modules

### What You CAN'T Do

❌ Install pip packages (not available)
❌ Access external files (sandboxed)
❌ Call exec() or eval() (security)
❌ Access other devices (isolated)
❌ Permanently change device code (non-persistent)

### Code Timeout

- Maximum execution time: **30 seconds**
- If code runs longer, device terminates execution
- Use timeouts on network calls: `socket.settimeout(5)`

### Error Handling

Always wrap risky code in try-catch:

```python
try:
    # Your code here
    sensor = dht.DHT22(machine.Pin(4))
    sensor.measure()
except Exception as e:
    print(f"Error: {e}")
```

---

## Common Tasks

### Check Device Uptime

```python
import machine
rtc = machine.RTC()
uptime_ms = machine.ticks_ms()
uptime_hours = uptime_ms / (1000 * 60 * 60)
print(f"Uptime: {uptime_hours:.1f} hours")
```

### List Available Modules

```python
import sys
print("Available modules:")
for module in sys.modules:
    print(f"  {module}")
```

### Get Device MAC Address

```python
import network
sta = network.WLAN(0)
mac = sta.config('mac')
print("MAC Address:", ':'.join(f'{b:02x}' for b in mac))
```

### Test Hardware Pin

```python
import machine

# Test GPIO pin 5
pin = machine.Pin(5, machine.Pin.OUT)
print("Pin 5 - Setting HIGH")
pin.on()
print("Pin 5 - Setting LOW")
pin.off()
print("Pin 5 test complete")
```

### Benchmark Performance

```python
import time

# Time a loop
start = time.ticks_ms()
for i in range(10000):
    _ = i * 2
duration = time.ticks_ms() - start

print(f"10000 iterations: {duration}ms")
```

---

## Troubleshooting

### Command Stuck in "Pending"

- Device is offline or not fetching commands
- Check device last heartbeat (in Device list)
- Restart device

### Execution Timeout

- Code ran longer than 30 seconds
- Add socket timeouts: `s.settimeout(5)`
- Simplify code, break into smaller steps

### ImportError: Module Not Found

- Module not available in MicroPython runtime
- Check [MicroPython documentation](https://docs.micropython.org/) for available modules
- Use stdlib alternatives

### Output is Empty

- Code executed but didn't print anything
- Add `print()` statements
- Check for exceptions (view Errors tab)

---

## Best Practices

✅ **DO:**
- Test code in dev environment first
- Add error handling (`try/except`)
- Use socket timeouts for network calls
- Check device is online before queueing
- Use meaningful output (structured format preferred)

❌ **DON'T:**
- Run infinite loops (will hang device)
- Queue to offline devices (command ignored)
- Print binary data
- Rely on persistent state changes (non-persistent)
- Execute heavy computations repeatedly

---

## Next Steps

- [📖 Assign modules for regular execution](features-modules.md)
- [📖 Monitor device activity](features-devices.md)
- [📖 Check system health](features-dashboard.md)
