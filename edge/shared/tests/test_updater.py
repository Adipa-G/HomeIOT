from pathlib import Path
import hashlib
import json
import sys
from collections.abc import Callable, Sequence
from typing import Any

from edge.shared.app.secret_crypto import encrypt_secret

import pytest

from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import Config
from edge.shared.app.updater import (
    PROBE_PATH,
    IncompatibleReleaseError,
    UpdateInfo,
    Updater,
    _StreamFrameReader,
    import_probe,
)
from edge.shared.hal.interfaces import IWatchdog
from edge.shared.tests.mocks.mock_filesystem import MockFileSystem
from edge.shared.tests.mocks.mock_http_client import MockHttpClient, MockStreamingResponse
from edge.shared.tests.mocks.mock_system import MockSystem


def _config():
    return Config(
        device_id="esp32-001",
        api_url="http://localhost:8000",
        api_key="secret",
        wifi_ssid="ssid",
        wifi_password="pass",
        heartbeat_interval_ms=1000,
        max_boot_attempts=3,
        current_version="1.0.0",
    )


_STREAM_URL = "http://localhost:8000/api/ota/stream?version=1.1.0"


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _build_ota_stream(files: Sequence[tuple[Any, ...]]) -> bytes:
    """Build an OTA stream payload as the server would send it.

    files: list of (rel_path, content_bytes) or (rel_path, content_bytes, hash_override)
    """
    out = bytearray()
    for entry in files:
        rel_path, content = entry[0], entry[1]
        h = entry[2] if len(entry) > 2 else _sha256_hex(content)
        out.extend(("HASH:" + h + "\n").encode())
        out.extend(("FILE:" + rel_path + "\n").encode())
        out.extend(("SIZE:" + str(len(content)) + "\n").encode())
        out.extend(content)
    out.extend(b"END\n")
    return bytes(out)


# ---------------------------------------------------------------------------
# OTA check tests
# ---------------------------------------------------------------------------

def test_check_returns_none_when_no_update():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    http.add_json_response(
        "GET",
        "http://localhost:8000/api/ota/check?version=1.0.0",
        200,
        {"available": False},
    )

    update = updater.check()

    assert update is None
    assert http.calls[0][1] == "http://localhost:8000/api/ota/check?version=1.0.0"
    assert http.calls[0][3]["X-Platform"] == "esp32"


def test_apply_downloads_and_swaps_version():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    fs.write_bytes("app/main.py", b"old-version")
    fs.write_text(
        "config.json",
        """
        {"device_id":"esp32-001","api_url":"http://localhost:8000","api_key":"old-secret","wifi_ssid":"ssid","wifi_password":"old-pass","heartbeat_interval_ms":1000,"max_boot_attempts":3,"current_version":"1.0.0"}
        """.strip(),
    )

    new_file = b"print('new-version')"
    # Staged config: placeholders for device secrets (should be preserved from active),
    # real values for non-secret fields (should be taken from the new release),
    # and a real api_url (should override the active value).
    new_config = b"{\"device_id\":\"replace-with-device-id\",\"api_url\":\"replace-with-api-url\",\"api_key\":\"replace-with-device-api-key\",\"wifi_ssid\":\"replace-with-ssid\",\"wifi_password\":\"replace-with-password\",\"heartbeat_interval_ms\":2000,\"max_boot_attempts\":4,\"current_version\":\"1.1.0\"}"

    stream_data = _build_ota_stream([("main.py", new_file), ("config.json", new_config)])
    http.add_stream_response(_STREAM_URL, stream_data)

    updater.apply(
        UpdateInfo(
            available=True,
            version="1.1.0",
            manifest=[
                {"path": "main.py", "hash": _sha256_hex(new_file), "size": len(new_file)},
                {"path": "config.json", "hash": _sha256_hex(new_config), "size": len(new_config)},
            ],
        )
    )

    assert fs.read_bytes("main.py") == new_file
    assert fs.read_bytes("app_prev/main.py") == b"old-version"
    merged_config = json.loads(fs.read_text("config.json"))
    assert merged_config["device_id"] == "esp32-001"            # placeholder → preserved from active
    assert merged_config["api_key"] == "old-secret"              # placeholder → preserved from active
    assert merged_config["wifi_password"] == "old-pass"          # placeholder → preserved from active
    assert merged_config["api_url"] == "http://localhost:8000"   # placeholder → preserved from active
    assert merged_config["heartbeat_interval_ms"] == 2000
    assert merged_config["max_boot_attempts"] == 4
    assert merged_config["current_version"] == "1.1.0"
    assert fs.read_text("config_prev.json").startswith("{\"device_id\":\"esp32-001\"")
    assert system.reset_calls == 1


