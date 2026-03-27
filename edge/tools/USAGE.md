# Edge Tools Usage

This folder provides four tools:

1. `provision_config.py` - generates a per-device `config.json`
2. `deploy_device.py` - deploys runtime files to a MicroPython device
3. `build_artifact.py` - builds an OTA artifact from the current edge source tree
4. `run_dev_command.py` - sends arbitrary Python code to a device for remote execution

Secrets policy:

- `provision_config.py` always encrypts `api_key` and `wifi_password` using device unique id binding.
- Runtime still supports plaintext secrets in `config.json` if you manually maintain them.
- `deploy_device.py` accepts both plaintext and encrypted config formats.

API route policy:

- Endpoint paths are centralized in shared code and are not meant to be customized in config.
- Logging uplink uses the shared logs route constant.

## Tool 1: provision_config.py

Generate a device-specific config file:

```bash
python edge/tools/provision_config.py \
  --platform esp32 \
  --device-id esp32-001 \
  --api-url http://192.168.1.10:8000 \
  --api-key YOUR_DEVICE_KEY \
  --wifi-ssid YOUR_WIFI \
  --wifi-password YOUR_WIFI_PASSWORD
```

Generated config stores encrypted fields:

- `api_key_enc`
- `wifi_password_enc`

Default output:

- `edge/tools/generated/esp32-config.json`
- `edge/tools/generated/pico-config.json`

Overwrite existing generated output:

```bash
python edge/tools/provision_config.py ... --overwrite
```

Use a custom output path:

```bash
python edge/tools/provision_config.py ... --output edge/tools/generated/lab-node-01.json
```

## Tool 2: deploy_device.py

Deploy runtime essentials (`edge/`, `boot.py`, `main.py`) to a connected device:

```bash
python edge/tools/deploy_device.py --platform esp32 --port auto
```

Safe config policy by default:

- Existing device `config.json` is preserved
- `config.json` is only uploaded if missing
- When `--force-config` overwrites the device config, the previous copy is backed up as `config_prev.json`
- `--config-only` skips runtime file upload and marks the update as config-only for selective rollback

Force overwrite device config:

```bash
python edge/tools/deploy_device.py --platform esp32 --port auto --force-config
```

Use custom config file for upload policy:

```bash
python edge/tools/deploy_device.py \
  --platform esp32 \
  --port auto \
  --config-file edge/tools/generated/esp32-config.json \
  --force-config
```

Verify deployment imports only (no writes):

```bash
python edge/tools/deploy_device.py --platform esp32 --verify-only
```

Skip reset after deploy:

```bash
python edge/tools/deploy_device.py --platform esp32 --no-reset
```

Config-only update with rollback metadata:

```bash
python edge/tools/deploy_device.py \
  --platform esp32 \
  --port auto \
  --config-file edge/tools/generated/esp32-config.json \
  --force-config \
  --config-only
```

## Common Combinations (2-tool workflows)

1. Provision once, deploy with forced config

```bash
python edge/tools/provision_config.py \
  --platform esp32 \
  --device-id esp32-001 \
  --api-url http://192.168.1.10:8000 \
  --api-key YOUR_DEVICE_KEY \
  --wifi-ssid YOUR_WIFI \
  --wifi-password YOUR_WIFI_PASSWORD

python edge/tools/deploy_device.py \
  --platform esp32 \
  --port auto \
  --config-file edge/tools/generated/esp32-config.json \
  --force-config
```

2. Provision multiple devices, deploy each with different config

```bash
python edge/tools/provision_config.py ... --device-id esp32-001 --output edge/tools/generated/esp32-001.json
python edge/tools/provision_config.py ... --device-id esp32-002 --output edge/tools/generated/esp32-002.json

python edge/tools/deploy_device.py --platform esp32 --config-file edge/tools/generated/esp32-001.json --force-config
python edge/tools/deploy_device.py --platform esp32 --config-file edge/tools/generated/esp32-002.json --force-config
```

3. Code-only update, keep device credentials

```bash
python edge/tools/deploy_device.py --platform esp32 --port auto
```

4. Dry-run style connection/import check before rollout

```bash
python edge/tools/deploy_device.py --platform esp32 --verify-only
```

5. Config-only update with selective rollback

```bash
python edge/tools/deploy_device.py --platform esp32 --config-file edge/tools/generated/esp32-config.json --force-config --config-only
```

## Notes

- `deploy_device.py` requires `mpremote` installed and available in PATH.
- `--platform` supports `esp32` and `pico`.
- `--config-file` is validated before any upload begins.
- Provisioned encrypted secrets are bound to the provided `--device-id` value.
- `current_version` in the generated config is the config version marker used by the runtime rollback flow.
- Selective rollback now restores only the surfaces marked as changed by the update path.

## Tool 3: build_artifact.py

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
- `config.json` in the artifact should use placeholder values (`"replace-with-device-id"`, `"replace-with-api-url"`) so device-specific values are preserved during OTA merge.

## Tool 4: run_dev_command.py

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
