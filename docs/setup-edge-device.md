# Edge Device Setup Guide

This guide covers adding an ESP32 or Raspberry Pi Pico to HomeIOT, and running the PC simulator for development.

Devices are added from the web UI. **Add device** registers the device, generates its API key, and downloads a single `main.py` installer. When that file runs on the board, it writes `config.json`, connects to WiFi, and installs the latest firmware release through the normal OTA updater. You don't need to generate config or deploy files by hand.

## Prerequisites

- **Server running.** See [Server Setup](setup-server.md).
- **A firmware release for the device's platform.** The installer downloads the latest release, so at least one must exist. See [Step 1](#step-1-publish-a-firmware-release).
- **MicroPython flashed on the board.** Use the firmware from [micropython.org/download](https://micropython.org/download/).
- **A way to copy one file to the board.** Either `mpremote` (`pip install mpremote`) or Thonny.
- **WiFi credentials** for the network the device will join (2.4 GHz).

---

## Step 1: Publish a Firmware Release

Skip this step if the OTA page already lists a release for your platform.

1. Build the release from the edge source tree:
   ```bash
   python edge/tools/build_artifact.py --platform esp32 --version 1.0.0
   ```
2. Make it available to the API:
   - **API running from source:** nothing more to do. The release is written to `api/artifacts/{platform}/{version}`, which is the development artifact root.
   - **Docker or remote server:** zip the *contents* of `api/artifacts/esp32/1.0.0/` into `1.0.0.zip`. Upload it in the web UI at **OTA → esp32** (or open `/ota/esp32` directly if no platform is listed yet). The zip file name becomes the version.

See [edge/tools/USAGE.md](../edge/tools/USAGE.md) for build options.

---

## Step 2: Add the Device

1. In the web UI, go to **Devices** and click **Add device**.
2. Fill in the form:

   | Field | Description | Example |
   |-------|-------------|---------|
   | Device ID | Unique identifier: letters, digits, `.`, `_` or `-` (max 64) | `kitchen-sensor-01` |
   | Platform | `esp32` or `pico` | `esp32` |
   | API URL | Server URL **as seen from the device** | `http://192.168.1.100:8080` |
   | WiFi SSID | Network name | `MyHome` |
   | WiFi password | Network password | |

3. Click **Create & download main.py**. The browser downloads `main.py`.

The device now appears in the list with an **Awaiting first boot** badge.

> **API URL must resolve on the device.** The board uses your router's DNS, which usually can't resolve bare local machine names such as `homesvr`. Use an IP address or a hostname your router's DNS knows. The URL defaults to the address you are browsing from; change it if that is `localhost`.

> **`main.py` contains secrets.** It holds the device API key and your WiFi password, in plain text. Delete the downloaded file once it is on the device. WiFi credentials are not stored on the server.

---

## Step 3: Install on the Board

1. Connect the board via USB. It must already run MicroPython.
2. Copy the installer and reset the board:
   ```bash
   mpremote cp main.py :main.py
   mpremote reset
   ```
   With Thonny instead: open `main.py`, choose **File → Save as… → MicroPython device**, name it `main.py`, then press the board's reset button.
3. Optionally watch progress with `mpremote repl`.

### What Happens

1. The installer unpacks its embedded bootstrap code (shared edge code) into `bootstrap_lib/`.
2. It writes `config.json`, with the API key and WiFi password encrypted and bound to the device ID.
3. It connects to WiFi.
4. It asks the API for the latest release (`/api/ota/check`), downloads every file, and verifies the hashes. This is the same updater that handles OTA updates.
5. The new firmware replaces `main.py`, and the board resets.
6. The firmware sends its first heartbeat. The **Awaiting first boot** badge disappears.

### Expected Output

```
[bootstrap] Unpacking installer payload
[bootstrap] INFO Bootstrap started {"device_id": "kitchen-sensor-01", "platform": "esp32"}
[bootstrap] INFO Config written {"path": "config.json"}
[bootstrap] INFO Connecting to WiFi {"ssid": "MyHome", "attempt": 1}
[bootstrap] INFO WiFi connected {"ip": "192.168.1.57"}
[bootstrap] INFO Sending OTA check request {...}
[bootstrap] INFO Installing firmware {"version": "1.0.0"}
...
```

If installation fails, the installer prints `[bootstrap] Install failed: ...`, waits 60 seconds, and tries again. See [Troubleshooting](#troubleshooting).

---

## Step 4: Verify the Device

Within about a minute of the reset, check the device in **Devices**:

| Field | Expected Value |
|-------|-----------------|
| Device ID | Your device ID |
| Platform | `esp32` or `pico` |
| Mode | `production` |
| Last Heartbeat | Recent |
| Version | The release that was installed |

The **Heartbeats** and **Logs** tabs on the device detail page show ongoing activity.

---

## Multiple Devices

Repeat [Step 2](#step-2-add-the-device) and [Step 3](#step-3-install-on-the-board) for each board. Every device needs its own ID and its own downloaded `main.py`, because each file carries that device's unique API key.

---

## Re-provisioning a Device

Re-provision a device to change its WiFi network or API URL, recover a lost key, or reinstall a board from scratch.

1. Open the device detail page and click **Re-provision**.
2. Enter the API URL and WiFi credentials, then click **Rotate key & download main.py**.
3. Copy it to the board and reset, as in [Step 3](#step-3-install-on-the-board).

Re-provisioning **rotates the device API key**. The old key stops working immediately, so a board still running with old config gets `401` responses until it runs the new installer. The device keeps its history, modules and settings.

---

## Switching to Development Mode

Development mode enables verbose logging and faster polling for debugging.

1. Go to **Devices** and open your device.
2. Click **Switch Mode** and select `development`.
3. The device applies the change at its next heartbeat.

| Setting | Production | Development |
|---------|-----------|-------------|
| Heartbeat Interval | 60s | 60s |
| Dev Command Polling | 2s | 2s |
| Log Level | INFO | DEBUG |
| Module Polling | 60s | 60s |
| WiFi Power Save | Enabled | Disabled |
| Radio-off light sleep | Opt-in | Never |

---

## Power Saving

Power settings live in the `power` block of `edge/platforms/<platform>/src/config.json`. They ship to devices with each release. Production mode uses WiFi `powersave` mode by default.

**Radio-off light sleep** is off by default. It uses much less power between polls on ESP32, Pico W and Pico 2 W. To enable it, set `"radio_off_sleep_enabled": true` and publish a release. In production mode, when the next scheduled task is at least `radio_off_sleep_min_ms` away (default 15000), the device:

1. Powers the WiFi radio down and enters `machine.lightsleep()`. RAM is kept, so the control loop continues where it left off.
2. On waking, reconnects to WiFi and re-applies the power-save mode. The `WiFi connected` log line includes `connect_ms`, so you can measure the reconnect cost on your network. A `Radio-off sleep finished` line shows how much of each sleep was real light sleep (`light_slept_ms`). If it is `0`, the board fell back to regular sleep.

On Pico W and Pico 2 W the WiFi chip is fully powered off (`WLAN.deinit()`) before sleeping, so each wake also reloads its firmware.

`wifi_country` is a per-device setting like `wifi_ssid`. Each device uses the two-letter country code in its own `config.json`, which updates never overwrite. If none is set, it defaults to `AU`. The release `config.json` ships the placeholder `"replace-with-wifi-country"`. The country matters because with the worldwide default the radio only listens passively on channels 12–13, which makes cold reconnects slow or unreliable. If a join times out, the radio is powered down and the error includes the WiFi status code (e.g. `WiFi connection timed out (status=-2)`).

Development mode never uses it. If `machine.lightsleep()` is missing or keeps returning immediately, the device logs a warning and falls back to regular sleep. USB serial drops while the board sleeps.

**ESP32-C6:** from MicroPython 1.27, `machine.lightsleep()` hangs on the C6 until its low-power watchdog resets the chip ([micropython#19396](https://github.com/micropython/micropython/issues/19396)). The firmware detects this, logs `Radio-off sleep unsupported … reason=micropython#19396`, and keeps WiFi connected with regular sleep instead. Radio-off sleep works on the C6 only with MicroPython 1.26.1 or earlier.

**Watchdog:** devices reset if the control loop stops feeding the watchdog for 120 s. The Pico hardware watchdog can't go above about 8 s, so the firmware feeds it from a timer while the app keeps checking in. An interactive REPL session on an installed device therefore resets after about two minutes.

---

## Removing a Device

1. Go to **Devices** and open your device.
2. Click **Delete** and confirm.

The device's API key is deleted with it, so the board can no longer talk to the server. To reuse the board, add it again with **Add device** (the same or a new ID) and install the new `main.py`.

---

## Alternative: Running a PC Simulator

Without a physical device, you can run the edge control loop on your PC.

### Quick Start

1. **Install dependencies**
   ```bash
   pip install -r edge/shared/tests/requirements.txt
   ```
   The simulator runs as CPython, so its HTTP client uses the `requests` package from this requirements file.

2. **Create the simulator config**
   ```bash
   cp edge/simulator/config.template.json simulator-config.json
   ```
   Set `api_url` to your API (e.g. `http://localhost:5228`). Then set `device_id` and `api_key` to a device the server knows. The server rejects unknown devices. Either:
   - keep the defaults (`simulator-device-1` / `simulator-api-key`), which match the development seed device (see [Server Setup](setup-server.md)); or
   - create a device with **Add device**, then copy its `device_id` and `api_key` from the `#@@PROVISION {...}` line near the top of the downloaded `main.py`. The simulator config takes the plain-text key.

3. **Run the simulator**
   ```bash
   python edge/simulator/worker.py --config simulator-config.json
   ```

4. **View in dashboard.** Open the web UI, go to **Devices**, and select your simulator device to see logs, heartbeats and module assignments.

### Simulator Features

- Runs the same control loop as real devices
- Connects to the real API (requires a running server)
- Runs modules as CPython, not MicroPython
- Sends real heartbeats and polls for dev commands
- Logs appear in the web dashboard like those from real devices

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
- Install the dependencies: `pip install -r edge/shared/tests/requirements.txt`. Use the same Python/venv you run the simulator with.

**`401 Unauthorized` / device not shown:**
- The device ID must already exist on the server, and the API key must match it. Self-registration is disabled.
- If the device was re-provisioned, copy the new key from the new `main.py`.

**Module execution errors:**
- Modules that import MicroPython-only modules (`machine`, `utime`) or need hardware won't work in the simulator.

---

## Troubleshooting

### Installer Errors (`[bootstrap] Install failed: ...`)

**`OSError: -2` / `-202`, or "Cannot resolve the API host"**
- The device can't resolve the API host name. Re-provision with an IP address (e.g. `http://192.168.1.100:8080`) or a hostname your router's DNS resolves.

**"No firmware release received"**
- Check that a release exists for the device's platform ([Step 1](#step-1-publish-a-firmware-release)).
- Check that the API URL is correct, and that the device wasn't deleted or re-provisioned after this `main.py` was downloaded.

**WiFi connection failed**
- Check the SSID and password, and that the network is 2.4 GHz. Re-provision with the correct credentials.

**Connection refused / timeouts**
- Check that the server is reachable from the device's network, and that the firewall allows the API port.

**Hash mismatch**
- The release on the server is stale or incomplete. Rebuild it with `build_artifact.py` and publish it again.

### Add Device Errors

| Message | Cause |
|---------|-------|
| Device already exists | The ID is taken. Pick another ID, or use **Re-provision** on the existing device. |
| No firmware release | Publish a release for the platform first ([Step 1](#step-1-publish-a-firmware-release)). |
| Release incomplete | The latest release is missing files. Rebuild and publish it again. |

### Device Goes Offline

1. Check that the device has power.
2. Check WiFi signal strength.
3. Check the **Logs** tab on the device detail page for WiFi or HTTP errors.
4. If logs show `401`, the key was rotated. Re-provision the device.
5. Power-cycle the device.

To inspect a connected board directly:

```bash
mpremote repl
# In the REPL:
import network
sta = network.WLAN(0)
print("Connected:", sta.isconnected(), sta.ifconfig())
```

---

## Next Steps

1. ⏭️ [Assign modules to device](features-modules.md)
2. ⏭️ [Execute dev commands for testing](features-dev-commands.md)
3. ⏭️ [Monitor device via Dashboard](features-dashboard.md)
