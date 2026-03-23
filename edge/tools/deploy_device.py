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
import tempfile
import time
from pathlib import Path
from typing import Iterable


REQUIRED_CONFIG_KEYS = {
    "device_id",
    "api_url",
    "wifi_ssid",
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

    _validate_placeholder_value(payload, "wifi_ssid")
    _validate_secret_payload(payload, "api_key")
    _validate_secret_payload(payload, "wifi_password")
    _validate_logging_payload(payload.get("logging"))


def _validate_placeholder_value(payload: dict, key_name: str) -> None:
    value = payload.get(key_name)
    if value is None:
        return
    if not isinstance(value, str) or not value.strip():
        raise DeployError(f"Config field must be a non-empty string: {key_name}")
    if value.strip().lower().startswith("replace-with-"):
        raise DeployError(f"Config field still contains placeholder value: {key_name}")


def _validate_secret_payload(payload: dict, key_name: str) -> None:
    if key_name in payload:
        _validate_placeholder_value(payload, key_name)
        return

    enc_key = key_name + "_enc"
    encrypted_payload = payload.get(enc_key)
    if encrypted_payload is None:
        raise DeployError(f"Config missing both plaintext and encrypted secret for: {key_name}")
    if not isinstance(encrypted_payload, dict):
        raise DeployError(f"Encrypted secret payload must be an object: {enc_key}")

    required_enc_keys = {"scheme", "nonce", "ciphertext", "tag"}
    missing_enc = sorted(required_enc_keys - set(encrypted_payload.keys()))
    if missing_enc:
        missing_text = ", ".join(missing_enc)
        raise DeployError(f"Encrypted secret payload missing keys for {enc_key}: {missing_text}")


def _validate_logging_payload(payload) -> None:
    if payload is None:
        return
    if not isinstance(payload, dict):
        raise DeployError("logging config must be an object")

    if "buffer_max_bytes" in payload and int(payload["buffer_max_bytes"]) < 512:
        raise DeployError("logging.buffer_max_bytes must be >= 512")
    if "flush_interval_ms" in payload and int(payload["flush_interval_ms"]) < 1000:
        raise DeployError("logging.flush_interval_ms must be >= 1000")


def _require_local_files(paths: dict[str, Path]) -> None:
    for key, path in paths.items():
        if not path.exists():
            raise DeployError(f"Required path for {key} does not exist: {path}")


def _progress(step: int, total: int, label: str) -> None:
    print(f"  [{step}/{total}] {label}")


def _run_mpremote(port: str, args: Iterable[str], phase: str) -> subprocess.CompletedProcess[str]:
    args_list = list(args)
    cmd = ["mpremote", "connect", port, *args_list]

    # Large recursive copies can take a while on MicroPython links, so print a
    # heartbeat line periodically to show the deploy has not stalled.
    show_heartbeat = bool(args_list) and args_list[0] == "cp"
    start = time.monotonic()
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    next_tick = start + 2.0
    while process.poll() is None:
        if show_heartbeat and time.monotonic() >= next_tick:
            elapsed = int(time.monotonic() - start)
            print(f"     ... {phase} in progress ({elapsed}s)")
            next_tick += 2.0
        time.sleep(0.1)

    stdout, stderr = process.communicate()
    result = subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        details = stderr or stdout or "unknown mpremote error"
        raise DeployError(f"{phase} failed: {details}")

    if show_heartbeat:
        elapsed = time.monotonic() - start
        print(f"     ... {phase} done ({elapsed:.1f}s)")

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


def _backup_device_config(port: str) -> None:
    _run_mpremote(port, ["cp", ":/config.json", ":/config_prev.json"], "backup config.json")


def _mark_pending_config_update(port: str, config_version: str) -> None:
    script = (
        "import json\n"
        "try:\n"
        "    raw = open('boot_state.json', 'r').read()\n"
        "    state = json.loads(raw)\n"
        "except Exception:\n"
        "    state = {}\n"
        "state.setdefault('boot_count', 0)\n"
        "state.setdefault('boot_succeeded', False)\n"
        "state.setdefault('current_version', '0.0.0')\n"
        "state.setdefault('previous_version', None)\n"
        "state.setdefault('config_version', state.get('current_version', '0.0.0'))\n"
        "state.setdefault('previous_config_version', None)\n"
        "state['previous_config_version'] = state.get('config_version') or state.get('current_version')\n"
        f"state['config_version'] = {json.dumps(config_version)}\n"
        "state['boot_count'] = 0\n"
        "state['boot_succeeded'] = False\n"
        "state['pending_app_changed'] = False\n"
        "state['pending_config_changed'] = True\n"
        "open('boot_state.json', 'w').write(json.dumps(state))\n"
        "print('BOOT_STATE_UPDATED')\n"
    )
    result = _run_mpremote(port, ["exec", script], "mark pending config update")
    if "BOOT_STATE_UPDATED" not in result.stdout:
        raise DeployError("failed to mark pending config update")

def _verify_remote_imports(port: str, platform: str) -> None:
    script = (
        "import edge.shared.app.endpoints\n"
        "import edge.shared.app.config\n"
        "import edge.shared.app.boot_manager\n"
        "import edge.shared.app.control_loop\n"
        "import edge.shared.app.module_runtime\n"
        f"import edge.platforms.{platform}.hal.filesystem\n"
        f"import edge.platforms.{platform}.hal.network\n"
        "print('IMPORTS_OK')\n"
    )
    result = _run_mpremote(port, ["exec", script], "remote import verification")
    if "IMPORTS_OK" not in result.stdout:
        raise DeployError("remote import verification failed: marker not found")


def _copy_runtime_essentials(port: str, paths: dict[str, Path], platform: str, root: Path) -> None:
    staging = _build_staging_tree(root, platform)
    try:
        staged_edge = staging / "edge"
        copies = [
            (staged_edge, ":/", f"edge/ (shared + {platform} HAL)"),
            (paths["boot"], ":/boot.py", "boot.py"),
            (paths["main"], ":/main.py", "main.py"),
        ]
        total = len(copies)
        for i, (src, dst, label) in enumerate(copies, 1):
            _progress(i, total, label)
            args = ["cp", "-r", str(src), dst] if src.is_dir() else ["cp", str(src), dst]
            _run_mpremote(port, args, f"copy {label}")
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _build_staging_tree(root: Path, platform: str) -> Path:
    """Return a temp directory containing only the files the device needs."""
    staging = Path(tempfile.mkdtemp(prefix="homeiot_deploy_"))
    edge_root = root / "edge"

    # edge/__init__.py
    _stage_file(edge_root / "__init__.py", staging / "edge" / "__init__.py")

    # edge/platforms/__init__.py  +  target platform only
    _stage_file(
        edge_root / "platforms" / "__init__.py",
        staging / "edge" / "platforms" / "__init__.py",
    )
    plat = edge_root / "platforms" / platform
    _stage_file(plat / "__init__.py", staging / "edge" / "platforms" / platform / "__init__.py")
    _stage_dir(plat / "hal", staging / "edge" / "platforms" / platform / "hal")

    # edge/shared  (app + hal only, no tests)
    shared = edge_root / "shared"
    _stage_file(shared / "__init__.py", staging / "edge" / "shared" / "__init__.py")
    _stage_dir(shared / "app", staging / "edge" / "shared" / "app")
    _stage_dir(shared / "hal", staging / "edge" / "shared" / "hal")

    return staging


def _stage_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _stage_dir(src: Path, dst: Path) -> None:
    """Recursively stage a directory, skipping __pycache__ and .pyc files."""
    for item in sorted(src.rglob("*")):
        if "__pycache__" in item.parts or item.suffix == ".pyc":
            continue
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def _maybe_copy_config(port: str, config_path: Path, force_config: bool, config_only: bool) -> str:
    exists = _device_has_config(port)
    if exists and not force_config:
        _progress(1, 1, "config.json preserved (use --force-config to overwrite)")
        return "preserved-existing"

    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    step_total = 3 if (config_only and exists) else (2 if exists else 1)
    current_step = 1

    if exists:
        _progress(current_step, step_total, "backing up existing config.json -> config_prev.json")
        _backup_device_config(port)
        current_step += 1

    _progress(current_step, step_total, f"uploading {config_path.name}")
    _run_mpremote(port, ["cp", str(config_path), ":/config.json"], "copy config.json")
    current_step += 1

    if config_only and exists:
        _progress(current_step, step_total, "marking pending config change in boot_state.json")
        _mark_pending_config_update(port, str(config_payload.get("current_version", "0.0.0")))

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
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="only update config.json; skip runtime file upload",
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

        if args.config_only:
            print("[2/5] Skipping runtime upload (--config-only)")
        else:
            print("[2/5] Upload runtime essentials (3 items)")
            _copy_runtime_essentials(args.port, paths, args.platform, root)

        print("[3/5] Apply config policy")
        config_status = _maybe_copy_config(args.port, config_path, args.force_config, args.config_only)

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