def test_apply_preserves_enc_credentials_when_absent_from_staged():
    """Devices using encrypted credentials (api_key_enc / wifi_password_enc) must not
    lose those fields after OTA — the artifact template never contains enc objects."""
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    # Use properly encrypted fixtures so staged config validation (Config.load) can decrypt them.
    device_id = "esp32-001"
    api_key_enc = encrypt_secret("real-api-key", device_id, "api_key")
    wifi_password_enc = encrypt_secret("real-wifi-pass", device_id, "wifi_password")

    fs.write_bytes("app/main.py", b"old-version")
    fs.write_text(
        "config.json",
        json.dumps({
            "device_id": device_id,
            "api_url": "http://localhost:8000",
            "api_key_enc": api_key_enc,
            "wifi_ssid": "ssid",
            "wifi_password_enc": wifi_password_enc,
            "heartbeat_interval_ms": 1000,
            "max_boot_attempts": 3,
            "current_version": "1.0.0",
        }, separators=(",", ":")),
    )

    new_file = b"print('new-version')"
    new_config = json.dumps({
        "device_id": "replace-with-device-id",
        "api_url": "replace-with-api-url",
        "api_key": "replace-with-device-api-key",
        "wifi_ssid": "replace-with-ssid",
        "wifi_password": "replace-with-password",
        "heartbeat_interval_ms": 2000,
        "max_boot_attempts": 4,
        "current_version": "1.1.0",
    }, separators=(",", ":")).encode("utf-8")

    stream_data = _build_ota_stream([("main.py", new_file), ("config.json", new_config)])
    http.add_stream_response(_STREAM_URL, stream_data)

    updater.apply(
        UpdateInfo(
            available=True,
            version="1.1.0",
            manifest=[
                {"path": "main.py", "hash": _sha256_hex(new_file), "size": len(new_file)},
                {"path": "config.json", "hash": _sha256_hex(new_config), "size": len(new_config)},
            ],
        )
    )

    merged_config = json.loads(fs.read_text("config.json"))
    assert merged_config["device_id"] == device_id
    assert merged_config["api_url"] == "http://localhost:8000"
    assert "api_key" not in merged_config                          # placeholder removed, enc used instead
    assert merged_config["api_key_enc"] == api_key_enc             # absent from staged → preserved from active
    assert merged_config["wifi_password_enc"] == wifi_password_enc # absent from staged → preserved from active
    assert "wifi_password" not in merged_config                    # placeholder removed, enc used instead
    assert merged_config["heartbeat_interval_ms"] == 2000
    assert merged_config["current_version"] == "1.1.0"


def test_apply_encrypts_new_plaintext_credentials_from_release():
    """If a release ships a real plaintext api_key or wifi_password (key rotation),
    the device must encrypt it before writing — never store secrets as plaintext."""
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    device_id = "esp32-001"
    old_api_key_enc = encrypt_secret("old-api-key", device_id, "api_key")
    old_wifi_password_enc = encrypt_secret("old-wifi-pass", device_id, "wifi_password")

    fs.write_bytes("app/main.py", b"old-version")
    fs.write_text(
        "config.json",
        json.dumps({
            "device_id": device_id,
            "api_url": "http://localhost:8000",
            "api_key_enc": old_api_key_enc,
            "wifi_ssid": "ssid",
            "wifi_password_enc": old_wifi_password_enc,
            "heartbeat_interval_ms": 1000,
            "max_boot_attempts": 3,
            "current_version": "1.0.0",
        }, separators=(",", ":")),
    )

    new_file = b"print('new-version')"
    # Release ships a new plaintext api_key (key rotation) — device must encrypt it.
    new_config = json.dumps({
        "device_id": "replace-with-device-id",
        "api_url": "replace-with-api-url",
        "api_key": "rotated-api-key",
        "wifi_ssid": "replace-with-ssid",
        "wifi_password": "replace-with-password",
        "heartbeat_interval_ms": 2000,
        "max_boot_attempts": 4,
        "current_version": "1.1.0",
    }, separators=(",", ":")).encode("utf-8")

    stream_data = _build_ota_stream([("main.py", new_file), ("config.json", new_config)])
    http.add_stream_response(_STREAM_URL, stream_data)

    updater.apply(
        UpdateInfo(
            available=True,
            version="1.1.0",
            manifest=[
                {"path": "main.py", "hash": _sha256_hex(new_file), "size": len(new_file)},
                {"path": "config.json", "hash": _sha256_hex(new_config), "size": len(new_config)},
            ],
        )
    )

    merged_config = json.loads(fs.read_text("config.json"))
    assert "api_key" not in merged_config                   # plaintext must never be stored
    assert "api_key_enc" in merged_config                   # must be encrypted
    assert merged_config["api_key_enc"] != old_api_key_enc  # new key, new enc object
    # wifi_password was a placeholder → old enc preserved
    assert "wifi_password" not in merged_config
    assert merged_config["wifi_password_enc"] == old_wifi_password_enc
    assert merged_config["current_version"] == "1.1.0"


