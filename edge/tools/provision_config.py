#!/usr/bin/env python3
"""Generate a device config.json for HomeIOT edge deployments.

Usage examples:
  python edge/tools/provision_config.py --platform esp32 --device-id esp32-001 --api-url http://192.168.1.10:8000 --api-key secret --wifi-ssid MyWiFi --wifi-password pass
  python edge/tools/provision_config.py --platform pico --device-id pico-001 --api-url http://192.168.1.10:8000 --api-key secret --wifi-ssid MyWiFi --wifi-password pass --output edge/tools/generated/pico-lab.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from edge.shared.app.secret_crypto import SCHEME, encrypt_secret


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _template_path(root: Path, platform: str) -> Path:
    return root / "edge" / "platforms" / platform / "src" / "config.json"


def _default_output_path(root: Path, platform: str) -> Path:
    return root / "edge" / "tools" / "generated" / f"{platform}-config.json"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a deployment config.json for a specific device")
    parser.add_argument("--platform", required=True, choices=["esp32", "pico"])
    parser.add_argument("--device-id", required=True)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--wifi-ssid", required=True)
    parser.add_argument("--wifi-password", required=True)
    parser.add_argument("--heartbeat-interval-ms", type=int, default=30000)
    parser.add_argument("--max-boot-attempts", type=int, default=3)
    parser.add_argument("--current-version", default="0.0.0")
    parser.add_argument(
        "--output",
        help="output config path (default: edge/tools/generated/<platform>-config.json)",
    )
    parser.add_argument(
        "--from-template",
        help="optional template config path (default: edge/platforms/<platform>/src/config.json)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="allow overwriting existing output file",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = _project_root()

    template_path = Path(args.from_template).resolve() if args.from_template else _template_path(root, args.platform)
    output_path = Path(args.output).resolve() if args.output else _default_output_path(root, args.platform)

    if not template_path.exists():
        print(f"[error] Template does not exist: {template_path}")
        return 1

    if output_path.exists() and not args.overwrite:
        print(f"[error] Output already exists: {output_path}")
        print("Use --overwrite to replace it.")
        return 1

    try:
        template = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[error] Invalid JSON in template {template_path}: {exc}")
        return 1

    template["device_id"] = args.device_id
    template["api_url"] = args.api_url.rstrip("/")
    template.pop("api_key", None)
    template.pop("wifi_password", None)
    template["api_key_enc"] = encrypt_secret(args.api_key, args.device_id, "api_key")
    template["wifi_ssid"] = args.wifi_ssid
    template["wifi_password_enc"] = encrypt_secret(args.wifi_password, args.device_id, "wifi_password")
    template["heartbeat_interval_ms"] = int(args.heartbeat_interval_ms)
    template["max_boot_attempts"] = int(args.max_boot_attempts)
    template["current_version"] = args.current_version
    if not isinstance(template.get("logging"), dict):
        template["logging"] = {
            "enabled_uplink": True,
            "buffer_max_bytes": 4096,
            "flush_interval_ms": 30000,
            "min_level": "INFO",
        }
    template["security"] = {
        "binding": "unique_id",
        "scheme": SCHEME,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")

    print("[ok] Config generated")
    print(f"  platform: {args.platform}")
    print(f"  output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
