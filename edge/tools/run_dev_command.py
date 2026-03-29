#!/usr/bin/env python3
"""Operator-side tool: send arbitrary Python code to a device for remote execution.

The code runs on the device via exec() inside a sandboxed scope — nothing is
written to the device filesystem. This is the interactive development environment
for testing module logic before deploying it.

Usage examples
--------------
# Inline one-liner
python edge/tools/run_dev_command.py \
    --api-url http://192.168.68.60:5228 \
    --device-id esp32-001 \
    --code "print('hello from device')"

# Read code from a .py file
python edge/tools/run_dev_command.py \
    --api-url http://192.168.68.60:5228 \
    --device-id esp32-001 \
    --code-file my_test_script.py

# Read code from stdin (custom credentials)
echo "import gc; print(gc.mem_free())" | python edge/tools/run_dev_command.py \\
    --api-url http://192.168.68.60:5228 \
    --device-id esp32-001 \
    --username Admin --password 123

Example scripts you can send
-----------------------------
# Check free heap memory
import gc; gc.collect(); print("free:", gc.mem_free(), "alloc:", gc.mem_alloc())

# Read all readable GPIO pin states
from machine import Pin
for n in [0,2,4,5,12,13,14,15,18,19,21,22,23,25,26,27,32,33,34,35]:
    try:
        print("GPIO{}: {}".format(n, Pin(n, Pin.IN).value()))
    except Exception as e:
        print("GPIO{}: err({})".format(n, e))

# Show filesystem contents and sizes
import os
def ls(path="", indent=0):
    for name in os.listdir(path or "/"):
        full = (path + "/" + name).lstrip("/")
        try:
            stat = os.stat(full)
            if stat[0] & 0x4000:
                print(" " * indent + name + "/")
                ls(full, indent + 2)
            else:
                print(" " * indent + "{} ({} bytes)".format(name, stat[6]))
        except Exception as e:
            print(" " * indent + name + " (err: {})".format(e))
ls()

# Check boot_state.json
import json; print(json.dumps(json.loads(open("boot_state.json").read()), indent=2))
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send Python code to a device for remote execution via the dev-command API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--api-url",   required=True,  help="API base URL, e.g. http://192.168.68.60:5228")
    parser.add_argument("--device-id", required=True,  help="Target device ID, e.g. esp32-001")
    parser.add_argument("--username",  default="Admin", help="Admin username (default: Admin)")
    parser.add_argument("--password",  default="123",   help="Admin password (default: 123)")
    parser.add_argument("--code",      default=None,   help="Python code string to execute on the device")
    parser.add_argument("--code-file", default=None,   help="Path to a .py file whose contents are sent as the command")
    parser.add_argument("--timeout-ms",   type=int, default=10000, help="Execution timeout on device (ms, default 10000)")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Seconds between result polls (default 2)")
    parser.add_argument("--max-polls",     type=int,   default=20,  help="Max result poll attempts (default 20)")
    parser.add_argument("--force-rerun",   action="store_true",     help="Set forceRerun=true so the device re-executes even if it saw this hash")
    args = parser.parse_args()

    # --- Resolve code ---
    if args.code_file:
        with open(args.code_file, "r", encoding="utf-8") as f:
            code = f.read()
    elif args.code:
        code = args.code
    elif not sys.stdin.isatty():
        code = sys.stdin.read()
    else:
        parser.error("Provide --code, --code-file, or pipe code via stdin.")
        return

    headers = {
        "Content-Type": "application/json",
    }

    # --- Authenticate (get JWT) ---
    token = _get_jwt_token(args.api_url, args.username, args.password)
    headers["Authorization"] = f"Bearer {token}"

    # --- Enqueue command ---
    body = json.dumps({
        "device_id":  args.device_id,
        "code":       code,
        "timeout_ms": args.timeout_ms,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{args.api_url}/api/admin/dev-commands",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            enqueue_resp = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Failed to enqueue command: HTTP {e.code}\n{e.read().decode()}", file=sys.stderr)
        sys.exit(1)

    command_id = enqueue_resp.get("command_id") or enqueue_resp.get("commandId")
    print(f"Queued command {command_id} → device {args.device_id}")
    print(f"Waiting for result (device polls every dev_poll_interval_ms in development mode)...\n")

    # --- Poll for result ---
    result_url = f"{args.api_url}/api/admin/dev-commands/{command_id}/result"
    for attempt in range(1, args.max_polls + 1):
        time.sleep(args.poll_interval)
        result_req = urllib.request.Request(result_url, headers=headers)
        try:
            with urllib.request.urlopen(result_req) as resp:
                result = json.loads(resp.read())
                _print_result(result)
                sys.exit(0 if result.get("exit_code", 0) == 0 else result.get("exit_code", 1))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print(f"  [{attempt}/{args.max_polls}] No result yet...")
            else:
                print(f"  Error polling result: HTTP {e.code}", file=sys.stderr)
                sys.exit(1)

    print(f"\nTimed out after {args.max_polls} polls. The device may not be in development mode or offline.")
    sys.exit(2)


def _get_jwt_token(api_url: str, username: str, password: str) -> str:
    body = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        f"{api_url}/api/admin/auth/token",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            return data["token"]
    except urllib.error.HTTPError as e:
        print(f"Authentication failed: HTTP {e.code}\n{e.read().decode()}", file=sys.stderr)
        sys.exit(1)


def _print_result(result: dict) -> None:
    status   = result.get("status", "?")
    exit_code = result.get("exit_code", 0)
    elapsed  = result.get("elapsed_ms", "?")
    stdout   = result.get("stdout") or ""
    stderr   = result.get("stderr") or ""
    data     = result.get("data")

    print(f"{'─' * 50}")
    print(f"  status    : {status}")
    print(f"  exit_code : {exit_code}")
    print(f"  elapsed   : {elapsed} ms")
    if stdout:
        print(f"\n── stdout ──────────────────────────────────────")
        print(stdout)
    if data is not None:
        print(f"\n── data ────────────────────────────────────────")
        print(json.dumps(data, indent=2))
    if stderr:
        print(f"\n── stderr ──────────────────────────────────────")
        print(stderr, file=sys.stderr)
    print(f"{'─' * 50}")


if __name__ == "__main__":
    main()