def test_apply_raises_on_hash_mismatch_and_cleans_staging():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    # Stream delivers file content whose hash doesn't match the HASH: header line.
    content = b"bad-content"
    stream_data = _build_ota_stream([("main.py", content, "0" * 64)])
    http.add_stream_response(_STREAM_URL, stream_data)

    with pytest.raises(ValueError):
        updater.apply(
            UpdateInfo(
                available=True,
                version="1.1.0",
                manifest=[{"path": "main.py", "hash": "0" * 64, "size": len(content)}],
            )
        )

    assert not fs.exists("app_staging")


def test_apply_raises_on_invalid_config_and_cleans_staging():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    fs.write_text(
        "config.json",
        """
        {"device_id":"esp32-001","api_url":"http://localhost:8000","api_key":"old-secret","wifi_ssid":"ssid","wifi_password":"old-pass","heartbeat_interval_ms":1000,"max_boot_attempts":3,"current_version":"1.0.0"}
        """.strip(),
    )

    new_file = b"print('new-version')"
    invalid_config = b"{\"device_id\":\"esp32-001\",\"api_url\":\"http://localhost:8000\"}"

    stream_data = _build_ota_stream([("main.py", new_file), ("config.json", invalid_config)])
    http.add_stream_response(_STREAM_URL, stream_data)

    with pytest.raises(ValueError):
        updater.apply(
            UpdateInfo(
                available=True,
                version="1.1.0",
                manifest=[
                    {"path": "main.py", "hash": _sha256_hex(new_file), "size": len(new_file)},
                    {"path": "config.json", "hash": _sha256_hex(invalid_config), "size": len(invalid_config)},
                ],
            )
        )

    assert fs.read_text("config.json").startswith("{\"device_id\":\"esp32-001\"")
    assert not fs.exists("config_staging.json")
    assert not fs.exists("app_staging")


class _TrackingLogger:
    """Logger that records pause/resume/flush calls for verification."""
    def __init__(self):
        self.calls: list[object] = []
    def pause_uplink(self) -> None:
        self.calls.append("pause")
    def resume_uplink(self) -> None:
        self.calls.append("resume")
    def flush(self, reason: str = "manual") -> bool:
        self.calls.append(("flush", reason))
        return True
    def info(self, msg: str, context: dict[str, Any] | None = None) -> None:
        pass
    def warn(self, msg: str, context: dict[str, Any] | None = None) -> None:
        pass
    def error(self, msg: str, context: dict[str, Any] | None = None) -> None:
        pass


def test_apply_does_not_pause_uplink():
    """apply() must not pause the logger — log flushes happen naturally via threshold."""
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    logger = _TrackingLogger()
    updater = Updater(fs=fs, http=http, system=system, config=_config(),
                      boot_manager=boot_manager, logger=logger)

    new_file = b"print('v2')"
    stream_data = _build_ota_stream([("main.py", new_file)])
    http.add_stream_response(_STREAM_URL, stream_data)

    updater.apply(
        UpdateInfo(available=True, version="1.1.0",
                   manifest=[{"path": "main.py", "hash": _sha256_hex(new_file), "size": len(new_file)}])
    )

    assert "pause" not in logger.calls
    assert "resume" not in logger.calls


def test_apply_flushes_logs_before_reset():
    """apply() must call flush('ota') after staging is complete and before reset()."""
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    logger = _TrackingLogger()
    updater = Updater(fs=fs, http=http, system=system, config=_config(),
                      boot_manager=boot_manager, logger=logger)

    files = [("mod" + str(i) + ".py", ("file-" + str(i)).encode()) for i in range(15)]
    stream_data = _build_ota_stream(files)
    http.add_stream_response(_STREAM_URL, stream_data)
    manifest = [{"path": p, "hash": _sha256_hex(c), "size": len(c)} for p, c in files]

    updater.apply(
        UpdateInfo(available=True, version="1.1.0", manifest=manifest)
    )

    assert ("flush", "ota") in logger.calls
    assert system.reset_calls == 1


# ---------------------------------------------------------------------------
# _StreamFrameReader unit tests
# ---------------------------------------------------------------------------

def test_stream_frame_reader_readline():
    data = b"HASH:abc123\nFILE:main.py\nSIZE:5\n"
    resp = MockStreamingResponse(data)
    reader = _StreamFrameReader(resp)

    assert reader.readline() == "HASH:abc123"
    assert reader.readline() == "FILE:main.py"
    assert reader.readline() == "SIZE:5"


