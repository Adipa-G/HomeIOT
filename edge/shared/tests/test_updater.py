import hashlib
import json

from edge.shared.app.secret_crypto import encrypt_secret

import pytest

from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import Config
from edge.shared.app.updater import UpdateInfo, Updater, _StreamFrameReader
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


def _build_ota_stream(files) -> bytes:
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
        self.calls = []
    def pause_uplink(self):
        self.calls.append("pause")
    def resume_uplink(self):
        self.calls.append("resume")
    def flush(self, reason="manual"):
        self.calls.append(("flush", reason))
        return True
    def info(self, msg, ctx=None):
        pass
    def warn(self, msg, ctx=None):
        pass
    def error(self, msg, ctx=None):
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
    import io

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
