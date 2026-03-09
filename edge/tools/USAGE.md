# Edge Tools Usage

This folder provides two tools:

1. `provision_config.py` - generates a per-device `config.json`
2. `deploy_device.py` - deploys runtime files to a MicroPython device

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
