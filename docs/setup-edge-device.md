# Edge Device Setup Guide

This guide walks you through provisioning and deploying firmware to an ESP32 or Raspberry Pi Pico device, or running a PC simulator for development.

## Prerequisites

- **Server running** — Verify at `http://localhost:5228` (see [Server Setup](setup-server.md))
- **Python 3.8+** — Required for provisioning and deployment tools
- **mpremote installed** — `pip install mpremote` (for real devices only)
- **Device connected via USB** — ESP32 or Raspberry Pi Pico (for real devices only)
- **WiFi credentials** — SSID and password for the device to connect (for real devices only)

---

## Alternative: Running a PC Simulator

If you don't have a physical device, you can run a simulator on your PC to test edge logic without hardware.

### Quick Start

1. **Install dependencies**
   ```bash
   pip install -r edge/shared/tests/requirements.txt
   ```
   The simulator's HTTP client uses the `requests` package (declared in this
   requirements file) since it runs as CPython rather than MicroPython.

2. **Generate simulator config**
   ```bash
   cp edge/simulator/config.template.json simulator-config.json
   
   # Edit simulator-config.json to match your server setup:
   # - Set "api_url" to your local API (e.g., "http://localhost:5228")
   # - Set "api_key" to a valid device API key
   # - Optionally customize "device_id" (e.g., "my-simulator-01")
   ```

3. **Run the simulator**
   ```bash
   python edge/simulator/worker.py --config simulator-config.json
   ```

4. **View in dashboard**
   - Open web UI at `http://localhost:5173`
   - Go to **Admin → Devices**
   - Find your simulator device (device ID from config)
   - View logs, heartbeats, and module assignments in real-time

### Simulator Features

- ✅ Runs the same control loop as real devices
- ✅ Connects to real API (requires running server)
- ✅ Real module execution (modules run as CPython, not MicroPython)
- ✅ Real heartbeats and dev command polling
- ✅ Logs appear in web dashboard like real devices

### CLI Options

```bash
python edge/simulator/worker.py \
  --config simulator-config.json \      # Config file path (default: config.json)
  --device-id test-device-001 \          # Override device ID from config
  --api-url http://your-api:5228 \      # Override API URL from config
  --api-key your-key-here \              # Override API key from config
  --max-iterations 10                    # Stop after N control loop iterations (for testing)
```

### Troubleshooting the Simulator

**`ModuleNotFoundError: No module named 'requests'`:**
- Install dependencies: `pip install -r edge/shared/tests/requirements.txt`
- Make sure you're running with the same Python/venv you installed into

**Simulator won't connect to API:**
- Verify server is running: `http://localhost:5228`
- Check API URL in config file
- Verify API key is valid

**Module execution errors:**
- Modules run as standard Python (not MicroPython)
- Check if modules use MicroPython-specific imports (e.g., `machine`, `utime`)
- Modules requiring hardware won't work in simulator

**Device doesn't appear in dashboard:**
- Wait 30+ seconds for first heartbeat
- Check API logs for registration errors
- Verify device ID is unique

---

## Step 1: Generate Device Configuration

Device configuration binds security credentials to the device ID and includes WiFi settings, API URL, and polling intervals.

### Command

```bash
python edge/tools/provision_config.py \
  --platform esp32 \
  --device-id my-esp32-001 \
  --api-url http://192.168.1.100:5228 \
  --api-key auto-generate \
  --wifi-ssid YOUR_WIFI_SSID \
  --wifi-password YOUR_WIFI_PASSWORD
```

### Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--platform` | Target platform | `esp32` or `pico` |
| `--device-id` | Unique device identifier (used in URL requests) | `kitchen-sensor-01` |
| `--api-url` | Server URL (must be reachable from device) | `http://192.168.1.100:5228` |
| `--api-key` | Device API key or `auto-generate` | `auto-generate` |
| `--wifi-ssid` | WiFi network name | `MyHome5G` |
| `--wifi-password` | WiFi password | `SuperSecure123!` |

### What Gets Created

```
edge/tools/generated/
└── esp32-config.json       # Device-specific config (encrypted credentials)
```

