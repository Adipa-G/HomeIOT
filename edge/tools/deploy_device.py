#!/usr/bin/env python3
"""Deploy HomeIOT edge runtime files to a MicroPython device via mpremote.

Usage examples:
  python edge/tools/deploy_device.py --platform esp32 --port auto
  python edge/tools/deploy_device.py --platform esp32 --verify-only
  python edge/tools/deploy_device.py --platform pico --force-config --no-reset
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


REQUIRED_CONFIG_KEYS = {
    "device_id",
    "api_url",
    "api_key",
    "wifi_ssid",
    "wifi_password",
    "heartbeat_interval_ms",
    "max_boot_attempts",
}


class DeployError(RuntimeError):
    pass


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _paths_for_platform(root: Path, platform: str) -> dict[str, Path]:
    platform_src = root / "edge" / "platforms" / platform / "src"
    return {
        "edge_dir": root / "edge",
        "boot": platform_src / "boot.py",
        "main": platform_src / "main.py",
        "config_template": platform_src / "config.json",
    }


def _check_mpremote_available() -> None:
    if shutil.which("mpremote") is None:
        raise DeployError(
            "mpremote is not available in PATH. Install it with: pip install mpremote"
        )


def _load_and_validate_config(config_path: Path) -> None:
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DeployError(f"Invalid JSON in {config_path}: {exc}") from exc

    missing = sorted(REQUIRED_CONFIG_KEYS - set(payload.keys()))
    if missing:
        missing_text = ", ".join(missing)
        raise DeployError(f"Config template missing required keys: {missing_text}")


def _require_local_files(paths: dict[str, Path]) -> None:
    for key, path in paths.items():
        if not path.exists():
            raise DeployError(f"Required path for {key} does not exist: {path}")


def _run_mpremote(port: str, args: Iterable[str], phase: str) -> subprocess.CompletedProcess[str]:
    cmd = ["mpremote", "connect", port, *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or "unknown mpremote error"
        raise DeployError(f"{phase} failed: {details}")
    return result


def _device_has_config(port: str) -> bool:
    script = (
        "import os\n"
        "try:\n"
        "    os.stat('config.json')\n"
        "    print('EXISTS')\n"
        "except OSError:\n"
        "    print('MISSING')\n"
    )
    result = _run_mpremote(port, ["exec", script], "config existence check")
    return "EXISTS" in result.stdout


def _verify_remote_imports(port: str, platform: str) -> None:
    script = (
        "import edge.shared.app.config\n"
        "import edge.shared.app.boot_manager\n"
        f"import edge.platforms.{platform}.hal.filesystem\n"
        f"import edge.platforms.{platform}.hal.network\n"
        "print('IMPORTS_OK')\n"
    )
    result = _run_mpremote(port, ["exec", script], "remote import verification")
    if "IMPORTS_OK" not in result.stdout:
        raise DeployError("remote import verification failed: marker not found")


def _copy_runtime_essentials(port: str, paths: dict[str, Path]) -> None:
    _run_mpremote(port, ["cp", "-r", str(paths["edge_dir"]), ":/"], "copy edge package")
    _run_mpremote(port, ["cp", str(paths["boot"]), ":/boot.py"], "copy boot.py")
    _run_mpremote(port, ["cp", str(paths["main"]), ":/main.py"], "copy main.py")


def _maybe_copy_config(port: str, config_path: Path, force_config: bool) -> str:
    exists = _device_has_config(port)
    if exists and not force_config:
        return "preserved-existing"

    _run_mpremote(port, ["cp", str(config_path), ":/config.json"], "copy config.json")
    return "overwritten" if exists else "created"


def _maybe_reset(port: str, no_reset: bool) -> bool:
    if no_reset:
        return False
    _run_mpremote(port, ["reset"], "device reset")
    return True


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy edge runtime files to a MicroPython device")
    parser.add_argument("--platform", required=True, choices=["esp32", "pico"])
    parser.add_argument("--port", default="auto", help="mpremote port target (default: auto)")
    parser.add_argument(
        "--force-config",
        action="store_true",
        help="overwrite existing config.json on device",
    )
    parser.add_argument(
        "--config-file",
        help="path to config json to upload when applying config policy (default: platform template)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="run preflight and remote import checks only; do not upload files",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="skip reset after successful deployment",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    root = _project_root()
    paths = _paths_for_platform(root, args.platform)
    config_path = Path(args.config_file).resolve() if args.config_file else paths["config_template"]

    try:
        print("[1/5] Preflight checks")
        _check_mpremote_available()
        _require_local_files(paths)
        if not config_path.exists():
            raise DeployError(f"Configured config file does not exist: {config_path}")
        _load_and_validate_config(config_path)

        if args.verify_only:
            print("[2/5] Verify-only mode: checking remote imports on existing deployment")
            _verify_remote_imports(args.port, args.platform)
            print("[ok] Verify-only checks passed")
            return 0

        print("[2/5] Upload runtime essentials")
        _copy_runtime_essentials(args.port, paths)

        print("[3/5] Apply config policy")
        config_status = _maybe_copy_config(args.port, config_path, args.force_config)

        print("[4/5] Verify remote imports")
        _verify_remote_imports(args.port, args.platform)

        print("[5/5] Finalize")
        did_reset = _maybe_reset(args.port, args.no_reset)

        print("[ok] Deployment completed")
        print(f"  platform: {args.platform}")
        print(f"  port: {args.port}")
        print(f"  config: {config_status}")
        print(f"  config-file: {config_path}")
        print(f"  reset: {'yes' if did_reset else 'no'}")
        return 0
    except DeployError as exc:
        print(f"[error] {exc}")
        print("Recovery tips:")
        print("  1) Re-run with --verify-only to validate existing deployment imports")
        print("  2) If config is invalid/missing, re-run with --force-config")
        print("  3) Confirm serial port and USB cable, then retry with --port <device>")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
