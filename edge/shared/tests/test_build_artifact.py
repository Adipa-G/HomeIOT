import hashlib
import json
from pathlib import Path

import pytest

from edge.tools import build_artifact

ROOT = Path(__file__).resolve().parents[3]
BUNDLE = json.loads((ROOT / "edge" / "bootstrap" / "bundle.json").read_text(encoding="utf-8"))


def _manifest(artifact_dir: Path) -> dict[str, str]:
    data = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
    return {item["path"]: item["hash"] for item in data["manifest"]}


def test_source_build_ships_source_only(tmp_path: Path):
    artifact_dir = build_artifact.build("esp32", "1.0.0", tmp_path, compile_mpy=False)

    paths = _manifest(artifact_dir)
    assert not [p for p in paths if p.endswith(".mpy")]
    assert "edge/shared/app/control_loop.py" in paths


@pytest.mark.parametrize("platform", ["esp32", "pico"])
def test_compiled_build_compiles_everything_except_entry_points(tmp_path: Path, platform: str):
    artifact_dir = build_artifact.build(platform, "1.0.0", tmp_path, compile_mpy=True)

    paths = _manifest(artifact_dir)
    source = sorted(p for p in paths if p.endswith(".py") and not p.endswith("__init__.py"))
    assert source == ["boot.py", "main.py"]
    assert "edge/shared/app/boot_manager.mpy" in paths
    assert "edge/shared/app/updater.mpy" in paths
    assert f"edge/platforms/{platform}/hal/network.mpy" in paths


def test_compiled_build_ships_probe_first(tmp_path: Path):
    artifact_dir = build_artifact.build("esp32", "1.0.0", tmp_path, compile_mpy=True)

    data = json.loads((artifact_dir / "manifest.json").read_text(encoding="utf-8"))
    assert data["manifest"][0]["path"] == "mpy_probe.mpy"
    assert (artifact_dir / "mpy_probe.mpy").read_bytes()[:2] == b"M\x06"


def test_compiled_build_manifest_hashes_match_shipped_files(tmp_path: Path):
    artifact_dir = build_artifact.build("esp32", "1.0.0", tmp_path, compile_mpy=True)

    for rel_path, expected in _manifest(artifact_dir).items():
        actual = hashlib.sha256((artifact_dir / rel_path).read_bytes()).hexdigest()
        assert actual == expected, rel_path


def test_compiled_modules_are_portable_bytecode_without_local_paths(tmp_path: Path):
    artifact_dir = build_artifact.build("esp32", "1.0.0", tmp_path, compile_mpy=True)

    data = (artifact_dir / "edge/shared/app/control_loop.mpy").read_bytes()
    # Header: 'M', .mpy major version 6, no native architecture (loads on any port).
    assert data[0:1] == b"M"
    assert data[1] == 6
    assert data[2] >> 2 == 0
    assert b"edge/shared/app/control_loop.py" in data
    assert str(ROOT).encode() not in data


def test_compiled_build_keeps_empty_package_files_as_source(tmp_path: Path):
    artifact_dir = build_artifact.build("esp32", "1.0.0", tmp_path, compile_mpy=True)

    paths = _manifest(artifact_dir)
    assert "edge/platforms/esp32/__init__.py" in paths
    for rel_path in paths:
        if rel_path.endswith(".mpy"):
            assert (artifact_dir / rel_path).stat().st_size > 0
        if rel_path.endswith("__init__.py") and rel_path not in BUNDLE["release_files"]:
            assert (artifact_dir / rel_path).stat().st_size == 0, rel_path


def test_rebuilding_a_version_removes_files_from_the_previous_build(tmp_path: Path):
    # A source build then a compiled build of the same version must not leave
    # interfaces.py next to interfaces.mpy: MicroPython would load the stale .py.
    build_artifact.build("pico", "1.0.0", tmp_path, compile_mpy=False)
    artifact_dir = build_artifact.build("pico", "1.0.0", tmp_path, compile_mpy=True)

    assert (artifact_dir / "edge/shared/hal/interfaces.mpy").exists()
    assert not (artifact_dir / "edge/shared/hal/interfaces.py").exists()
    shipped = {p.relative_to(artifact_dir).as_posix() for p in artifact_dir.rglob("*") if p.is_file()}
    assert shipped == set(_manifest(artifact_dir)) | {"manifest.json"}


def test_build_refuses_to_overwrite_a_folder_that_is_not_a_release(tmp_path: Path):
    unrelated = tmp_path / "pico" / "1.0.0"
    unrelated.mkdir(parents=True)
    (unrelated / "notes.txt").write_text("keep me", encoding="utf-8")

    with pytest.raises(SystemExit, match="not a release build"):
        build_artifact.build("pico", "1.0.0", tmp_path, compile_mpy=True)

    assert (unrelated / "notes.txt").read_text(encoding="utf-8") == "keep me"
