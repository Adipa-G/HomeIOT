# Device Management Guide

The Devices screen lets you monitor, filter, and manage all connected IoT devices.

## Accessing Devices

Navigate to **Admin → Devices** to see the device list.

---

## Device List

### Viewing Devices

The device list shows all registered devices with key information:

| Column | Description |
|--------|-------------|
| **Device ID** | Unique identifier (e.g., `kitchen-sensor-01`) |
| **Platform** | Hardware type: `esp32` or `pico` |
| **Version** | Current firmware version |
| **Mode** | `production` or `development` (affects polling intervals and logging) |
| **Last Heartbeat** | When device last checked in (e.g., "2 seconds ago") |
| **IP Address** | Device's WiFi IP address |
| **Status** | `online` if heartbeat in last 24h, `offline` otherwise |

### Filtering Devices

Use filters at the top of the list:

- **Platform Filter** — Show only `esp32` or `pico` devices
- **Mode Filter** — Show only `production` or `development` devices
- **Search** — Find devices by device ID (substring match)

### Pagination

If you have many devices, navigate using pagination controls at the bottom. Each page shows 10-20 devices.

---

## Device Details

Click on any **Device ID** to view detailed information and metrics.

### Device Information

Shows basic device details:
- Device ID
- Platform
- Version
- Mode (production/development)
- IP address
- Last heartbeat timestamp
- Created date

### Device Tabs

#### Heartbeats Tab

Shows heartbeat history with device status metrics:

| Field | Description |
|-------|-------------|
| **Timestamp** | When heartbeat was received (server time) |
| **Uptime (ms)** | Device uptime in milliseconds (time since device powered on) |
| **Free Memory (bytes)** | Available RAM on device (useful for detecting memory leaks) |

**Use case:** If free memory is decreasing over time, a module might have a memory leak.

#### Logs Tab

Device-generated log messages with timestamp, level, and content:

| Field | Description |
|-------|-------------|
| **Timestamp** | When log was generated (device time) |
| **Level** | Log severity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| **Message** | Log message text |

**Use case:** Debugging device issues (WiFi errors, module execution failures, etc.)

**Filtering logs:**
- View last 24 hours by default
- Adjust time range with date pickers (if available)

#### Module Results Tab

Output from executed modules:

| Field | Description |
|-------|-------------|
| **Module Name** | Which module executed |
| **Status** | `success` or `failed` |
| **Output** | Module output (stdout) or error message |
| **Timestamp** | When module executed |

**Use case:** Verify modules are executing correctly and producing expected output.

---

## Device Actions

### Switch Mode

Toggle between `production` and `development` modes:

**Production Mode:**
- Lower device power consumption
- Standard polling intervals
- INFO level logging

**Development Mode:**
- Faster polling for debugging
- DEBUG level logging
- More verbose output (useful when troubleshooting)

**Steps:**
1. Click device
2. Click **Switch Mode** button
3. Confirm mode change
4. Mode takes effect at next heartbeat (within 60 seconds)

### Delete Device

Permanently remove device from the system:

**Steps:**
1. Click device
2. Click **Delete** button
3. Confirm deletion

**Note:** Device can be re-registered anytime by deploying firmware again with the same device-id. Deleting removes all associated data (logs, heartbeats, results).

---

## Device Lifecycle

### New Device (Just Deployed)

1. Device registers on first heartbeat
2. Appears in **Devices** list with status `online`
3. Mode defaults to `production`
4. Last heartbeat is "now"

### Online Device

- Sends heartbeat every 60 seconds (default)
- Status: `online`
- Last heartbeat timestamp is recent

### Offline Device

- Device hasn't sent heartbeat in 24+ hours
- Status: `offline`
- Could be: powered off, network disconnected, or crashed

### Reconnecting Device

- If offline device powers back on and connects to WiFi
- Sends heartbeat to server
- Status changes back to `online`
- All previous logs and results are still available

---

## Common Workflows

### Monitor Device Health

1. Navigate to device
2. Check **Last Heartbeat** — Should be recent (within 60 seconds)
3. View **Heartbeats** tab — Check if **Free Memory** is stable
4. View **Logs** tab — Look for errors or warnings

### Debug Device Issue

1. Navigate to device
2. View **Logs** tab — Find error messages
3. View **Heartbeats** tab — Check memory trends
4. Switch to **Development Mode** for more verbose logging
5. Use **Dev Commands** to test device state (see [Dev Commands Guide](features-dev-commands.md))

### Check Module Execution

1. Navigate to device
2. Click **Module Results** tab
3. Verify modules have executed (`status: success`)
4. If failed, check output for error message

### Identify Offline Devices

1. Navigate to **Devices** list
2. Filter by **Status** = `offline` (if filter available)
3. Or scroll and look for "Last Heartbeat" showing "days ago"
4. Investigate: Power issue? Network? Crashed firmware?

---

## Device Naming Convention (Optional)

While device-id can be any string, a consistent naming convention helps organization:

**Suggested Format:** `{location}-{sensor-type}-{number}`

Examples:
- `kitchen-temp-01`
- `garage-motion-sensor-01`
- `bedroom-light-controller-02`
- `living-room-air-quality-01`

This makes filtering and searching easier as your fleet grows.

---

## Next Steps

- [📖 Assign modules to devices](features-modules.md)
- [📖 Execute dev commands for debugging](features-dev-commands.md)
- [📖 Monitor system health on dashboard](features-dashboard.md)
