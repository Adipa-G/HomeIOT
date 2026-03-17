# HomeIOT API Specification (v1 Tightened Contract)

Version: 1.0
Date: 2026-05-28

## Contract Goals

- Remove ambiguity in device mode control.
- Require auth headers on every endpoint.
- Make header identity authoritative.

## Base URL

- http://{host}:{port}
- All paths below are absolute under this base.

## Authentication

Required request headers on all endpoints:

- X-Device-ID: device identifier
- X-Api-Key: device secret

Authoritative identity rule:

- Server must identify device from X-Device-ID header.
- If a body also carries device_id, it must match header value, otherwise 400.
- For GET endpoints (no body), header identity is the only identity source.

## Device Mode

- mode values: production | development
- mode is returned via heartbeat response metadata.
- No role field in v1.
- No admin_exec_enabled field in v1.

Interpretation:

- mode=production: module runtime active, dev command polling inactive.
- mode=development: module runtime active, dev command polling active.

Development mode is additive, not exclusive.

## Existing Endpoints (unchanged paths)

### POST /api/devices/register

Purpose:

- Register or refresh device record.

Request body example:

```json
{
  "device_id": "esp32-001",
  "version": "1.0.0",
  "ip": "192.168.1.30",
  "timestamp": 1716890000
}
```

Response 200/201 example:

```json
{
  "status": "ok",
  "device_id": "esp32-001"
}
```

Notes:

- Must require X-Device-ID and X-Api-Key.
- If device_id in body differs from X-Device-ID, return 400.
- platform may be accepted by the server, but current edge clients do not send it.

### POST /api/devices/heartbeat

Purpose:

- Presence signal and runtime control metadata.

Request body example:

```json
{
  "device_id": "esp32-001",
  "timestamp": 1716890000,
  "uptime_ms": 420000,
  "free_memory_bytes": 122880
}
```

Response 200 example:

```json
{
  "status": "ok",
  "server_time_utc": "2026-05-28T14:30:00Z",
  "mode": "development",
  "dev_poll_interval_ms": 2000,
  "module_assignment_poll_interval_ms": 60000,
  "next_heartbeat_ms": 30000
}
```

Notes:

- mode is authoritative for enabling dev command polling.
- Heartbeat remains lightweight and does not carry full command/module payloads.

### GET /api/ota/check

Purpose:

- Check OTA availability.

Query example:

- /api/ota/check?version=1.0.0

Notes:

- Current edge clients also send X-Current-Version as an optional header hint.

Response 200 example:

```json
{
  "available": true,
  "version": "1.0.1",
  "manifest": [
    {"path": "main.py", "hash": "..."},
    {"path": "config.json", "hash": "..."}
  ]
}
```

Response 200 no update example:

```json
{
  "available": false
}
```

### GET /api/ota/file

Purpose:

- Download OTA file by version/path.

Query example:

- /api/ota/file?version=1.0.1&path=main.py

Response:

- 200 with binary payload.

### POST /api/devices/logs

Purpose:

- Upload batched logs.

Request body example:

```json
{
  "device_id": "esp32-001",
  "reason": "interval",
  "sentAt": 1716890000,
  "dropped_count": 0,
  "truncated": false,
  "logs": [
    {"ts": 1716890000, "level": "INFO", "message": "Booted", "context": {}}
  ]
}
```

Response 200 example:

```json
{
  "status": "ok",
  "received": 1
}
```

## New Endpoints (development commands + module runtime)

### GET /api/devices/dev-commands/next

Purpose:

- Return next development command for mode=development devices.

Polling:

- Every 2000ms (with small jitter).

Execute policy:

- Execute only on change.
- Device executes when revision_hash changed or forceRerun=true.

Query example:

- /api/devices/dev-commands/next?last_revision_hash=abc

Response 200 example:

```json
{
  "command_id": "cmd-001",
  "revision_hash": "def456",
  "code": "print('hello')",
  "timeout_ms": 5000,
  "forceRerun": false,
  "dedupe_token": "cmd-001:def456",
  "expires_at_utc": "2026-05-28T14:35:00Z",
  "signature": "base64sig"
}
```

Response when no command:

- 204 No Content

### POST /api/devices/dev-commands/{commandId}/result

Purpose:

- Submit execution outcome for development command.

Request body example:

```json
{
  "command_id": "cmd-001",
  "revision_hash": "def456",
  "dedupe_token": "cmd-001:def456",
  "status": "success",
  "started_at_utc": "2026-05-28T14:30:00Z",
  "finished_at_utc": "2026-05-28T14:30:01Z",
  "elapsed_ms": 1000,
  "exit_code": 0,
  "stdout": "hello",
  "stderr": ""
}
```

