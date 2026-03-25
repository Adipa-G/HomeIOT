#!/usr/bin/env python3
"""Build an OTA artifact from the current edge source tree.

Usage:
  python edge/tools/build_artifact.py --platform esp32 --version 1.0.0
  python edge/tools/build_artifact.py --platform esp32 --version 1.0.0 --out api/artifacts
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _collect_files(root: Path, platform: str) -> dict[str, Path]:
    """Return {relative_artifact_path: absolute_source_path} for all deployable files."""
    edge = root / "edge"
    plat_src = edge / "platforms" / platform / "src"
    shared = edge / "shared"
    plat_hal = edge / "platforms" / platform / "hal"

    files: dict[str, Path] = {}

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


def build(platform: str, version: str, out_root: Path) -> Path:
    root = _project_root()
    artifact_dir = out_root / platform / version
    artifact_dir.mkdir(parents=True, exist_ok=True)

    files = _collect_files(root, platform)
    manifest_items: list[dict] = []

    for rel_path, src_path in files.items():
        if not src_path.exists():
            print(f"  SKIP (not found): {rel_path}")
            continue
        dst = artifact_dir / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dst)
        file_hash = _sha256(src_path)
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
    args = parser.parse_args()

    root = _project_root()
    out_root = (root / args.out).resolve()
    print(f"Building artifact: platform={args.platform}, version={args.version}")
    print(f"Output: {out_root}\n")
    build(args.platform, args.version, out_root)


if __name__ == "__main__":
    main()