def test_stream_frame_reader_read_chunks_full():
    payload = b"hello world!"
    data = ("SIZE:" + str(len(payload)) + "\n").encode() + payload + b"END\n"
    resp = MockStreamingResponse(data)
    reader = _StreamFrameReader(resp)
    reader.readline()  # consume SIZE line

    collected = b"".join(reader.read_chunks(len(payload)))
    assert collected == payload


def test_stream_frame_reader_read_chunks_small_chunk():
    payload = b"0123456789"
    resp = MockStreamingResponse(payload + b"END\n")
    reader = _StreamFrameReader(resp)

    # Convert each chunk to bytes immediately — the yielded memoryviews share
    # the same pre-allocated buffer and are only valid until the next iteration.
    chunks = [bytes(c) for c in reader.read_chunks(len(payload), chunk_size=3)]
    assert b"".join(chunks) == payload
    # Each chunk except possibly the last should be at most 3 bytes
    for c in chunks[:-1]:
        assert len(c) <= 3


def test_stream_frame_reader_reports_progress_per_chunk():
    payload = b"0123456789"
    resp = MockStreamingResponse(payload + b"END\n")
    progress: list[int] = []
    reader = _StreamFrameReader(resp, on_progress=lambda: progress.append(1))

    chunks = [bytes(c) for c in reader.read_chunks(len(payload), chunk_size=4)]

    assert b"".join(chunks) == payload
    assert len(progress) == len(chunks)


def test_stream_frame_reader_raises_on_eof():
    resp = MockStreamingResponse(b"HASH:abc")  # no newline — truncated
    reader = _StreamFrameReader(resp)

    with pytest.raises(RuntimeError, match="Unexpected EOF"):
        reader.readline()


def test_stream_frame_reader_raises_on_eof_in_content():
    # SIZE says 100 bytes but only 5 are available
    resp = MockStreamingResponse(b"hello")
    reader = _StreamFrameReader(resp)

    with pytest.raises(RuntimeError, match="Unexpected EOF"):
        list(reader.read_chunks(100))


# ---------------------------------------------------------------------------
# Streaming — single-socket guarantee
# ---------------------------------------------------------------------------

def test_apply_uses_single_stream_request_for_all_files():
    """The entire update must be fetched over ONE stream request (one socket)."""
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    files = [("mod" + str(i) + ".py", ("content-" + str(i)).encode()) for i in range(10)]
    stream_data = _build_ota_stream(files)
    http.add_stream_response(_STREAM_URL, stream_data)
    manifest = [{"path": p, "hash": _sha256_hex(c), "size": len(c)} for p, c in files]

    updater.apply(UpdateInfo(available=True, version="1.1.0", manifest=manifest))

    stream_calls = [c for c in http.calls if c[0] == "GET_STREAM"]
    assert len(stream_calls) == 1, "Expected exactly one GET_STREAM call for all files"
    assert stream_calls[0][1] == _STREAM_URL


def test_apply_writes_large_file_without_full_buffer():
    """Non-config files must be written to disk via write_chunks (no full-file bytearray).

    Verifies the OOM fix: even a 'large' file (simulated as 15 KB) is correctly
    staged without allocating a contiguous buffer for the entire content.
    The MockFileSystem.write_chunks implementation buffers internally for test
    assertions, but the updater itself never holds the full content in one object.
    """
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    # 15 KB file — larger than typical ESP32 contiguous heap blocks after fragmentation
    large_content = b"X" * 15360
    stream_data = _build_ota_stream([("lib/big_module.py", large_content)])
    http.add_stream_response(_STREAM_URL, stream_data)

    updater.apply(
        UpdateInfo(
            available=True,
            version="1.1.0",
            manifest=[{"path": "lib/big_module.py", "hash": _sha256_hex(large_content), "size": len(large_content)}],
        )
    )

    assert fs.read_bytes("app/lib/big_module.py") == large_content
    assert system.reset_calls == 1


