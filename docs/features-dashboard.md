# Dashboard Feature Guide

The HomeIOT Dashboard provides a real-time overview of your IoT system with 24-hour metrics and key performance indicators.

## Dashboard Overview

Navigate to `http://localhost:5228/dashboard` to access the main dashboard.

### What You See

The dashboard displays aggregated statistics for the past 24 hours:

| Metric | Description |
|--------|-------------|
| **Total Devices** | Count of all registered devices |
| **Online Devices** | Devices with heartbeat in last 24 hours (online = recent heartbeat) |
| **Modules** | Total count of unique modules in the system |
| **Active Assignments** | Number of devices with currently assigned modules |
| **Total Users** | Admin user count |
| **Heartbeats (24h)** | Total heartbeat messages received |
| **Logs (24h)** | Total device log entries received |
| **Module Runs (24h)** | Total module executions completed |
| **Module Failures (24h)** | Total modules that failed to execute (useful for identifying problem modules) |

## Understanding the Metrics

### Online Devices

A device is marked **online** if it sent a heartbeat within the last 24 hours. By default, devices send heartbeats every 60 seconds, so:
- ✅ **Online**: Heartbeat timestamp is recent (within last few minutes)
- ⏸️ **Offline**: No recent heartbeat (device disconnected, powered off, or network issue)

### Module Assignments

Shows how many devices currently have active module assignments. This indicates:
- How widely your modules are deployed
- If you have idle devices waiting for assignments

### Failures Metric

Track the **Module Failures** count to identify problematic modules:
- High failure rate on a specific module → Module might have a bug
- All failures on one device → Device configuration issue
- No failures → System healthy

## Navigation from Dashboard

From the dashboard, click any of these cards to drill down:

| Card | Navigates To |
|------|--------------|
| **Online Devices** | Device list (filtered by online status) |
| **Modules** | Module list (view all modules) |
| **Active Assignments** | Module assignments (see which modules assigned to which devices) |
| **Total Users** | User management (admin users) |

## Real-Time Updates

The dashboard refreshes automatically every 10 seconds. You'll see:
- Heartbeat count increasing as devices send keep-alives
- Module runs increasing when modules execute
- Failures appearing if modules encounter errors

## Next Steps

- [📖 View and manage devices](features-devices.md)
- [📖 Create and assign modules](features-modules.md)
- [📖 Monitor user access](features-users.md)
