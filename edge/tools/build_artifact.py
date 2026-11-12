#!/usr/bin/env python3
"""Build an OTA artifact from the current edge source tree.

Modules are precompiled to .mpy with mpy-cross unless --source is given. Run it
through uv so mpy-cross (an edge dev dependency) is available.

Usage:
  uv run --project edge python edge/tools/build_artifact.py --platform esp32 --version 1.0.0
  uv run --project edge python edge/tools/build_artifact.py --platform esp32 --version 1.0.0 --out api/artifacts
  uv run --project edge python edge/tools/build_artifact.py --platform esp32 --version 1.0.0 --source
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

# Entry points MicroPython runs directly by name; they must stay as source.
_ENTRY_POINTS = ("boot.py", "main.py")

# Compiled with the rest of the release and listed first, so the updater and the
# installer can import it to check the firmware loads this release's .mpy files.
PROBE_PATH = "mpy_probe.py"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _require_mpy_cross():
    try:
        import mpy_cross
    except ImportError as exc:
        raise SystemExit(
            "mpy-cross is not installed. Run with `uv run --project edge python edge/tools/build_artifact.py ...`, "
            "or pass --source to ship uncompiled .py files."
        ) from exc
    return mpy_cross


def _compile_mpy(src: Path, dst: Path, rel_path: str) -> None:
    """Compile src to bytecode-only .mpy (no -march, so it loads on any port)."""
    mpy_cross = _require_mpy_cross()
    mpy_cross.fix_perms()
    # -s embeds the release path instead of the local absolute path, for tracebacks.
    result = subprocess.run(
        [mpy_cross.mpy_cross, "-s", rel_path, "-o", str(dst), str(src)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"mpy-cross failed for {rel_path}: {result.stderr.strip()}")


def _collect_files(root: Path, platform: str) -> dict[str, Path]:
    """Return {relative_artifact_path: absolute_source_path} for all deployable files."""
    edge = root / "edge"
    plat_src = edge / "platforms" / platform / "src"
    shared = edge / "shared"
    plat_hal = edge / "platforms" / platform / "hal"

    files: dict[str, Path] = {}

    # .mpy compatibility probe; first, so an incompatible release fails before the rest downloads.
    files[PROBE_PATH] = shared / "mpy_probe.py"

    # Top-level entry points
    files["boot.py"] = plat_src / "boot.py"
    files["main.py"] = plat_src / "main.py"
    files["config.json"] = plat_src / "config.json"

    # edge/__init__.py
    files["edge/__init__.py"] = edge / "__init__.py"

    # edge/platforms/__init__.py + platform init + platform HAL
    files["edge/platforms/__init__.py"] = edge / "platforms" / "__init__.py"
    files[f"edge/platforms/{platform}/__init__.py"] = edge / "platforms" / platform / "__init__.py"
    _add_dir(plat_hal, edge / "platforms" / platform / "hal", f"edge/platforms/{platform}/hal", files)

    # edge/shared/__init__.py + app + hal
    files["edge/shared/__init__.py"] = shared / "__init__.py"
    _add_dir(shared / "app", shared / "app", "edge/shared/app", files)
    _add_dir(shared / "hal", shared / "hal", "edge/shared/hal", files)

    return files


def _add_dir(src_dir: Path, base: Path, prefix: str, out: dict[str, Path]) -> None:
    for item in sorted(src_dir.rglob("*")):
        if "__pycache__" in item.parts or item.suffix == ".pyc" or not item.is_file():
            continue
        rel = item.relative_to(base)
        key = f"{prefix}/{rel.as_posix()}"
        out[key] = item


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def build(platform: str, version: str, out_root: Path, compile_mpy: bool = False) -> Path:
    if compile_mpy:
        _require_mpy_cross()  # fail before writing anything
    root = _project_root()
    artifact_dir = out_root / platform / version
    artifact_dir.mkdir(parents=True, exist_ok=True)

    files = _collect_files(root, platform)
    manifest_items: list[dict] = []

    for rel_path, src_path in files.items():
        if not src_path.exists():
            print(f"  SKIP (not found): {rel_path}")
            continue
        # Empty files (package __init__.py) are smaller as source than as .mpy.
        compile_file = (
            compile_mpy
            and rel_path.endswith(".py")
            and rel_path not in _ENTRY_POINTS
            and src_path.stat().st_size > 0
        )
        if compile_file:
            rel_path = rel_path[: -len(".py")] + ".mpy"
        dst = artifact_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        if compile_file:
            _compile_mpy(src_path, dst, rel_path[: -len(".mpy")] + ".py")
        else:
            shutil.copy2(src_path, dst)
        file_hash = _sha256(dst)
        manifest_items.append({"path": rel_path, "hash": file_hash})
        print(f"  + {rel_path}")

    manifest = {"version": version, "manifest": manifest_items}
    manifest_path = artifact_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote manifest.json ({len(manifest_items)} files) -> {manifest_path}")
    return artifact_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a HomeIOT OTA artifact.")
    parser.add_argument("--platform", default="esp32", help="Target platform (default: esp32)")
    parser.add_argument("--version", required=True, help="Artifact version (e.g. 1.0.0)")
    parser.add_argument(
        "--out",
        default="api/artifacts",
        help="Output root directory relative to project root (default: api/artifacts)",
    )
    parser.add_argument(
        "--source",
        action="store_true",
        help="Ship modules as .py source instead of precompiled .mpy (larger, for debugging)",
    )
    args = parser.parse_args()

    root = _project_root()
    out_root = (root / args.out).resolve()
    compile_mpy = not args.source
    print(f"Building artifact: platform={args.platform}, version={args.version}, compiled={compile_mpy}")
    print(f"Output: {out_root}\n")
    build(args.platform, args.version, out_root, compile_mpy=compile_mpy)


if __name__ == "__main__":
    main()