def test_apply_cleans_tmp_file_on_stream_error():
    """If the stream is cut during a file, any .ota_tmp file must be cleaned up."""
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    # Build a valid first file then truncate mid-second file
    first = b"hello"
    second = b"world-truncated"
    # Stream: full first file, then second file with only 3 bytes delivered (SIZE says 15)
    stream_bytes = bytearray()
    stream_bytes.extend(("HASH:" + _sha256_hex(first) + "\n").encode())
    stream_bytes.extend(b"FILE:first.py\n")
    stream_bytes.extend(("SIZE:" + str(len(first)) + "\n").encode())
    stream_bytes.extend(first)
    # Second file: correct hash header but truncated body
    stream_bytes.extend(("HASH:" + _sha256_hex(second) + "\n").encode())
    stream_bytes.extend(b"FILE:second.py\n")
    stream_bytes.extend(("SIZE:" + str(len(second)) + "\n").encode())
    stream_bytes.extend(b"xxx")  # only 3 bytes instead of 15 — EOF will trigger

    http.add_stream_response(_STREAM_URL, bytes(stream_bytes))

    with pytest.raises(RuntimeError, match="Unexpected EOF"):
        updater.apply(
            UpdateInfo(
                available=True,
                version="1.1.0",
                manifest=[
                    {"path": "first.py", "hash": _sha256_hex(first), "size": len(first)},
                    {"path": "second.py", "hash": _sha256_hex(second), "size": len(second)},
                ],
            )
        )

    # Staging should be cleaned; no leftover .ota_tmp files
    assert not fs.exists("app_staging")


# ---------------------------------------------------------------------------
# manifest.json special handling (hash verification bypass)
# ---------------------------------------------------------------------------

def test_apply_skips_manifest_json_hash_verification():
    """manifest.json must be written without hash verification.
    
    The manifest contains hashes of all other files, so it cannot verify itself.
    This test verifies that an incorrect hash for manifest.json doesn't cause an error.
    """
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    fs.write_bytes("app/main.py", b"old-version")
    fs.write_text(
        "config.json",
        """
        {"device_id":"esp32-001","api_url":"http://localhost:8000","api_key":"old-secret","wifi_ssid":"ssid","wifi_password":"old-pass","heartbeat_interval_ms":1000,"max_boot_attempts":3,"current_version":"1.0.0"}
        """.strip(),
    )

    new_file = b"print('new-version')"
    new_config = b"{\"device_id\":\"replace-with-device-id\",\"api_url\":\"replace-with-api-url\",\"api_key\":\"replace-with-device-api-key\",\"wifi_ssid\":\"replace-with-ssid\",\"wifi_password\":\"replace-with-password\",\"heartbeat_interval_ms\":2000,\"max_boot_attempts\":4,\"current_version\":\"1.1.0\"}"
    manifest_content = b'{"version":"1.1.0","manifest":[{"path":"main.py","hash":"abc123"}]}'

    # Build stream with WRONG hash for manifest.json (0*64 instead of actual hash)
    stream_data = _build_ota_stream([
        ("main.py", new_file),
        ("config.json", new_config),
        ("manifest.json", manifest_content, "0" * 64)  # Wrong hash!
    ])
    http.add_stream_response(_STREAM_URL, stream_data)

    # Should succeed despite manifest.json having wrong hash
    updater.apply(
        UpdateInfo(
            available=True,
            version="1.1.0",
            manifest=[
                {"path": "main.py", "hash": _sha256_hex(new_file), "size": len(new_file)},
                {"path": "config.json", "hash": _sha256_hex(new_config), "size": len(new_config)},
                {"path": "manifest.json", "hash": "0" * 64, "size": len(manifest_content)},
            ],
        )
    )

    # All files should be staged correctly
    assert fs.read_bytes("main.py") == new_file
    assert system.reset_calls == 1


def test_apply_writes_manifest_json_to_staging():
    """manifest.json should be written and end up in app/ after version swap."""
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    fs.write_bytes("app/main.py", b"old-version")
    fs.write_text(
        "config.json",
        """
        {"device_id":"esp32-001","api_url":"http://localhost:8000","api_key":"old-secret","wifi_ssid":"ssid","wifi_password":"old-pass","heartbeat_interval_ms":1000,"max_boot_attempts":3,"current_version":"1.0.0"}
        """.strip(),
    )

    new_file = b"print('new-version')"
    new_config = b"{\"device_id\":\"replace-with-device-id\",\"api_url\":\"replace-with-api-url\",\"api_key\":\"replace-with-device-api-key\",\"wifi_ssid\":\"replace-with-ssid\",\"wifi_password\":\"replace-with-password\",\"heartbeat_interval_ms\":2000,\"max_boot_attempts\":4,\"current_version\":\"1.1.0\"}"
    manifest_content = b'{"version":"1.1.0","manifest":[{"path":"main.py","hash":"abc123"}]}'

    stream_data = _build_ota_stream([
        ("main.py", new_file),
        ("config.json", new_config),
        ("manifest.json", manifest_content)
    ])
    http.add_stream_response(_STREAM_URL, stream_data)

    updater.apply(
        UpdateInfo(
            available=True,
            version="1.1.0",
            manifest=[
                {"path": "main.py", "hash": _sha256_hex(new_file), "size": len(new_file)},
                {"path": "config.json", "hash": _sha256_hex(new_config), "size": len(new_config)},
                {"path": "manifest.json", "hash": _sha256_hex(manifest_content), "size": len(manifest_content)},
            ],
        )
    )

    # After apply(), manifest.json should be in app/manifest.json (after version swap)
    assert fs.read_bytes("app/manifest.json") == manifest_content
    assert system.reset_calls == 1