Response 200 example:

```json
{
  "status": "recorded"
}
```

### GET /api/devices/modules/assignment

Purpose:

- Return module assignment metadata.

Query example:

- /api/devices/modules/assignment?last_assignment_hash=abc

Response 200 example:

```json
{
  "assignment_hash": "xyz789",
  "modules": [
    {
      "module_id": "temp-sensor",
      "version": "2.0.0",
      "interval_ms": 60000,
      "timeout_ms": 10000,
      "package_hash": "...",
      "signature": "..."
    }
  ]
}
```

Response when unchanged:

- 204 No Content

### GET /api/devices/modules/package

Purpose:

- Download signed module package.

Query example:

- /api/devices/modules/package?module_id=temp-sensor&version=2.0.0

Response:

- 200 with binary package.

### POST /api/devices/modules/results

Purpose:

- Submit module run result.

Request body example:

```json
{
  "device_id": "esp32-001",
  "module_id": "temp-sensor",
  "module_version": "2.0.0",
  "run_id": "run-123",
  "started_at_utc": "2026-05-28T14:30:00Z",
  "finished_at_utc": "2026-05-28T14:30:02Z",
  "elapsed_ms": 2000,
  "status": "success",
  "output": {"temperature": 23.1},
  "error_message": null,
  "metrics": {"memory_peak_bytes": 45000}
}
```

### POST /api/devices/modules/status

Purpose:

- Submit module quarantine or re-enable state from the device.

Request body example:

```json
{
  "device_id": "esp32-001",
  "module_id": "temp-sensor",
  "module_version": "2.0.0",
  "disabled": true,
  "disabled_reason": "Failed start count exceeded threshold (3 consecutive failures)",
  "failed_start_count": 3,
  "disabled_at_utc": "2026-05-28T14:30:00Z"
}
```

Re-enable acknowledgement example:

```json
{
  "device_id": "esp32-001",
  "module_id": "temp-sensor",
  "module_version": "2.0.0",
  "disabled": false
}
```

Response 200 example:

```json
{
  "status": "recorded"
}
```

## Status Codes

---

### POST /api/devices/modules/status

Purpose:

- Report a module quarantine (disable) event from the device, or acknowledge a server-initiated re-enable.
- This endpoint handles both directions. The device sends `disabled: true` when a module is quarantined after repeated failures, and `disabled: false` when acknowledging a server re-enable.
- If the device was offline at the time of quarantine, it will send this notification on the next connected loop iteration.

Request body (device-initiated disable):

```json
{
  "device_id": "esp32-001",
  "module_id": "temp-sensor",
  "module_version": "2.0.0",
  "disabled": true,
  "disabled_reason": "Failed start count exceeded threshold (3 consecutive failures)",
  "failed_start_count": 3,
  "disabled_at_utc": "2026-05-29T10:15:00Z"
}
```

Request body (device acknowledges re-enable):

```json
{
  "device_id": "esp32-001",
  "module_id": "temp-sensor",
  "module_version": "2.0.0",
  "disabled": false
}
```

Response 200 example:

```json
{
  "status": "recorded"
}
```

Re-enable flow:

- Server sets `enabled: true` on the module in the next assignment response.
- Device sees `enabled: true` in the assignment, clears local quarantine state, schedules the module for immediate execution, and posts to this endpoint with `disabled: false` as an acknowledgement.
- Version change in the assignment also clears quarantine locally (no status post required for that path).

## Status Codes

- 200 OK
- 201 Created
- 202 Accepted
- 204 No Content
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 409 Conflict
- 410 Gone
- 413 Payload Too Large
- 429 Too Many Requests
- 500 Internal Server Error
- 503 Service Unavailable

## Idempotency and Dedupe

Recommended write dedupe keys:

- register: device_id
- heartbeat: device_id + timestamp bucket
- logs: device_id + sentAt + reason
- dev command result: device_id + command_id + revision_hash
- module results: device_id + module_id + run_id

If Idempotency-Key is provided on POST, server should cache/return same outcome for retried requests.

## .NET Implementation Notes

- Add middleware to enforce required headers globally for /api/* routes.
- Resolve device context from X-Device-ID first; validate X-Api-Key against device record.
- Reject body/header device_id mismatch with 400.
- Keep controllers thin and use services:
  - DeviceAuthService
  - HeartbeatService
  - OtaService
  - DevCommandService
  - ModuleRuntimeService
  - LogIngestionService
- Keep development command dispatch separate from heartbeat endpoint logic.