The config file contains:
- Device ID and API key (device-ID-bound encryption)
- WiFi credentials (device-ID-bound encryption)
- Server API URL
- Polling intervals (heartbeat: 60s, dev commands: 2s, modules: 60s)
- Logging configuration
- Power management settings (device-specific)

---

## Step 2: Deploy Firmware to Device

Deploy the runtime and configuration to the connected device.

### Prerequisites

1. **Device connected via USB** — Computer should recognize the serial port
2. **Configuration file generated** — From Step 1 above

### Command

```bash
python edge/tools/deploy_device.py \
  --platform esp32 \
  --port auto \
  --config-file edge/tools/generated/esp32-config.json
```

### Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--platform` | Target platform | Required: `esp32` or `pico` |
| `--port` | Serial port (`auto` to detect, or `COM3`, `/dev/ttyUSB0`) | `auto` |
| `--config-file` | Path to config JSON from Step 1 | Optional |
| `--force-config` | Overwrite device config even if present | `False` |
| `--verify-only` | Validate without uploading (dry-run) | `False` |

### What Happens

1. **Validates** config file syntax
2. **Connects** to device via serial (USB)
3. **Uploads** files:
   - Runtime (`main.py`, `boot.py`)
   - Platform-specific modules
   - Configuration (`config.json`)
4. **Device reboots** automatically
5. **Device boots** and connects to WiFi
6. **Device registers** with server on first heartbeat

### Expected Output

```
[INFO] Connecting to device on COM4...
[INFO] Device connected (MicroPython vX.X.X)
[INFO] Uploading files...
[INFO] Uploaded: boot.py
[INFO] Uploaded: main.py
[INFO] Uploaded: config.json
[INFO] Device rebooting...
[SUCCESS] Deploy complete! Device should connect within 60 seconds.
```

---

## Step 3: Verify Device Registration

After deployment, the device should appear in the HomeIOT dashboard within 60 seconds.

### Check in Web UI

1. Open `http://localhost:5228` in browser
2. Navigate to **Dashboard**
3. Verify **"Online Devices"** count increased by 1
4. Go to **Admin → Devices**
5. Look for your device ID in the list (e.g., `my-esp32-001`)

### What You Should See

| Field | Expected Value |
|-------|-----------------|
| Device ID | `my-esp32-001` (matches your device-id) |
| Platform | `esp32` |
| Mode | `production` |
| Last Heartbeat | Recent (within last 60 seconds) |
| Status | `online` |
| Version | Shows current firmware version |

### If Device Doesn't Appear

**Check device connectivity:**
1. Verify device is powered on (LED indicator)
2. Verify WiFi connection:
   - Use **Dev Commands** to check WiFi status
   - Navigate to device detail → click **Dev Commands**
   - Execute: `import network; sta = network.WLAN(0); print("Connected:", sta.isconnected())`
3. Verify API URL reachability:
   - Execute: `import socket; s = socket.socket(); s.connect(('192.168.1.100', 5228)); print('OK')`
4. Check device logs:
   - In device detail → **Logs** tab
   - Look for connection errors or WiFi failures

**Troubleshooting:**
- Wrong WiFi password → Re-run provision_config.py with correct credentials
- API URL incorrect → Verify device can reach server IP from device's network
- Port blocked → Ensure firewall allows port 5228
- Device offline → Check WiFi signal strength

---

## Step 4: Verify Device Heartbeat (Optional)

Monitor device communication to ensure everything is working.

### View Heartbeat History

1. Navigate to device detail page
2. Click **Heartbeats** tab
3. You should see a list of recent heartbeats (one every 60 seconds by default)
4. Each entry shows:
   - Timestamp received by server
   - Device uptime (milliseconds)
   - Free memory (bytes)

### Real-Time Monitoring

1. Navigate to device detail page
2. **Last Heartbeat** should update every ~60 seconds
3. If it's getting older, device is offline or not sending heartbeats

---

## Multiple Devices

To provision and deploy multiple devices:

1. **Generate config for each device** (unique device-id per device)
   ```bash
   python edge/tools/provision_config.py \
     --platform esp32 \
     --device-id kitchen-sensor-01 \
     --api-url http://192.168.1.100:5228 \
     --api-key auto-generate \
     --wifi-ssid YOUR_WIFI \
     --wifi-password YOUR_WIFI_PASSWORD
   
   # Repeat for device 2, 3, etc.
   ```