def test_apply_still_validates_other_files_when_manifest_present():
    """Skipping manifest.json hash verification should not affect other files.
    
    Verifies that while manifest.json bypasses hash verification, all other files
    (except config.json which is special-cased) still require correct hashes.
    """
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    fs.write_bytes("app/main.py", b"old-version")
    fs.write_text(
        "config.json",
        """
        {"device_id":"esp32-001","api_url":"http://localhost:8000","api_key":"old-secret","wifi_ssid":"ssid","wifi_password":"old-pass","heartbeat_interval_ms":1000,"max_boot_attempts":3,"current_version":"1.0.0"}
        """.strip(),
    )

    new_file = b"print('new-version')"
    manifest_content = b'{"version":"1.1.0"}'
    
    # Stream has WRONG hash for main.py but manifest.json bypasses verification
    stream_data = _build_ota_stream([
        ("main.py", new_file, "0" * 64),  # Wrong hash!
        ("manifest.json", manifest_content)
    ])
    http.add_stream_response(_STREAM_URL, stream_data)

    # Should raise because main.py has wrong hash
    with pytest.raises(ValueError, match="Hash mismatch"):
        updater.apply(
            UpdateInfo(
                available=True,
                version="1.1.0",
                manifest=[
                    {"path": "main.py", "hash": "0" * 64, "size": len(new_file)},
                    {"path": "manifest.json", "hash": _sha256_hex(manifest_content), "size": len(manifest_content)},
                ],
            )
        )

    # Staging should be cleaned up
    assert not fs.exists("app_staging")


def test_apply_feeds_watchdog_while_streaming():
    class _CountingWatchdog(IWatchdog):
        def __init__(self):
            self.feed_calls = 0

        def feed(self):
            self.feed_calls += 1

    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    watchdog = _CountingWatchdog()
    updater = Updater(
        fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager, watchdog=watchdog
    )

    content = b"Y" * 4096
    http.add_stream_response(_STREAM_URL, _build_ota_stream([("lib/big.py", content)]))

    updater.apply(
        UpdateInfo(
            available=True,
            version="1.1.0",
            manifest=[{"path": "lib/big.py", "hash": _sha256_hex(content), "size": len(content)}],
        )
    )

    assert watchdog.feed_calls >= 4096 // 512


def _merge_with_active(active_extra: dict[str, Any], staged_extra: dict[str, Any]) -> dict[str, Any]:
    fs = MockFileSystem()
    system = MockSystem()
    active: dict[str, Any] = {
        "device_id": "esp32-001",
        "api_url": "http://localhost:8000",
        "api_key": "old-secret",
        "wifi_ssid": "ssid",
        "wifi_password": "old-pass",
        "heartbeat_interval_ms": 1000,
        "max_boot_attempts": 3,
        "current_version": "1.0.0",
    }
    active.update(active_extra)
    fs.write_text("config.json", json.dumps(active))
    updater = Updater(
        fs=fs, http=MockHttpClient(), system=system, config=_config(),
        boot_manager=BootManager(fs=fs, system=system, max_attempts=3),
    )
    staged: dict[str, Any] = {
        "device_id": "replace-with-device-id",
        "api_url": "replace-with-api-url",
        "api_key": "replace-with-device-api-key",
        "wifi_ssid": "replace-with-ssid",
        "wifi_password": "replace-with-password",
        "wifi_country": "replace-with-wifi-country",
        "heartbeat_interval_ms": 2000,
        "max_boot_attempts": 3,
    }
    staged.update(staged_extra)
    return json.loads(updater._merge_config_payload(json.dumps(staged).encode("utf-8"), "1.1.0"))


def test_merge_retains_device_wifi_country():
    merged = _merge_with_active({"wifi_country": "NZ"}, {})

    assert merged["wifi_country"] == "NZ"


def test_merge_retains_device_wifi_country_over_release_value():
    merged = _merge_with_active({"wifi_country": "NZ"}, {"wifi_country": "AU"})

    assert merged["wifi_country"] == "NZ"


def test_merge_drops_wifi_country_placeholder_when_device_has_none():
    merged = _merge_with_active({}, {})

    assert "wifi_country" not in merged


def test_merge_uses_release_wifi_country_when_device_has_none():
    merged = _merge_with_active({}, {"wifi_country": "NZ"})

    assert merged["wifi_country"] == "NZ"


