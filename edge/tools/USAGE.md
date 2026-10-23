# Edge Tools Usage

This folder provides two tools:

1. `build_artifact.py` - builds an OTA firmware release from the current edge source tree
2. `run_dev_command.py` - sends arbitrary Python code to a device for remote execution

New devices are not configured or flashed with tools. Use **Add device** on the web UI Devices page, which registers the device and downloads a `main.py` installer that writes `config.json` and installs the latest release built by `build_artifact.py`. See [Edge Device Setup](../../docs/setup-edge-device.md).

API route policy:

- Endpoint paths are centralized in shared code and are not meant to be customized in config.
- Logging uplink uses the shared logs route constant.

## Tool 1: build_artifact.py

Build an OTA artifact from the current edge source tree. Copies all deployable files to `api/artifacts/{platform}/{version}/`, computes SHA256 hashes, and writes a `manifest.json`.

```bash
python edge/tools/build_artifact.py --platform esp32 --version 1.0.0
```

Custom output directory:

```bash
python edge/tools/build_artifact.py --platform esp32 --version 1.0.1 --out api/artifacts
```

Output structure:

```
api/artifacts/esp32/1.0.0/
  manifest.json
  main.py
  config.json
  edge/shared/app/...
  edge/platforms/esp32/...
```

Important:

- Must be re-run after every edit to edge source files — the artifact is a snapshot and stale hashes cause OTA hash mismatch failures on the device.
- `config.json` in the artifact should use placeholder values (`"replace-with-device-id"`, `"replace-with-api-url"`, `"replace-with-wifi-country"`) so device-specific values are preserved during OTA merge. A device's existing `wifi_country` is always kept; devices without one default to `AU`. A device's existing `power.radio_off_sleep_enabled` is also kept; the release value only seeds devices that don't have one.
- The **Add device** installer is built from the latest release of the selected platform, so at least one release must exist before a device can be added.

Publishing a release:

- When the API runs locally from source, the default `--out api/artifacts` is the API's artifact root, so the release is available immediately.
- For a Docker or remote server, zip the *contents* of `api/artifacts/{platform}/{version}/` into `{version}.zip` (e.g. `1.0.0.zip`) and upload it in the web UI at `/ota/{platform}` (the zip file name becomes the version).

## Tool 2: run_dev_command.py

Send arbitrary Python code to a device for remote execution via the admin API. The code runs on the device via `exec()` in memory — nothing is written to the device filesystem. This is the interactive development environment for testing module logic before deploying it.

Requires:

- The API must be running.
- The target device must be in `development` mode (heartbeat returns `mode=development`).
- Admin credentials (default: `Admin` / `123`).

Inline code:

```bash
python edge/tools/run_dev_command.py \
  --api-url http://192.168.68.60:5228 \
  --device-id esp32-001 \
  --code "print('hello from device')"
```

Code from file:

```bash
python edge/tools/run_dev_command.py \
  --api-url http://192.168.68.60:5228 \
  --device-id esp32-001 \
  --code-file my_test_script.py
```

Code from stdin:

```bash
echo "import gc; print(gc.mem_free())" | python edge/tools/run_dev_command.py \
  --api-url http://192.168.68.60:5228 \
  --device-id esp32-001
```

Custom credentials:

```bash
python edge/tools/run_dev_command.py \
  --api-url http://192.168.68.60:5228 \
  --device-id esp32-001 \
  --username Admin --password mypassword \
  --code "print('hi')"
```

Adjust polling and timeout:

```bash
python edge/tools/run_dev_command.py \
  --api-url http://192.168.68.60:5228 \
  --device-id esp32-001 \
  --code "print('slow')" \
  --timeout-ms 30000 \
  --poll-interval 5 \
  --max-polls 10
```

Returning structured data (set `result` variable in your code):

```bash
python edge/tools/run_dev_command.py \
  --api-url http://192.168.68.60:5228 \
  --device-id esp32-001 \
  --code "import gc; gc.collect(); result = {'free': gc.mem_free(), 'alloc': gc.mem_alloc()}"
```

The response will show both `stdout` (from `print()`) and `data` (from `result` variable).

Auth flow:

- The tool authenticates via `POST /api/admin/auth/token` with `--username` / `--password` to get a JWT.
- Enqueue and result polling use `Authorization: Bearer <token>` against `/api/admin/dev-commands`.
- Device credentials (`X-Device-ID` / `X-Api-Key`) are not needed by the operator.