2. **Deploy to each device** (one at a time, via USB)
   ```bash
   # Device 1
   python edge/tools/deploy_device.py \
     --platform esp32 \
     --port auto \
     --config-file edge/tools/generated/esp32-config.json
   
   # Disconnect device 1, connect device 2
   # Device 2 config already generated with different device-id
   python edge/tools/deploy_device.py \
     --platform pico \
     --port auto \
     --config-file edge/tools/generated/pico-config.json
   ```

3. **Verify all devices** appear in dashboard

---

## Switching to Development Mode

Development mode enables verbose logging and faster polling for debugging.

### Via Web UI

1. Navigate to **Admin → Devices**
2. Find your device
3. Click **Switch Mode** button
4. Select `development`
5. Device applies mode change at next heartbeat (~60 seconds)

### Effects of Development Mode

| Setting | Production | Development |
|---------|-----------|-------------|
| Heartbeat Interval | 60s | 60s |
| Dev Command Polling | 2s | 2s |
| Log Level | INFO | DEBUG |
| Module Polling | 60s | 60s |
| WiFi Power Save | Enabled | Disabled |

---

## Updating Device Config

If you need to change WiFi or API settings after deployment:

### Method 1: Re-provision and Deploy (Recommended)

```bash
# Generate new config
python edge/tools/provision_config.py \
  --platform esp32 \
  --device-id my-esp32-001 \
  --api-url http://NEW_IP:5228 \
  --wifi-ssid NEW_WIFI \
  --wifi-password NEW_PASSWORD

# Force config update on device
python edge/tools/deploy_device.py \
  --platform esp32 \
  --port auto \
  --config-file edge/tools/generated/esp32-config.json \
  --force-config
```

### Method 2: Config-Only Update

To update config without re-uploading runtime:

```bash
python edge/tools/deploy_device.py \
  --platform esp32 \
  --port auto \
  --config-file edge/tools/generated/esp32-config.json
```

The tool preserves the runtime by default.

---

## Removing a Device

### From Web UI

1. Navigate to **Admin → Devices**
2. Find your device
3. Click **Delete** button
4. Confirm deletion

Device will no longer appear in dashboard (but can be re-registered anytime).

### Physical Device

To repurpose the device:
1. Delete from dashboard (above)
2. Connect device via USB again
3. Run `provision_config.py` with new device-id
4. Run `deploy_device.py` to deploy with new config

---

## Troubleshooting

### Device Connection Issues

**Symptom: Device never appears in dashboard**

```bash
# Check device serial output (real-time log)
python -m mpremote connect COM4 repl

# In REPL, run:
import network
sta = network.WLAN(0)
print("Connected:", sta.isconnected())
print("IP:", sta.ifconfig())

# Exit with Ctrl+X
```

**Solutions:**
- Verify WiFi SSID and password in config (re-run provision_config.py)
- Check device can reach API server: `socket.connect(('192.168.1.100', 5228))`
- Verify firewall allows port 5228

### Device Goes Offline

**Symptom: Device was online, now offline**

1. Check device is powered on
2. Check WiFi signal (move device closer to router)
3. Check logs:
   - Device detail → **Logs** tab
   - Look for WiFi disconnection errors
4. Restart device (power cycle or soft reset)

### Deploy Fails

**Error: `mpremote: command not found`**
```bash
# Install mpremote
pip install mpremote

# Verify installation
mpremote version
```

**Error: `No device found on port`**
```bash
# Check connected devices
python -m mpremote list

# Manually specify port
python edge/tools/deploy_device.py \
  --platform esp32 \
  --port COM3 \
  --config-file edge/tools/generated/esp32-config.json
```

**Error: `Config validation failed`**
- Verify JSON syntax in generated config file
- Ensure all required fields present (device_id, api_url, wifi_ssid, wifi_password)
- Re-run provision_config.py to regenerate

---

## Next Steps

1. ✅ Device is provisioned and registered
2. ⏭️ [Assign modules to device](features-modules.md)
3. ⏭️ [Execute dev commands for testing](features-dev-commands.md)
4. ⏭️ [Monitor device via Dashboard](features-dashboard.md)