def test_merge_retains_device_radio_off_sleep_enabled_over_release():
    merged = _merge_with_active(
        {"power": {"radio_off_sleep_enabled": False, "production_sleep_max_ms": 1000}},
        {"power": {"radio_off_sleep_enabled": True, "production_sleep_max_ms": 60000}},
    )

    assert merged["power"]["radio_off_sleep_enabled"] is False
    # Other power settings still come from the release.
    assert merged["power"]["production_sleep_max_ms"] == 60000


def test_merge_retains_device_radio_off_sleep_enabled_true():
    merged = _merge_with_active(
        {"power": {"radio_off_sleep_enabled": True}},
        {"power": {"radio_off_sleep_enabled": False}},
    )

    assert merged["power"]["radio_off_sleep_enabled"] is True


def test_merge_uses_release_radio_off_sleep_enabled_when_device_has_none():
    merged = _merge_with_active({"power": {"production_sleep_max_ms": 1000}}, {"power": {"radio_off_sleep_enabled": True}})

    assert merged["power"]["radio_off_sleep_enabled"] is True


def test_merge_keeps_device_radio_off_sleep_when_release_has_no_power_block():
    merged = _merge_with_active({"power": {"radio_off_sleep_enabled": True}}, {})

    assert merged["power"] == {"radio_off_sleep_enabled": True}


# ---------------------------------------------------------------------------
# Flash space: confirmed app backup is freed before staging
# ---------------------------------------------------------------------------

def _updater_with_confirmed_app(
    fs: MockFileSystem, http: MockHttpClient, system: MockSystem, pending_app_changed: bool = False
) -> Updater:
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    fs.write_bytes("app/edge/main.py", b"current")
    fs.write_bytes("app_prev/edge/main.py", b"previous")
    fs.write_bytes("app_prev/edge/stale.py", b"previous-only")
    boot_manager.mark_success()
    if pending_app_changed:
        state = json.loads(fs.read_text("boot_state.json"))
        state["pending_app_changed"] = True
        fs.write_text("boot_state.json", json.dumps(state))
    return Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)


def test_apply_discards_confirmed_app_backup_before_staging():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    updater = _updater_with_confirmed_app(fs, http, system)
    new_file = b"new"
    http.add_stream_response(_STREAM_URL, _build_ota_stream([("edge/main.py", new_file)]))

    updater.apply(UpdateInfo(available=True, version="1.1.0", manifest=[]))

    assert fs.read_bytes("app/edge/main.py") == new_file
    assert fs.read_bytes("app_prev/edge/main.py") == b"current"
    assert not fs.exists("app_prev/edge/stale.py")


def test_apply_frees_confirmed_backup_even_when_download_fails():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    updater = _updater_with_confirmed_app(fs, http, system)
    http.add_stream_response(_STREAM_URL, _build_ota_stream([("edge/main.py", b"new", "0" * 64)]))

    with pytest.raises(ValueError):
        updater.apply(UpdateInfo(available=True, version="1.1.0", manifest=[]))

    assert not fs.exists("app_prev")
    assert fs.read_bytes("app/edge/main.py") == b"current"


def test_apply_keeps_backup_while_current_app_is_unconfirmed():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    updater = _updater_with_confirmed_app(fs, http, system, pending_app_changed=True)
    http.add_stream_response(_STREAM_URL, _build_ota_stream([("edge/main.py", b"new", "0" * 64)]))

    with pytest.raises(ValueError):
        updater.apply(UpdateInfo(available=True, version="1.1.0", manifest=[]))

    assert fs.read_bytes("app_prev/edge/stale.py") == b"previous-only"

# ---------------------------------------------------------------------------
# Root entry points are staged, not written to the live root mid-download
# ---------------------------------------------------------------------------

def test_apply_leaves_live_entry_points_untouched_when_download_fails():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)
    fs.write_bytes("main.py", b"main-v1")
    fs.write_bytes("boot.py", b"boot-v1")
    fs.write_bytes("app/edge/x.py", b"app-v1")
    http.add_stream_response(
        _STREAM_URL,
        _build_ota_stream(
            [
                ("boot.py", b"boot-v2"),
                ("main.py", b"main-v2"),
                ("edge/x.py", b"app-v2", "0" * 64),
            ]
        ),
    )

    with pytest.raises(ValueError):
        updater.apply(UpdateInfo(available=True, version="1.1.0", manifest=[]))

    assert fs.read_bytes("main.py") == b"main-v1"
    assert fs.read_bytes("boot.py") == b"boot-v1"
    assert not fs.exists("app_staging")
    assert system.reset_calls == 0


