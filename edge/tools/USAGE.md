# Edge Tools Usage

This folder provides two tools:

1. `build_artifact.py` - builds an OTA firmware release from the current edge source tree
2. `run_dev_command.py` - sends arbitrary Python code to a device for remote execution

New devices are not configured or flashed with tools. Use **Add device** on the web UI Devices page, which registers the device and downloads a `main.py` installer that writes `config.json` and installs the latest release built by `build_artifact.py`. See [Edge Device Setup](../../docs/setup-edge-device.md).

API route policy:

- Endpoint paths are centralized in shared code and are not meant to be customized in config.
- Logging uplink uses the shared logs route constant.

## Tool 1: build_artifact.py

Build an OTA artifact from the current edge source tree. Writes all deployable files to `api/artifacts/{platform}/{version}/`, computes SHA256 hashes, and writes a `manifest.json`. Modules are precompiled to `.mpy` with `mpy-cross` (a dev dependency in `edge/pyproject.toml`), so run it through `uv`:

```bash
uv run --project edge python edge/tools/build_artifact.py --platform esp32 --version 1.0.0
```

Custom output directory:

```bash
uv run --project edge python edge/tools/build_artifact.py --platform esp32 --version 1.0.1 --out api/artifacts
```

Uncompiled `.py` release (larger; useful when debugging on a device):

```bash
uv run --project edge python edge/tools/build_artifact.py --platform esp32 --version 1.0.2 --source
```

### Compiled releases

Compiled releases are about 62% smaller (ESP32: 170 KB to 64 KB), and devices skip compiling modules at import, which lowers peak RAM.

- Modules are bytecode-only `.mpy` (no `-march`), which loads on every port with `.mpy` v6 firmware (MicroPython 1.19+; ESP32 1.30 and Pico W 1.28 are both fine). The firmware must also support 31-bit small ints, which ESP32 and rp2 do.
- Everything except `boot.py` and `main.py` is compiled; MicroPython runs those two by name, so they stay as `.py`.
- Every release starts with `mpy_probe.mpy`, a one-line module compiled with the rest of the release. Before installing, the device updater imports it from staging, so the firmware's own loader decides whether it can load the release. If it can't, the device keeps its current version, logs `OTA release is incompatible with this firmware` with the reason, and doesn't download that version again until it reboots.
- The **Add device** installer embeds compiled modules as base64 and imports the probe before running anything else, so a board with unsupported firmware stops with a clear message instead of a broken install.
- The probe proves the firmware loads this release's `.mpy` format. It can't catch a bug in the firmware's `.mpy` loader that only shows up for particular code. If that happened on the boot path, the device would need reflashing over USB; that risk is accepted.
- Empty package `__init__.py` files stay as source; they are smaller than their `.mpy`.
- Tracebacks keep line numbers and show the release path (e.g. `edge/shared/app/control_loop.py`).

### Rolling out compiled releases for the first time

Devices on releases built before compiled-release support don't have the `.mpy` check, so roll out in this order:

1. Build and publish a **source** release (`--source`) so every device gets the updater that runs the probe.
2. Build a compiled release and install it on one ESP32 and one Pico W first. Check that both boot, send heartbeats and show no `incompatible` warnings in their logs.
3. Publish it for the rest of the devices.

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
uv run --project edge python edge/tools/run_dev_command.py \
  --api-url http://192.168.68.60:5228 \
  --device-id esp32-001 \
  --code "print('hello from device')"
```

Code from file:

```bash
uv run --project edge python edge/tools/run_dev_command.py \
  --api-url http://192.168.68.60:5228 \
  --device-id esp32-001 \
  --code-file my_test_script.py
```

Code from stdin:

```bash
echo "import gc; print(gc.mem_free())" | uv run --project edge python edge/tools/run_dev_command.py \
  --api-url http://192.168.68.60:5228 \
  --device-id esp32-001
```

Custom credentials:

```bash
uv run --project edge python edge/tools/run_dev_command.py \
  --api-url http://192.168.68.60:5228 \
  --device-id esp32-001 \
  --username Admin --password mypassword \
  --code "print('hi')"
```

Adjust polling and timeout:

```bash
uv run --project edge python edge/tools/run_dev_command.py \
  --api-url http://192.168.68.60:5228 \
  --device-id esp32-001 \
  --code "print('slow')" \
  --timeout-ms 30000 \
  --poll-interval 5 \
  --max-polls 10
```

Returning structured data (set `result` variable in your code):

```bash
uv run --project edge python edge/tools/run_dev_command.py \
  --api-url http://192.168.68.60:5228 \
  --device-id esp32-001 \
  --code "import gc; gc.collect(); result = {'free': gc.mem_free(), 'alloc': gc.mem_alloc()}"
```

The response will show both `stdout` (from `print()`) and `data` (from `result` variable).

Auth flow:

- The tool authenticates via `POST /api/admin/auth/token` with `--username` / `--password` to get a JWT.
- Enqueue and result polling use `Authorization: Bearer <token>` against `/api/admin/dev-commands`.
- Device credentials (`X-Device-ID` / `X-Api-Key`) are not needed by the operator.