def test_apply_installs_entry_points_with_app_swap():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)
    fs.write_bytes("main.py", b"main-v1")
    fs.write_bytes("app/edge/x.py", b"app-v1")
    http.add_stream_response(
        _STREAM_URL,
        _build_ota_stream([("main.py", b"main-v2"), ("edge/x.py", b"app-v2")]),
    )

    updater.apply(UpdateInfo(available=True, version="1.1.0", manifest=[]))

    assert fs.read_bytes("main.py") == b"main-v2"
    assert fs.read_bytes("app/edge/x.py") == b"app-v2"
    assert fs.read_bytes("app_prev/_root/main.py") == b"main-v1"
    assert system.reset_calls == 1

# ---------------------------------------------------------------------------
# .mpy compatibility probe
# ---------------------------------------------------------------------------

_CHECK_URL = "http://localhost:8000/api/ota/check?version=1.0.0"
_PROBE = (PROBE_PATH, b"M\x06\x00\x1f probe")


class _Probe:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls: list[str] = []

    def __call__(self, directory: str) -> None:
        self.calls.append(directory)
        if self.error is not None:
            raise self.error


def _probe_updater(
    fs: MockFileSystem, http: MockHttpClient, system: MockSystem, probe: Callable[[str], None] | None
) -> Updater:
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    return Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager, probe=probe)


def _release(files: list[tuple[str, bytes]]) -> UpdateInfo:
    return UpdateInfo(
        available=True,
        version="1.1.0",
        manifest=[{"path": path, "hash": _sha256_hex(data), "size": len(data)} for path, data in files],
    )


def test_apply_installs_release_when_probe_loads():
    fs, http, system = MockFileSystem(), MockHttpClient(), MockSystem()
    probe = _Probe()
    updater = _probe_updater(fs, http, system, probe)
    files = [_PROBE, ("edge/shared/app/control_loop.mpy", b"compiled"), ("main.py", b"print('new')")]
    http.add_stream_response(_STREAM_URL, _build_ota_stream(files))

    updater.apply(_release(files))

    assert probe.calls == ["app_staging"]
    assert fs.read_bytes("app/edge/shared/app/control_loop.mpy") == b"compiled"
    assert system.reset_calls == 1


def test_apply_rejects_release_when_probe_fails_and_keeps_current_app():
    fs, http, system = MockFileSystem(), MockHttpClient(), MockSystem()
    updater = _probe_updater(fs, http, system, _Probe(ValueError("incompatible .mpy file")))
    fs.write_bytes("app/main.py", b"current")
    files = [_PROBE, ("edge/shared/app/control_loop.mpy", b"compiled"), ("main.py", b"print('new')")]
    http.add_stream_response(_STREAM_URL, _build_ota_stream(files))

    with pytest.raises(IncompatibleReleaseError, match="mpy_probe.mpy failed to load: incompatible .mpy file"):
        updater.apply(_release(files))

    assert not fs.exists("app_staging")
    assert fs.read_bytes("app/main.py") == b"current"
    assert system.reset_calls == 0


def test_check_skips_release_rejected_by_probe():
    fs, http, system = MockFileSystem(), MockHttpClient(), MockSystem()
    updater = _probe_updater(fs, http, system, _Probe(ValueError("incompatible .mpy file")))
    http.add_stream_response(_STREAM_URL, _build_ota_stream([_PROBE]))
    with pytest.raises(IncompatibleReleaseError):
        updater.apply(_release([_PROBE]))

    http.add_json_response("GET", _CHECK_URL, 200, {"available": True, "version": "1.1.0", "manifest": []})
    assert updater.check() is None

    http.add_json_response("GET", _CHECK_URL, 200, {"available": True, "version": "1.2.0", "manifest": []})
    newer = updater.check()
    assert newer is not None and newer.version == "1.2.0"


def test_apply_without_probe_installs_mpy_release():
    fs, http, system = MockFileSystem(), MockHttpClient(), MockSystem()
    updater = _probe_updater(fs, http, system, None)
    files = [_PROBE, ("edge/shared/app/control_loop.mpy", b"compiled")]
    http.add_stream_response(_STREAM_URL, _build_ota_stream(files))

    updater.apply(_release(files))

    assert fs.read_bytes("app/mpy_probe.mpy") == _PROBE[1]


def test_import_probe_loads_module_from_directory_and_cleans_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    (tmp_path / "mpy_probe.py").write_text("OK = 1\n", encoding="utf-8")

    import_probe(str(tmp_path))

    assert str(tmp_path) not in sys.path
    assert "mpy_probe" not in sys.modules


def test_import_probe_raises_when_module_cannot_load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    (tmp_path / "mpy_probe.py").write_text("raise ValueError('incompatible .mpy file')\n", encoding="utf-8")

    with pytest.raises(ValueError, match="incompatible"):
        import_probe(str(tmp_path))

    assert str(tmp_path) not in sys.path
    assert "mpy_probe" not in sys.modules
